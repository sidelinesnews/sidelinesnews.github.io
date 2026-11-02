#!/usr/bin/env python3
"""
Sidelines - an anti-bubble news aggregator.

Reads a wide pool of outlets, reads a small "baseline" of big mainstream
outlets only to see what's already everywhere, groups stories that are about
the same thing, and ranks the ones the big outlets aren't covering. Caps how
many stories any one outlet can place so no single source dominates.

Standard library only (no pip installs). Writes a static site to docs/.

  python aggregator.py                 # real run
  python aggregator.py --feeds X.json  # use a different feed list
"""
import argparse
import concurrent.futures as cf
import email.utils
import html
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CONFIG = {
    "max_stories": 60,         # stories on the page
    "per_outlet_cap": 3,       # max stories from any one outlet
    "max_age_hours": 96,       # ignore anything older
    "half_life_hours": 36,     # freshness decay
    "timeout": 20,
    "user_agent": "SidelinesBot/0.3 (+open-source news aggregator)",
}

STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being
it its this that these those over after before about into than then up down out off new says say said
amid how why what who when where will would can could may might not no yes more most just now his her
their our your you we they he she them us via vs per new year years week day days report reports""".split())


# ---------- fetching & parsing ----------

class _Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []

    def handle_data(self, d):
        self.out.append(d)


BOILERPLATE = re.compile(r"\s*(The post .{0,300}? appeared first on .{0,120}?\.?|Continue reading\W*|Read more\W*)\s*$", re.I)


def strip_html(s):
    if not s:
        return ""
    p = _Strip()
    try:
        p.feed(s)
    except Exception:
        return re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(" ".join(p.out))).strip()


def local(tag):
    return tag.rsplit("}", 1)[-1].lower()


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names:
            if local(c.tag) == "link" and c.get("href"):
                if c.get("rel", "alternate") == "alternate":
                    return c.get("href")
                continue
            if c.text and c.text.strip():
                return c.text.strip()
    return ""


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        d = None
    if d is None:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _clean_xml(raw):
    """Repairs the most common feed mistakes: junk before the first tag,
    bare '&' characters, and invisible control characters."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    text = text[text.find("<"):] if "<" in text else text
    text = re.sub(r"&(?!#?[A-Za-z0-9]+;)", "&amp;", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"^<\?xml[^>]*\?>", "", text)
    return text.encode("utf-8")


