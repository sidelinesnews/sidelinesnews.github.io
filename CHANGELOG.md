# Changelog

Every change to how Sidelines chooses stories is recorded here, in the open.

## 3 November 2026: a balanced handful

- The top five now follow a fixed recipe: two "Worth knowing" (the most under-covered stories), one "Something good", one "Something wondrous" (science, curiosity, nature) and one "Off the map" (a region not already shown).
- Never more than two heavy stories in the handful. Heavy stories still appear in the full list; nothing is hidden.
- The words that mark a story as heavy or hopeful are public in `tones.json`.
- Added three solutions-journalism outlets: Reasons to be Cheerful, Positive News and YES! Magazine.

## 3 November 2026: smarter story matching

- Headlines are now also matched on rare, specific words (names, places, numbers), not only on how many words they share. Rare words count more than common ones, so "Ebola", "Congo" and "5,300" outweigh words like "says" or "new".
- Two headlines are treated as the same story if they share at least two rare words that carry most of their meaning. Numbers like "5,300" and "5300" now match.
- Result: fewer stories wrongly labelled "no mainstream pickup", and a more trustworthy Bubbling up list.

## 2 November 2026: sources

- Added WIRED to the pool.
- Added the Associated Press and Reuters to the mainstream comparison list (via Google News, as neither offers a public feed), so stories already on the wires are recognized.
- Removed The Wire (India), which blocks automated readers.

## 2 November 2026: launch

- Reads a public pool of independent, regional, local, science and across-the-spectrum outlets, plus a mainstream comparison list that is never shown.
- Groups headlines about the same story.
- Score: stories the mainstream list is running lose most of their score; stories picked up widely across the pool lose a little; newer stories rank higher.
- Each outlet can place at most 3 stories, and repeats from one outlet are penalized so sources interleave.
- Stories with missing or future dates are treated as about 18 hours old, never as brand new.
- Today's handful: the top 5 stories.
- Bubbling up: stories covered by 2 or more pool outlets and no mainstream outlet.
- Found by readers: hand-checked links, shown for 14 days.
