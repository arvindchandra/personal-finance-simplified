#!/usr/bin/env python3
"""Import new podcast episodes from the show's public RSS feed."""

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
EPISODES_DIR = ROOT / "content" / "episodes"
FEED_URL = "https://anchor.fm/s/114d1d4bc/podcast/rss"
ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
TITLE_RE = re.compile(r'^title\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
NUMBER_RE = re.compile(r'^episode\s*=\s*"(\d+)"\s*$', re.MULTILINE)
GUID_RE = re.compile(r'^rss_guid\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
ACCENTS = ("coral", "blue", "yellow")
MARKDOWN_SPECIALS = re.compile(r"([\\`*_{}\[\]()#+.!|>-])")


@dataclass
class Episode:
    title: str
    guid: str
    date: str
    duration: str
    audio_url: str
    description: str
    body: str


class DescriptionParser(HTMLParser):
    """Turn RSS description HTML into plain paragraphs and list items."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: List[Tuple[str, str]] = []
        self.current: List[str] = []
        self.block_type = "p"

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("p", "li"):
            self._finish_block()
            self.block_type = tag
        elif tag == "br":
            self.current.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("p", "li"):
            self._finish_block()

    def handle_data(self, data: str) -> None:
        self.current.append(data)

    def _finish_block(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self.current)).strip()
        if text:
            self.blocks.append((self.block_type, text))
        self.current = []
        self.block_type = "p"

    def result(self) -> List[Tuple[str, str]]:
        self._finish_block()
        return self.blocks


def _clean_description(value: str) -> List[Tuple[str, str]]:
    parser = DescriptionParser()
    parser.feed(html.unescape(value))
    parser.close()
    blocks = parser.result()
    if blocks:
        return blocks
    text = re.sub(r"\s+", " ", html.unescape(value)).strip()
    return [("p", text)] if text else []


def _escape_markdown(value: str) -> str:
    return MARKDOWN_SPECIALS.sub(r"\\\1", value)


def _duration(value: Optional[str]) -> str:
    if not value:
        return "Unknown duration"
    parts = value.split(":")
    try:
        seconds = sum(int(part) * (60 ** index) for index, part in enumerate(reversed(parts)))
    except ValueError as error:
        raise ValueError(f"Invalid RSS episode duration: {value!r}") from error
    minutes = max(1, (seconds + 30) // 60)
    return f"{minutes} min"


def parse_feed(xml_data: bytes) -> List[Episode]:
    root = ET.fromstring(xml_data)
    episodes: List[Episode] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        guid = (item.findtext("guid") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        enclosure = item.find("enclosure")
        audio_url = enclosure.get("url", "").strip() if enclosure is not None else ""
        if not title or not guid or not pub_date or not audio_url:
            raise ValueError("An RSS episode is missing its title, GUID, publish date, or audio enclosure.")

        try:
            published = parsedate_to_datetime(pub_date)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid publish date for RSS episode {title!r}: {pub_date!r}") from error
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        blocks = _clean_description(item.findtext("description") or "")
        description_text = next((text for kind, text in blocks if kind == "p"), title)
        if len(description_text) > 240:
            description_text = description_text[:237].rsplit(" ", 1)[0] + "..."
        body = "\n\n".join(
            ("- " if kind == "li" else "") + _escape_markdown(text)
            for kind, text in blocks
        ) or _escape_markdown(title)

        episodes.append(
            Episode(
                title=title,
                guid=guid,
                date=published.astimezone(timezone.utc).date().isoformat(),
                duration=_duration(item.findtext(ITUNES_NS + "duration")),
                audio_url=audio_url,
                description=description_text,
                body=body,
            )
        )
    return episodes


def _normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _read_existing(episodes_dir: Path) -> Tuple[Set[str], Set[str], int]:
    titles: Set[str] = set()
    guids: Set[str] = set()
    max_number = 0
    for path in episodes_dir.glob("*/index.md"):
        text = path.read_text(encoding="utf-8")
        title_match = TITLE_RE.search(text)
        number_match = NUMBER_RE.search(text)
        guid_match = GUID_RE.search(text)
        if title_match:
            titles.add(_normalized_title(_decode_toml_string(title_match.group(1))))
        if number_match:
            max_number = max(max_number, int(number_match.group(1)))
        if guid_match:
            guids.add(_decode_toml_string(guid_match.group(1)))
    return titles, guids, max_number


def _slugify(value: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.casefold()).strip("-")
    return slug or "episode"


def _front_matter_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _decode_toml_string(value: str) -> str:
    return json.loads(f'"{value}"')


def _render_episode(episode: Episode, number: int) -> str:
    accent = ACCENTS[(number - 1) % len(ACCENTS)]
    return (
        "+++\n"
        f"title = {_front_matter_string(episode.title)}\n"
        f"date = {episode.date}\n"
        f"description = {_front_matter_string(episode.description)}\n"
        "\n[extra]\n"
        f"episode = {_front_matter_string(str(number))}\n"
        f"rss_guid = {_front_matter_string(episode.guid)}\n"
        f"duration = {_front_matter_string(episode.duration)}\n"
        f"rss_audio_url = {_front_matter_string(episode.audio_url)}\n"
        f"accent = {_front_matter_string(accent)}\n"
        "+++\n\n"
        f"{episode.body}\n"
    )


def sync_episodes(episodes: List[Episode], episodes_dir: Path, dry_run: bool = False) -> List[Path]:
    episodes_dir.mkdir(parents=True, exist_ok=True)
    known_titles, known_guids, next_number = _read_existing(episodes_dir)
    missing = [
        episode for episode in episodes
        if episode.guid not in known_guids and _normalized_title(episode.title) not in known_titles
    ]
    missing.sort(key=lambda episode: (episode.date, episode.guid))

    created: List[Path] = []
    for offset, episode in enumerate(missing, start=1):
        number = next_number + offset
        slug = _slugify(episode.title)
        destination = episodes_dir / slug / "index.md"
        if destination.exists():
            destination = episodes_dir / f"{slug}-episode-{number}" / "index.md"
        if destination.exists():
            raise FileExistsError(f"Episode output already exists: {destination}")
        created.append(destination)
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(_render_episode(episode, number), encoding="utf-8")
        known_titles.add(_normalized_title(episode.title))
        known_guids.add(episode.guid)

    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed-url", default=FEED_URL, help="Podcast RSS feed URL")
    parser.add_argument("--episodes-dir", type=Path, default=EPISODES_DIR, help="Zola episodes directory")
    parser.add_argument("--dry-run", action="store_true", help="Report new episodes without writing files")
    args = parser.parse_args()

    request = urllib.request.Request(
        args.feed_url,
        headers={"User-Agent": "PersonalFinanceSimplifiedEpisodeSync/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            episodes = parse_feed(response.read())
        created = sync_episodes(episodes, args.episodes_dir, dry_run=args.dry_run)
    except (OSError, ET.ParseError, ValueError) as error:
        print(f"Episode sync failed: {error}", file=sys.stderr)
        return 1

    if not created:
        print("Episode catalog is up to date.")
        return 0

    action = "Would add" if args.dry_run else "Added"
    for path in created:
        print(f"{action}: {path.relative_to(args.episodes_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
