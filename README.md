# rss-digest

Merges ~215 political/cultural RSS feeds (see `sites_list.md`) into one
combined feed, on a schedule, for free.

## Setup

```
pip install -r requirements.txt
python merge_feeds.py
```

This writes `combined.xml`, `combined.html`, and `index.html` locally.

## Sharing the combined feed downstream, for free

GitHub Pages is the free hosting piece — the `.github/workflows/update.yml`
workflow already re-runs the script daily and commits the fresh output, so
once Pages is turned on, the feed updates itself automatically at no cost.

1. Push this repo to GitHub (public repo — Pages' free tier requires it,
   unless you're on a paid GitHub plan that supports private Pages).
2. In the repo: **Settings → Pages → Build and deployment → Source:
   Deploy from a branch → Branch: `main`, folder: `/ (root)`** → Save.
3. GitHub gives you a URL shaped like:
   `https://<your-username>.github.io/<repo-name>/`
   - That URL itself serves `index.html` — a browsable digest page.
   - The **RSS feed** to actually share/subscribe to is:
     `https://<your-username>.github.io/<repo-name>/combined.xml`
4. Anyone can paste that `combined.xml` URL into Feedly, Inoreader,
   Flipboard, Apple News, NetNewsWire, etc. — it's a normal public RSS
   feed at that point, no login or API key needed on their end.

If you'd rather not use GitHub Pages, `combined.xml` is a plain static
file — Cloudflare Pages, Netlify, or even a Gist raw URL work the same
way, for free, with the same workflow just swapped to deploy elsewhere.

## Files

- `merge_feeds.py` — the script; edit the `FEEDS` dict to add/remove sources
- `sites_list.md` — clean reference list of every source currently included
- `.github/workflows/update.yml` — daily auto-refresh via GitHub Actions
- `requirements.txt` — just `feedparser`

## A note on feed URLs

Many entries in `FEEDS` are marked `# verify` — best-guess URLs based on
common CMS conventions, not individually hand-checked (216 feeds is too
many to verify one by one). Run the script and read the console output:
failing feeds print `[skip] Name: could not parse (...)` and are safely
ignored rather than crashing the run. Fix or remove those as you find them.
