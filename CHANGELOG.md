# Changelog

Every change to how Sidelines chooses stories is recorded here, in the open.

## 3 November 2026: a rhythm (good, laughs, pets)

The full list now has a rhythm: **every 3rd story is good news** (or something wondrous), **every 5th is a laugh**, and **every 6th is a pet or animal story**. Satire is always labelled **"A laugh · satire"**, because satire without a label on a news site is how jokes become misinformation. Satire with heavy words (war, killed…) is skipped. Laughs and pets are kept out of the news ranking and the meter; they're slotted in on purpose, from up to 14 days back, and if they run out the list simply carries on.

New sources: Good News Network and The Optimist Daily (good news), Good News Network's animals section (pets & critters), and McSweeney's Internet Tendency and The Beaverton (laughs).

## 3 November 2026: the Gentle button

A **Gentle** button next to the greeting. One tap shows only good and wondrous stories; tap again and the hard news is back. Nothing is deleted or ranked differently, it's just hidden on your screen. The choice is remembered in your own browser only (localStorage); Sidelines never sees it. Suggested by a reader's mom, who would prefer 4 good stories to every 1 bad one.

Also: **"rescue" is no longer a hopeful word** (in South Africa, "business rescue" is a bankruptcy process), and words like insolvency, liquidation, slaughter, smuggling and poaching now count as heavy.

Also: **hopeful words now only count in the headline.** Checked against the live page, words like "protect" and "recovery" kept turning up in the summaries of grim stories ("a plan to prevent Democrats from being seated", "data centers to protect against drones"). "Protect", "celebrate", "recovery", "together" and "community" were removed from the hopeful list. Heavy words still count anywhere.

Also: **shopping posts are blocked.** A WIRED coupon post ("Uber Eats Promo Codes") reached the handful labelled "Something good". Sidelines promises no ads, so headlines that look like coupons, deals or gift guides are now skipped before anything else happens.

## 3 November 2026: labels are promises

The first live run of the balanced handful mislabelled two stories: an election-timing explainer was called "Something good", and a story about a controversial resort was called "Something wondrous". Fixes:

- **No false labels.** If no story truly fits "good" or "wondrous", the slot now says **Something else**.
- **A deeper well.** Hopeful outlets publish less often, so the good and wondrous slots may reach back up to 14 days. Everything else still sticks to the last 4 days.
- **Every third story is a bright one.** In the full list, every third story is good news (or, failing that, something wondrous), topped up from the 14-day well. When the well runs dry, the list carries on as normal: nothing is invented, nothing is hidden. Doom sells; Sidelines isn't selling anything.
- **One outlet per handful**, so no single voice sets the mood.
- **Word lists tuned** (`tones.json`): added heavier words (arrest, police, controversial, uncertainty, protest…); removed noisy hopeful words (first, free, win, return, community, clean); environment outlets no longer count as automatically "wondrous".

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
