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
3. The workflow in `.github/workflows/deploy.yml` checks and builds the site on pull requests. Pushing to `main` builds and deploys it automatically.
4. The site is configured for `https://personalfinancesimplified.win`. The `static/CNAME` file carries that domain into the published site. Point the domain's DNS to GitHub Pages and add the custom domain under **Settings → Pages** if those are not already configured.

If you prefer the default `https://<OWNER>.github.io/<REPOSITORY>/` address, change `base_url` in `zola.toml` to that URL and remove `static/CNAME` before publishing.

## Customize

- Update `base_url` and the show details in `zola.toml` before deploying.
- Add an episode as `content/episodes/your-episode/index.md`. Include its episode number, date, and duration, along with either `spotify_episode_id` or `rss_audio_url` in the front matter to provide a player.
- Push a new episode file to `main` to have GitHub Actions rebuild and publish the site.
- Episode metadata and hosted audio are published in the show's RSS feed at `https://anchor.fm/s/114d1d4bc/podcast/rss`.
- The homepage contact form emails messages to `contact_email` in `zola.toml` through FormSubmit. Confirm the activation email sent by FormSubmit to the recipient before accepting submissions. Form submissions are processed by FormSubmit.
