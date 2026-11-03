<img src="docs/icon.svg" width="64" alt="Sidelines logo: a dot outside a bubble">

# Sidelines

*The dot outside the bubble.*

**Live:** [sidelinesnews.github.io](https://sidelinesnews.github.io) · [Sources](https://sidelinesnews.github.io/sources.html) · [Support](https://sidelinesnews.github.io/support.html) · [How it was built](https://sidelinesnews.github.io/about.html)

An open-source, ad-free news aggregator for the stories that never make it to the main stage.

Most people's news comes from the same ten places. Sidelines reads a wide pool of independent, regional, local, science and across-the-spectrum outlets. It checks what the big mainstream outlets are already running and pushes those stories down. It also stops any single source from dominating the page.

No ads. No tracking. No accounts. No algorithmic feed tuned for engagement.

## How it works

1. **Fetch:** reads every feed in `feeds.json`. `pool` feeds are shown. `baseline` feeds (BBC, CNN, Fox, NYT…) are never shown; they're only used to see what's already everywhere.
2. **Group:** headlines that describe the same story are merged, so one event doesn't take up ten slots.
3. **Score:** stories the mainstream baseline is covering lose most of their score. Stories picked up widely across the pool lose a little. Newer stories rank higher.
4. **Balance:** each outlet can place at most 3 stories, and repeats from the same outlet are penalized so sources interleave.
5. **A balanced handful:** the top five are two "Worth knowing", one "Something good", one "Something wondrous" and one "Off the map", with never more than two heavy stories. The word lists that decide "heavy" and "hopeful" are public in `tones.json`.
6. **Publish:** writes a static page to `docs/` with a diversity meter showing how spread out that day's page is.

All the logic is in `aggregator.py`, in plain Python with no dependencies. Anyone can read exactly why a story is on the page.

## Run it locally

Windows: double-click `Start.bat`. Anywhere else: `python aggregator.py`, then open `docs/index.html`.

## Hosting (free, automatic)

`.github/workflows/update.yml` runs the aggregator on GitHub's servers every 3 hours and commits the new page. GitHub Pages serves it from `docs/`.

## Adding or removing outlets

Edit `feeds.json`. After a run, `docs/feed_status.json` lists any feeds that failed.

## Following Sidelines

- **RSS:** `feed.xml` on the site, for any feed reader.
- **Data:** `data.json`, for anyone who wants to build on it.
- **For AI tools:** `llms.txt` explains the site and its rules in plain text.
- **Archive:** the last page of every day is kept under `archive/`.
- **For reporters:** `bubbling.xml` is an RSS feed of stories several independent outlets are covering that the mainstream hasn't picked up yet.
- **Search engines:** `robots.txt` and `sitemap.xml` welcome everyone, and each update pings IndexNow so search engines (and the AI tools built on them) see changes quickly.

## Sensitive tips

Sidelines collects nothing, on purpose. The [Tips page](https://sidelinesnews.github.io/tips.html) sends anyone with a sensitive tip to SecureDrop, the system maintained by the Freedom of the Press Foundation.

## Security

- No server, no database, no forms, no cookies: there's nothing stored to steal.
- Every page carries a content security policy that only allows the site's own script.
- The update robot's tools are pinned to exact versions, and it has only the one permission it needs.
- Ranking changes are logged in [`CHANGELOG.md`](CHANGELOG.md).

## Found by readers

To feature a story a reader sent in, edit `reader_found.json` and add it to `items` (the file includes an example). Only add links to stories that are already published elsewhere. Each one shows on the front page for 14 days.

## The promise

Sidelines will never:

- run ads
- sell or rent placement on the page
- track readers (no cookies, no analytics, no tracking pixels)
- sell or share data about anyone

The ranking rules are public, and any change to them happens in the open.

**Money:** Sidelines takes no money. It costs nothing to run. If you want to help, support the journalists and the free-press organizations listed on the [Support page](https://sidelinesnews.github.io/support.html). (A donate switch exists in `feeds.json` as `donate_url`. It is off, and would only ever be turned on in the open if real running costs appeared.)

If Sidelines ever breaks this promise, you already have the cure: the code is AGPL-3.0, so fork it and run the honest version.

## Legacy

Sidelines is meant to outlive me. This is my public statement of intent, made on 2 November 2026:

If Sidelines grows beyond a one-person project, or if I die or can no longer care for it, I want everything that is mine to give (the code, the repository, the Sidelines name, and any remaining funds) to go to the **Freedom of the Press Foundation**. They adopted Aaron Swartz's unfinished SecureDrop project after his death and kept it alive, and I'd be proud for Sidelines to follow the same path.

If they decline, it should go to another independent, non-commercial journalism or press-freedom organization that will keep the promise above.

Sidelines is not affiliated with or endorsed by the Freedom of the Press Foundation, and any handover depends on their agreement. The code itself already belongs to everyone under the AGPL-3.0, so the idea can't be owned or buried either way.

## Identifier

The founding statement lives in [`FOUNDING.md`](FOUNDING.md) and is never edited. Its SHA-256 fingerprint is:

`113a4b9d9e1987b9398a5035db0ffabf282c4a93b3f193fe7f3e905bc3a44164`

That fingerprint is stamped into the Bitcoin ledger with [OpenTimestamps](https://opentimestamps.org) (proof file: `FOUNDING.md.ots`), so anyone can verify that the founding statement existed, unchanged, from 2 November 2026.

---

Built with the help of Claude, an AI made by Anthropic.