def parse_feed(raw):
    """Handles RSS 2.0, RSS 1.0/RDF and Atom. Tries strict first, then repaired."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        root = ET.fromstring(_clean_xml(raw))
    items = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title = strip_html(child_text(el, "title"))
        link = child_text(el, "link") or child_text(el, "guid", "id")
        summ = BOILERPLATE.sub("", strip_html(child_text(el, "description", "summary", "content", "encoded")))
        date = parse_date(child_text(el, "pubdate", "published", "updated", "date"))
        if title and link:
            items.append({"title": title, "link": link.strip(), "summary": summ[:280], "date": date})
    return items


HEADERS = {
    "User-Agent": CONFIG["user_agent"],
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "en",
}


def fetch(feed, tries=2):
    """Tries the main URL, then any 'alt' URLs. One retry per URL for hiccups
    (timeouts, 5xx), with more patience the second time. A 4xx means 'no'."""
    err = None
    for url in [feed["url"]] + feed.get("alt", []):
        for attempt in range(tries):
            req = urllib.request.Request(url, headers=HEADERS)
            try:
                with urllib.request.urlopen(req, timeout=CONFIG["timeout"] * (attempt + 1)) as r:
                    return feed, parse_feed(r.read()), None
            except urllib.error.HTTPError as e:
                err = f"HTTPError: {e}"
                if e.code < 500:
                    break
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
            if attempt + 1 < tries:
                time.sleep(3)
    return feed, [], (err or "unknown error")[:200]


def fetch_all(feeds):
    results = []
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for r in ex.map(fetch, feeds):
            results.append(r)
    return results


# ---------- clustering ----------

def tokens(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = set()
    for w in words:
        if w in STOP or len(w) < 3:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def same_story(a, b):
    shared = a & b
    if len(shared) < 3:
        return False
    return len(shared) / min(len(a), len(b)) >= 0.5


def cluster(items):
    clusters = []
    for it in items:
        tk = it["tokens"]
        if len(tk) < 3:
            clusters.append({"items": [it], "tokens": set(tk)})
            continue
        for c in clusters:
            if same_story(tk, c["tokens"]):
                c["items"].append(it)
                c["tokens"] |= tk
                break
        else:
            clusters.append({"items": [it], "tokens": set(tk)})
    return clusters


# ---------- scoring & selection ----------

UNKNOWN_AGE_H = 18  # undated stories are treated as 'sort of recent', never as brand new


def item_age_h(it, now):
    d = it["date"]
    if d is None:
        return None
    age = (now - d).total_seconds() / 3600
    if age < -0.25:  # dated in the future: the feed's clock is wrong, so we can't trust it
        return None
    return max(0.0, age)


def score_clusters(clusters, now):
    scored = []
    for c in clusters:
        pool = [i for i in c["items"] if not i["baseline"]]
        if not pool:
            continue  # only mainstream covered it; we don't show those
        base_outlets = {i["outlet"] for i in c["items"] if i["baseline"]}
        pool_outlets = {i["outlet"] for i in pool}
        # rarity: penalise mainstream pickup hard, wide pool pickup gently
        rarity = 1.0 / (1 + 2.0 * len(base_outlets) + 0.5 * (len(pool_outlets) - 1))
        known = [i for i in pool if item_age_h(i, now) is not None]
        lead = min(known, key=lambda i: item_age_h(i, now)) if known else pool[0]
        age_h = item_age_h(lead, now)
        date_known = age_h is not None
        if not date_known:
            age_h = UNKNOWN_AGE_H
        if age_h > CONFIG["max_age_hours"]:
            continue
        fresh = 0.5 ** (age_h / CONFIG["half_life_hours"])
        scored.append({
            "lead": lead,
            "also": sorted(pool_outlets - {lead["outlet"]}),
            "mainstream": sorted(base_outlets),
            "rarity": rarity,
            "score": rarity * (0.35 + 0.65 * fresh),
            "age_h": age_h,
            "date_known": date_known,
        })
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored


def select(scored):
    # Greedy pick; each repeat from the same outlet costs 25%, so sources
    # interleave instead of one outlet stacking the top of the page.
    per = Counter()
    picked = []
    left = list(scored)
    while left and len(picked) < CONFIG["max_stories"]:
        left = [s for s in left if per[s["lead"]["outlet"]] < CONFIG["per_outlet_cap"]]
        if not left:
            break
        best = max(left, key=lambda s: s["score"] * 0.75 ** per[s["lead"]["outlet"]])
        left.remove(best)
        per[best["lead"]["outlet"]] += 1
        picked.append(best)
    return picked


def diversity(picked):
    """Evenness of outlets on the page: 100 = perfectly spread, 0 = one outlet."""
    counts = Counter(s["lead"]["outlet"] for s in picked)
    n = sum(counts.values())
    if len(counts) <= 1:
        return {"outlets": len(counts), "regions": 0, "evenness": 0, "top_share": 100 if n else 0}
    h = -sum((c / n) * math.log(c / n) for c in counts.values())
    return {
        "outlets": len(counts),
        "regions": len({s["lead"]["region"] for s in picked}),
        "evenness": round(100 * h / math.log(len(counts))),
        "top_share": round(100 * max(counts.values()) / n),
    }


# ---------- output ----------

def ago(h):
    if h < 1:
        return "under an hour ago"
    if h < 24:
        return f"{int(h)}h ago"
    return f"{int(h // 24)}d ago"


def render(picked, meter, status, now, donate_url=""):
    regions = sorted({s["lead"]["region"] for s in picked})
    cards = []
    for s in picked:
        L = s["lead"]
        notes = []
        if s["also"]:
            notes.append("Also covered by " + ", ".join(html.escape(x) for x in s["also"][:4]))
        if s["mainstream"]:
            notes.append("Mainstream pickup: " + ", ".join(html.escape(x) for x in s["mainstream"]))
        else:
            notes.append("No mainstream pickup")
        when = (f' · <time datetime="{L["date"].isoformat()}">{ago(s["age_h"])}</time>'
                if s["date_known"] else "")
        rare = "rare" if s["rarity"] >= 0.99 else ("uncommon" if s["rarity"] >= 0.5 else "known")
        cards.append(f"""
