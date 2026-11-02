# Sidelines

An open-source, ad-free news aggregator for the stories that never make it to the main stage.

Most people's news comes from the same ten places. Sidelines reads a wide pool of independent, regional, local, science and across-the-spectrum outlets. It checks what the big mainstream outlets are already running and pushes those stories down. It also stops any single source from dominating the page.

No ads. No tracking. No accounts. No algorithmic feed tuned for engagement.

## How it works

1. **Fetch:** reads every feed in `feeds.json`. `pool` feeds are shown. `baseline` feeds (BBC, CNN, Fox, NYT…) are never shown; they're only used to see what's already everywhere.
2. **Group:** headlines that describe the same story are merged, so one event doesn't take up ten slots.
3. **Score:** stories the mainstream baseline is covering lose most of their score. Stories picked up widely across the pool lose a little. Newer stories rank higher.
4. **Balance:** each outlet can place at most 3 stories, and repeats from the same outlet are penalized so sources interleave.
5. **Publish:** writes a static page to `docs/` with a diversity meter showing how spread out that day's page is.

All the logic is in `aggregator.py`, in plain Python with no dependencies. Anyone can read exactly why a story is on the page.

## Run it locally

Windows: double-click `Start.bat`. Anywhere else: `python aggregator.py`, then open `docs/index.html`.

## Hosting (free, automatic)

`.github/workflows/update.yml` runs the aggregator on GitHub's servers every 3 hours and commits the new page. GitHub Pages serves it from `docs/`.

## Adding or removing outlets

Edit `feeds.json`. After a run, `docs/feed_status.json` lists any feeds that failed.

## Principles

- No ads, no trackers, no paywall, ever.
- The ranking rules are public, and changes to them happen in the open.
- Funded by donations only, if at all.
