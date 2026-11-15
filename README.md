# Personal Finance Simplified

A responsive podcast site built with [Zola](https://www.getzola.org/) for the Personal Finance Simplified podcast. It features verified show information and recent episodes, with Spotify listening embeds and individual episode pages.

## Run locally

Install Zola, then start the preview server:

```sh
zola serve
```

Build the static site into `public/`:

```sh
zola build
```

## Publish with GitHub Pages

1. Create a GitHub repository and push this project to its `main` branch.
2. In the repository, open **Settings → Pages** and set the build and deployment source to **GitHub Actions**.
3. The workflow in `.github/workflows/deploy.yml` checks and builds pull requests and deploys pushes to `main`.
4. The site is configured for `https://arvindchandra.github.io/personal-finance-simplified`.

## Customize

- Update `base_url` and the show details in `zola.toml` before deploying.
- Add an episode as `content/episodes/your-episode/index.md`. Include its episode number, date, and duration, along with either `spotify_episode_id` or `rss_audio_url` in the front matter to provide a player.
- The scheduled workflow checks the podcast RSS feed every six hours. When a new episode appears, it creates a Zola page, commits it to `main`, and includes it in that run's GitHub Pages deployment. Use **Actions → Build and deploy site → Run workflow** to check manually.
- The workflow requires repository Actions permissions that allow `GITHUB_TOKEN` to write contents, and branch protection must allow the workflow to push its generated episode commit to `main`.
- Episode metadata and hosted audio are published in the show's RSS feed at `https://anchor.fm/s/114d1d4bc/podcast/rss`.
- The homepage contact form emails messages to `contact_email` in `zola.toml` through FormSubmit. Confirm the activation email sent by FormSubmit to the recipient before accepting submissions. Form submissions are processed by FormSubmit.