<article data-region="{html.escape(L['region'])}">
  <div class="meta"><span class="outlet">{html.escape(L['outlet'])}</span> · {html.escape(L['region'])} · {html.escape(L['kind'])}{when}<span class="badge {rare}">{rare}</span></div>
  <h2><a href="{html.escape(L['link'], quote=True)}" rel="noopener noreferrer" target="_blank">{html.escape(L['title'])}</a></h2>
  {f'<p>{html.escape(L["summary"])}</p>' if L['summary'] else ''}
  <div class="notes">{' · '.join(notes)}</div>
</article>""")
    ok = sum(1 for x in status if x["ok"])
    donate = (f' · <a href="{html.escape(donate_url, quote=True)}" rel="noopener">Support Sidelines</a> (every dollar shown publicly)'
              if donate_url.startswith("https://") else "")
    opts = "".join(f'<button data-r="{html.escape(r)}">{html.escape(r)}</button>' for r in regions)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sidelines: news from off the main stage</title>
<meta name="description" content="Open-source, ad-free news aggregator for the stories the big outlets aren't covering.">
<style>
:root{{--bg:#fbfaf7;--fg:#1d1c1a;--mut:#6b675f;--line:#e4e0d8;--acc:#2f5d50}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ebe8e2;--mut:#9a958b;--line:#2c2b28;--acc:#7fb8a4}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 Georgia,'Iowan Old Style',serif}}
header,main,footer{{max-width:760px;margin:0 auto;padding:0 20px}}
header{{padding-top:36px}}h1{{font-size:30px;margin:0;letter-spacing:-.5px}}
.tag{{color:var(--mut);margin:4px 0 20px}}
.meter{{display:flex;gap:22px;flex-wrap:wrap;border:1px solid var(--line);border-radius:10px;padding:14px 18px;font:14px system-ui,sans-serif}}
.meter b{{display:block;font-size:22px;color:var(--acc)}}
.bar{{height:6px;background:var(--line);border-radius:3px;margin-top:6px;width:120px}}.bar i{{display:block;height:100%;background:var(--acc);border-radius:3px}}
nav{{margin:18px 0 6px;display:flex;gap:6px;flex-wrap:wrap}}
nav button{{font:13px system-ui,sans-serif;background:none;border:1px solid var(--line);color:var(--fg);border-radius:20px;padding:4px 11px;cursor:pointer}}
nav button.on{{background:var(--acc);color:var(--bg);border-color:var(--acc)}}
article{{border-bottom:1px solid var(--line);padding:18px 0}}
.meta,.notes{{font:13px system-ui,sans-serif;color:var(--mut)}}.outlet{{color:var(--fg);font-weight:600}}
h2{{font-size:20px;margin:6px 0;line-height:1.3}}h2 a{{color:inherit;text-decoration:none}}h2 a:hover{{text-decoration:underline}}
article p{{margin:4px 0 8px}}
.badge{{margin-left:8px;font-size:11px;padding:1px 7px;border-radius:9px;border:1px solid var(--line)}}
.badge.rare{{color:var(--acc);border-color:var(--acc)}}
footer{{font:13px system-ui,sans-serif;color:var(--mut);padding:30px 20px 50px}}a{{color:var(--acc)}}
</style></head><body>
<header>
<h1>Sidelines</h1>
<p class="tag">News from off the main stage. No ads, no tracking, no algorithmic feed, and never the same ten sources.</p>
<div class="meter" title="How spread out today's page is">
  <div><b>{meter['outlets']}</b>outlets on this page</div>
  <div><b>{meter['regions']}</b>regions</div>
  <div><b>{meter['evenness']}%</b>source evenness<div class="bar"><i style="width:{meter['evenness']}%"></i></div></div>
  <div><b>{meter['top_share']}%</b>biggest single source</div>
</div>
<nav><button class="on" data-r="">All</button>{opts}</nav>
</header>
<main>{''.join(cards) or '<p>No stories this run.</p>'}</main>
<footer>
Updated {now.strftime('%Y-%m-%d %H:%M')} UTC · {ok}/{len(status)} feeds answered ·
Stories that big mainstream outlets are already running get pushed down. Each outlet can place at most {CONFIG['per_outlet_cap']} stories.
Open source. <a href="feed_status.json">Feed status</a> · <a href="data.json">Raw data</a>{donate}
</footer>
<script>
document.querySelectorAll('time[datetime]').forEach(t=>{{
 const h=(Date.now()-new Date(t.getAttribute('datetime')))/36e5;
 t.textContent=h<1?'under an hour ago':h<24?Math.floor(h)+'h ago':Math.floor(h/24)+'d ago';
}});
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{{
 document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('on',x===b));
 document.querySelectorAll('article').forEach(a=>a.style.display=(!b.dataset.r||a.dataset.region===b.dataset.r)?'':'none');
}});
</script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feeds", default=str(ROOT / "feeds.json"))
    ap.add_argument("--out", default=str(ROOT / "docs"))
    args = ap.parse_args()

    cfg = json.loads(Path(args.feeds).read_text(encoding="utf-8"))
    feeds = [dict(f, baseline=False) for f in cfg["pool"]] + \
            [dict(f, baseline=True, region="", kind="mainstream") for f in cfg["baseline"]]

    now = datetime.now(timezone.utc)
    print(f"Fetching {len(feeds)} feeds...")
    items, status = [], []
    for feed, got, err in fetch_all(feeds):
        undated = sum(1 for it in got if item_age_h(it, now) is None)
        status.append({"name": feed["name"], "url": feed["url"], "ok": err is None,
                       "items": len(got), "undated_or_future": undated,
                       "error": err, "baseline": feed["baseline"]})
        mark = "ok " if err is None else "ERR"
        print(f"  [{mark}] {feed['name']:<28} {len(got):>3} items" + (f"  {err}" if err else ""))
        for it in got:
            it.update(outlet=feed["name"], region=feed["region"], kind=feed["kind"],
                      baseline=feed["baseline"], tokens=tokens(it["title"]))
            items.append(it)

    picked = select(score_clusters(cluster(items), now))
    meter = diversity(picked)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render(picked, meter, status, now, cfg.get("donate_url", "")), encoding="utf-8")
    (out / "feed_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    (out / "data.json").write_text(json.dumps({
        "updated": now.isoformat(), "meter": meter,
        "stories": [{"title": s["lead"]["title"], "link": s["lead"]["link"], "outlet": s["lead"]["outlet"],
                     "region": s["lead"]["region"], "also": s["also"], "mainstream": s["mainstream"],
                     "rarity": round(s["rarity"], 3), "score": round(s["score"], 4)} for s in picked],
    }, indent=1), encoding="utf-8")
    (out / ".nojekyll").write_text("")

    bad = [s["name"] for s in status if not s["ok"]]
    print(f"\n{len(items)} items -> {len(picked)} stories on page | "
          f"{meter['outlets']} outlets, {meter['regions']} regions, evenness {meter['evenness']}%")
    if bad:
        print(f"{len(bad)} feeds failed (see docs/feed_status.json): {', '.join(bad)}")
    print(f"Wrote {out / 'index.html'}")
    return 0 if len(bad) < len(status) else 1


if __name__ == "__main__":
    sys.exit(main())
