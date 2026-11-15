import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync_episodes import parse_feed, sync_episodes


FEED = b"""<?xml version="1.0"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
  <channel>
    <item>
      <title>New Episode: Money &amp; More</title>
      <description>&lt;p&gt;A clear introduction to money.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Build a budget&lt;/li&gt;&lt;li&gt;Save consistently&lt;/li&gt;&lt;/ul&gt;</description>
      <guid isPermaLink="false">rss-episode-2</guid>
      <pubDate>Wed, 18 Nov 2026 14:00:00 GMT</pubDate>
      <enclosure url="https://example.com/audio.m4a" type="audio/x-m4a" />
      <itunes:duration>00:10:30</itunes:duration>
    </item>
    <item>
      <title>First Episode</title>
      <description>&lt;p&gt;A first episode summary.&lt;/p&gt;</description>
      <guid isPermaLink="false">rss-episode-1</guid>
      <pubDate>Wed, 11 Nov 2026 14:00:00 GMT</pubDate>
      <enclosure url="https://example.com/first.m4a" type="audio/x-m4a" />
      <itunes:duration>00:08:00</itunes:duration>
    </item>
  </channel>
</rss>
"""


class ParseFeedTests(unittest.TestCase):
    def test_parses_rss_episode_metadata(self):
        episodes = parse_feed(FEED)

        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0].title, "New Episode: Money & More")
        self.assertEqual(episodes[0].date, "2026-11-18")
        self.assertEqual(episodes[0].duration, "11 min")
        self.assertEqual(episodes[0].audio_url, "https://example.com/audio.m4a")
        self.assertIn("- Build a budget", episodes[0].body)
        self.assertIn("- Save consistently", episodes[0].body)

    def test_rejects_items_without_stable_identity_or_audio(self):
        malformed = b"<rss><channel><item><title>Missing fields</title></item></channel></rss>"

        with self.assertRaisesRegex(ValueError, "missing its title, GUID"):
            parse_feed(malformed)


class SyncEpisodeTests(unittest.TestCase):
    def test_adds_only_missing_episodes_and_is_idempotent(self):
        episodes = parse_feed(FEED)
        with tempfile.TemporaryDirectory() as temporary:
            episodes_dir = Path(temporary)
            (episodes_dir / "existing").mkdir()
            (episodes_dir / "existing" / "index.md").write_text(
                '+++\ntitle = "First Episode"\n[extra]\nepisode = "4"\n+++\n',
                encoding="utf-8",
            )

            created = sync_episodes(episodes, episodes_dir)

            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].parent.name, "new-episode-money-more")
            page = created[0].read_text(encoding="utf-8")
            self.assertIn('episode = "5"', page)
            self.assertIn('rss_guid = "rss-episode-2"', page)
            self.assertIn('rss_audio_url = "https://example.com/audio.m4a"', page)
            self.assertEqual(sync_episodes(episodes, episodes_dir), [])

    def test_dry_run_does_not_create_episode_files(self):
        episodes = parse_feed(FEED)
        with tempfile.TemporaryDirectory() as temporary:
            episodes_dir = Path(temporary)

            created = sync_episodes(episodes, episodes_dir, dry_run=True)

            self.assertEqual(len(created), 2)
            self.assertEqual(list(episodes_dir.iterdir()), [])

    def test_matches_existing_titles_with_curly_apostrophes(self):
        episode = parse_feed(FEED)[0]
        episode.title = "Money Mistakes Young Adults Shouldn’t Avoid"
        episode.guid = "existing-rss-id"
        with tempfile.TemporaryDirectory() as temporary:
            episodes_dir = Path(temporary)
            (episodes_dir / "existing").mkdir()
            (episodes_dir / "existing" / "index.md").write_text(
                '+++\ntitle = "Money Mistakes Young Adults Shouldn’t Avoid"\n'
                '[extra]\nepisode = "1"\n+++\n',
                encoding="utf-8",
            )

            self.assertEqual(sync_episodes([episode], episodes_dir), [])


if __name__ == "__main__":
    unittest.main()
