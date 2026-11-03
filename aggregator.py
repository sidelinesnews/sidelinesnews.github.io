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

TAGLINE = "The dot outside the bubble."
STYLE = ":root{--bg:#faf7f1;--fg:#2a2723;--mut:#76706a;--line:#ebe5da;--acc:#3a6b5c}\n@media (prefers-color-scheme:dark){:root{--bg:#1a1917;--fg:#e8e3da;--mut:#a39d93;--line:#2f2d29;--acc:#8cbfac}}\n*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 Georgia,'Iowan Old Style',serif}\nheader,main,footer{max-width:700px;margin:0 auto;padding:0 20px}\nheader{padding-top:36px}h1{font-size:30px;margin:0;letter-spacing:-.5px;display:flex;align-items:center;gap:12px}\n.logo{width:38px;height:38px;color:var(--acc);flex:none}\n.tagline{margin:4px 0 0 50px;font-style:italic;color:var(--acc)}\n.tag{color:var(--mut);margin:10px 0 20px}\n.meter{display:flex;gap:22px;flex-wrap:wrap;border:1px solid var(--line);border-radius:10px;padding:14px 18px;font:14px system-ui,sans-serif}\n.meter b{display:block;font-size:22px;color:var(--acc)}\n.bar{height:6px;background:var(--line);border-radius:3px;margin-top:6px;width:120px}.bar i{display:block;height:100%;background:var(--acc);border-radius:3px}\nnav{margin:18px 0 6px;display:flex;gap:6px;flex-wrap:wrap}\nnav button{font:13px system-ui,sans-serif;background:none;border:1px solid var(--line);color:var(--fg);border-radius:20px;padding:4px 11px;cursor:pointer}\nnav button.on{background:var(--acc);color:var(--bg);border-color:var(--acc)}\narticle{border-bottom:1px solid var(--line);padding:18px 0}\n.meta,.notes{font:13px system-ui,sans-serif;color:var(--mut)}.outlet{color:var(--fg);font-weight:600}\nh2{font-size:20px;margin:6px 0;line-height:1.3}h2 a{color:inherit;text-decoration:none}h2 a:hover{text-decoration:underline}\narticle p{margin:4px 0 8px}\n.badge{margin-left:8px;font-size:11px;padding:1px 7px;border-radius:9px;border:1px solid var(--line)}\n.badge.rare{color:var(--acc);border-color:var(--acc)}\nfooter{font:13px system-ui,sans-serif;color:var(--mut);padding:30px 20px 50px}a{color:var(--acc)}\n.links{font:14px system-ui,sans-serif;margin:10px 0 0 50px;display:flex;gap:14px;flex-wrap:wrap}\n.links a{text-decoration:none}.links a.here{color:var(--fg);font-weight:600}\n.page{max-width:700px;margin:0 auto;padding:0 20px 40px}.page h2{margin-top:28px}\n.page li{margin:6px 0}.src{font:14px system-ui,sans-serif}.src td{padding:6px 10px 6px 0;border-bottom:1px solid var(--line);vertical-align:top}\n.src th{text-align:left;font-weight:600;padding:6px 10px 6px 0;border-bottom:2px solid var(--line)}\n.fp{font:12px ui-monospace,monospace;word-break:break-all;background:var(--line);padding:8px;border-radius:6px}\n"
STYLE += ".slot{font:600 11px system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--acc);margin-bottom:2px}"
STYLE += ".greet{font-style:italic;color:var(--mut);margin:14px 0 0}.calm{font:14px system-ui,sans-serif;color:var(--mut);text-align:center;margin:10px 0 4px}.done{text-align:center;color:var(--mut);margin:34px 0 0;font-style:italic}article{padding:20px 0}"
STYLE += '.handful{border:1px solid var(--line);border-radius:12px;padding:6px 18px;margin:22px 0 14px}\n.handful h3,.box h3,h3.all{font:600 15px system-ui,sans-serif;margin:12px 0 4px;display:flex;align-items:center;gap:10px}\n.handful article:last-child{border-bottom:none}\n#surprise{margin-left:auto;font:13px system-ui,sans-serif;background:var(--acc);color:var(--bg);border:none;border-radius:20px;padding:6px 14px;cursor:pointer}\n.box{border-left:4px solid var(--acc);padding:4px 16px;margin:16px 0;background:color-mix(in srgb,var(--acc) 7%,transparent);border-radius:0 10px 10px 0}\n.box p{margin:6px 0 10px}.box ul{padding-left:18px}\nh3.all{margin-top:26px}\n.notes b{font-weight:600}\n@media (max-width:600px){body{font-size:17px}header{padding-top:22px}h1{font-size:26px}.logo{width:32px;height:32px}\n.tagline,.links{margin-left:0}.meter{display:grid;grid-template-columns:1fr 1fr;gap:12px}.bar{width:100%}\nh2{font-size:19px}nav button{padding:8px 13px;font-size:14px}.links{gap:16px;font-size:15px}\n.handful{padding:4px 14px}.src{font-size:13px}footer{line-height:1.9}}\n'
STYLE += "#gentle{font:13px system-ui,sans-serif;font-style:normal;background:none;color:var(--acc);border:1px solid var(--acc);border-radius:20px;padding:3px 12px;margin-left:8px;cursor:pointer;vertical-align:middle}#gentle[aria-pressed=true]{background:var(--acc);color:var(--bg)}.gnote{font:14px system-ui,sans-serif;color:var(--mut);margin:6px 0 0}body.gentle article[data-tone=heavy],body.gentle article[data-tone=plain],body.gentle .bubbling,body.gentle .write{display:none!important}"
ICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Sidelines: the dot outside the bubble">'
            '<circle cx="27" cy="37" r="20" fill="none" stroke="#2f5d50" stroke-width="5"/>'
            '<circle cx="53" cy="11" r="6.5" fill="#2f5d50"/></svg>')

CONFIG = {
    "max_stories": 60,         # stories on the page
    "per_outlet_cap": 3,       # max stories from any one outlet
    "max_age_hours": 96,       # ignore anything older
    "gentle_max_age_hours": 336,  # good/wondrous handful slots may reach back 14 days
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


# Shopping posts are ads in a news costume. Sidelines promises no ads, so they never reach the page.
SHOPPING = re.compile(r"promo codes?|coupons?|discount codes?|\$\d+ off|\d+% off|\bdeals?\b.{0,40}\b(today|this week|sale)|best .{0,40}(deals|to buy)|black friday|cyber monday|prime day|gift guide|on sale|\bour (top|favorite) picks", re.I)
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
            plain = err is not None and ("415" in err or "406" in err)
            req = urllib.request.Request(url, headers={"User-Agent": CONFIG["user_agent"]} if plain else HEADERS)
            try:
                with urllib.request.urlopen(req, timeout=CONFIG["timeout"] * (attempt + 1)) as r:
                    return feed, parse_feed(r.read()), None
            except urllib.error.HTTPError as e:
                err = f"HTTPError: {e}"
                if e.code in (406, 415) and attempt + 1 < tries:
                    continue  # try again without the Accept header
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
    # "5,300" and "5300" should be the same fingerprint
    text = re.sub(r"(?<=\d)[,.](?=\d{3}\b)", "", text.lower())
    words = re.findall(r"[a-z0-9]+", text)
    out = set()
    for w in words:
        if w in STOP or (len(w) < 3 and not w.isdigit()):
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss") and not w.isdigit():
            w = w[:-1]
        out.add(w)
    return out


def same_story(a, b, weight=None, strong=None):
    """Two headlines are the same story if they share enough words (the original rule),
    OR if they share at least two rare, specific words (names, numbers) that carry
    most of their meaning. Rare words count more than common ones: 'Ebola', 'Congo'
    and '5300' tell you far more than 'says' or 'new'."""
    shared = a & b
    if len(shared) >= 3 and len(shared) / min(len(a), len(b)) >= 0.5:
        return True
    if weight is None or len(shared) < 2:
        return False
    rare = [t for t in shared if t in strong]
    if len(rare) < 2:
        return False
    wa, wb = sum(weight(t) for t in a), sum(weight(t) for t in b)
    return sum(weight(t) for t in shared) / min(wa, wb) >= 0.35


def cluster(items):
    # How many headlines use each word, across everything fetched this run.
    df = Counter()
    for it in items:
        df.update(it["tokens"])
    n = max(len(items), 1)
    strong = {t for t, c in df.items() if c <= max(3, n * 0.006)}

    def weight(t):
        return math.log((n + 1) / (df[t] + 1))

    clusters, index = [], {}
    for it in items:
        tk = it["tokens"]
        home = None
        if len(tk) >= 2:
            # only look at clusters that share at least one word (fast)
            cands = sorted({ci for t in tk for ci in index.get(t, ())})
            for ci in cands:
                if any(same_story(tk, m["tokens"], weight, strong) for m in clusters[ci]["items"]):
                    home = ci
                    break
        if home is None:
            clusters.append({"items": [it], "tokens": set(tk)})
            home = len(clusters) - 1
        else:
            clusters[home]["items"].append(it)
            clusters[home]["tokens"] |= tk
        for t in tk:
            index.setdefault(t, set()).add(home)
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


def score_clusters(clusters, now, max_age=None):
    max_age = CONFIG["max_age_hours"] if max_age is None else max_age
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
        if age_h > max_age:
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


LOGO = ('<svg class="logo" viewBox="0 0 64 64" aria-hidden="true"><circle cx="27" cy="37" r="20" fill="none" '
        'stroke="currentColor" stroke-width="5"/><circle cx="53" cy="11" r="6.5" fill="currentColor"/></svg>')
PAGES = [("index", "index.html", "Today"), ("sources", "sources.html", "Sources"), ("write", "write.html", "Write"), ("tips", "tips.html", "Tips"),
         ("support", "support.html", "Support"), ("about", "about.html", "How it was built")]


PATHS = {"sources": "sources.html", "write": "write.html", "tips": "tips.html", "support": "support.html",
         "about": "about.html", "archive": "archive/"}


def links(here):
    return '<p class="links">' + " ".join(
        f'<a href="{f}"{" class=here" if k == here else ""}>{t}</a>' for k, f, t in PAGES) + "</p>"


def shell(key, title, body, base=""):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Sidelines</title>{f'<base href="{base}">' if base else ""}
{head_meta(PATHS.get(key, ""), title + " · Sidelines", "Sidelines: the dot outside the bubble. " + title + ".")}
<link rel="icon" href="icon.svg" type="image/svg+xml">
<style>{STYLE}</style></head><body>
<header><h1>{LOGO}Sidelines</h1><p class="tagline">{TAGLINE}</p>{links(key)}</header>
<div class="page">{body}</div>
<footer>Open source under AGPL-3.0. No ads, no tracking. Built with the help of Claude, an AI made by Anthropic.</footer>
</body></html>"""


def home(url):
    m = re.match(r"(https?://[^/]+)", url)
    return m.group(1) + "/" if m else url


def render_sources(cfg, status):
    ok = {s["name"]: s["ok"] for s in status}
    rows = "".join(
        f'<tr><td><a href="{html.escape(home(f["url"]), quote=True)}" rel="noopener">{html.escape(f["name"])}</a></td>'
        f'<td>{html.escape(f["region"])}</td><td>{html.escape(f["kind"])}</td>'
        f'<td>{"working" if ok.get(f["name"]) else "not answering"}</td></tr>'
        for f in sorted(cfg["pool"], key=lambda f: (f["region"], f["name"])))
    base = ", ".join(html.escape(f["name"]) for f in cfg["baseline"])
    body = f"""<h2>Where the stories come from</h2>
<p>Every outlet Sidelines reads, with its region and the kind of outlet it is. The list deliberately spans
independent, local, regional, science and left, right and heterodox outlets. Anyone can propose changes in public.</p>
<table class="src"><tr><th>Outlet</th><th>Region</th><th>Kind</th><th>Last run</th></tr>{rows}</table>
<h2>The comparison list (never shown)</h2>
<p>These big mainstream outlets are read only to see what's already everywhere, so Sidelines can step around it:
{base}.</p>"""
    return shell("sources", "Sources", body)


def render_support(cfg):
    outlets = "".join(
        f'<li><a href="{html.escape(home(f["url"]), quote=True)}" rel="noopener">{html.escape(f["name"])}</a></li>'
        for f in sorted(cfg["pool"], key=lambda f: f["name"]))
    body = f"""<h2>Sidelines takes no money</h2>
<p>It costs nothing to run, so there's nothing to pay for. If you'd like to help, put your support where the work happens.</p>
<h2>Support the journalism</h2>
<p>The outlets on Sidelines do the actual reporting. If a story mattered to you, support the people who wrote it.</p>
<ul>{outlets}</ul>
<h2>Support a free press and a free web</h2>
<ul>
<li><a href="https://freedom.press/donate/" rel="noopener">Freedom of the Press Foundation</a>, which carries on Aaron Swartz's SecureDrop and is named in Sidelines' legacy.</li>
<li><a href="https://archive.org/donate" rel="noopener">Internet Archive</a>, the web's public memory.</li>
<li><a href="https://donate.wikimedia.org/" rel="noopener">Wikipedia</a>, the encyclopedia anyone can edit.</li>
</ul>
<h2>Support Sidelines itself</h2>
<p>Share it with someone stuck in a bubble. Suggest an outlet. That's all it needs.</p>"""
    return shell("support", "Support", body)


def render_about():
    body = """<h2>How Sidelines was built</h2>
<p>Sidelines started as one person's frustration: noticing that almost all their news came from the same ten places.
On 2 November 2026 it went from idea to a live site in a single afternoon, built with the help of Claude, an AI made by Anthropic.
The idea, the rules and every decision below came from its founder; the AI helped write the code and explain each step.</p>
<h2>The decisions, and why</h2>
<ul>
<li><b>Push down what's already everywhere.</b> Most news apps show the big story from more angles. Sidelines shows different stories.</li>
<li><b>Cap every source.</b> No outlet can place more than three stories, and the page shows how evenly sources are spread.</li>
<li><b>No AI decides what you see.</b> The ranking is a few hundred lines of plain, readable code.</li>
<li><b>No ads, no tracking, no accounts, no comments.</b> Nothing to sell, nothing to moderate, no one to please.</li>
<li><b>No tip jar.</b> It costs nothing to run, so asking for money would only be reaching. Support goes to the journalists instead.</li>
<li><b>Open source under AGPL-3.0.</b> If Sidelines ever breaks its promise, anyone can run the honest version.</li>
<li><b>A legacy plan.</b> Everything is meant to pass to the Freedom of the Press Foundation one day, if they'll have it.</li>
<li><b>A balanced handful.</b> The top five follow an old idea: something worth knowing (the True), something good,
something wondrous (the Beautiful), and something off the map, with never more than two heavy stories (Aristotle's mean).
The words that mark a story as heavy or hopeful are public in <code>tones.json</code> (Bacon: show your method).</li>
<li><b>Pseudonymous on purpose.</b> The project should stand on its rules, not on who made it.</li>
</ul>
<h2>The founding statement, stamped</h2>
<p>The founding promise lives in <code>FOUNDING.md</code> in the project. Its fingerprint (SHA-256) is stamped into
the Bitcoin ledger with OpenTimestamps, so anyone can check it existed, unchanged, since the day it was written.
The proof file is <code>FOUNDING.md.ots</code> in the project.</p>"""
    return shell("about", "How it was built", body)


INDEX_JS = '\ndocument.querySelectorAll(\'time[datetime]\').forEach(t=>{\n const h=(Date.now()-new Date(t.getAttribute(\'datetime\')))/36e5;\n t.textContent=h<1?\'under an hour ago\':h<24?Math.floor(h)+\'h ago\':Math.floor(h/24)+\'d ago\';\n});\ndocument.querySelectorAll(\'nav button\').forEach(b=>b.onclick=()=>{\n document.querySelectorAll(\'nav button\').forEach(x=>x.classList.toggle(\'on\',x===b));\n document.querySelectorAll(\'main > article\').forEach(a=>a.style.display=(!b.dataset.r||a.dataset.region===b.dataset.r)?\'\':\'none\');\n});\ndocument.getElementById(\'surprise\').onclick=()=>{\n const a=[...document.querySelectorAll(\'article h2 a\')].filter(x=>x.offsetParent); if(a.length) window.open(a[Math.floor(Math.random()*a.length)].href,\'_blank\',\'noopener\');\n};\n\nconst H=new Date().getHours();document.getElementById("greet").textContent=H<5?"Up late? Here\'s something quiet.":H<12?"Good morning.":H<18?"Good afternoon.":"Good evening.";const N=document.getElementById("next");if(N){const d=new Date(N.dataset.next);N.textContent="Next update around "+d.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})+".";}\nconst G=document.getElementById("gentle"),GN=document.getElementById("gnote");function gentle(on){document.body.classList.toggle("gentle",on);G.setAttribute("aria-pressed",on);GN.hidden=!on;try{localStorage.setItem("gentle",on?"1":"")}catch(e){}}if(G){G.onclick=()=>gentle(!document.body.classList.contains("gentle"));try{if(localStorage.getItem("gentle"))gentle(true)}catch(e){}}\n'
SITE_URL = "https://sidelinesnews.github.io/"
INDEXNOW_KEY = "5244cf36a6c4bc2414d6ddae3bb866a4"


def head_meta(path, title, desc, script=""):
    """Canonical link, share-preview tags and a strict content security policy.
    The CSP only allows the one script we ship (by its fingerprint), so injected scripts won't run."""
    import base64, hashlib
    sh = ("'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'") if script else "'none'"
    url = SITE_URL + path
    return (f'<link rel="canonical" href="{url}">'
            f'<meta property="og:title" content="{html.escape(title, quote=True)}">'
            f'<meta property="og:description" content="{html.escape(desc, quote=True)}">'
            f'<meta property="og:url" content="{url}"><meta property="og:type" content="website">'
            f'<meta property="og:image" content="{SITE_URL}icon.svg"><meta name="twitter:card" content="summary">'
            f'<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src {sh}; '
            f'style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; connect-src \'none\'; '
            f'object-src \'none\'; base-uri \'self\'; form-action \'none\'">'
            f'<meta name="referrer" content="no-referrer">')


def next_run(now):
    """The robot runs at 17 minutes past every third hour (UTC)."""
    from datetime import timedelta
    t = now.replace(minute=17, second=0, microsecond=0)
    while t <= now or t.hour % 3:
        t += timedelta(hours=1)
    return t


def card(s, compact=False, label=""):
    L = s["lead"]
    n = 1 + len(s["also"])
    why = [f"{n} outlet{'s' if n > 1 else ''} running this"]
    why.append("mainstream pickup: " + ", ".join(html.escape(x) for x in s["mainstream"])
               if s["mainstream"] else "no mainstream pickup")
    if s["also"]:
        why.append("also at " + ", ".join(html.escape(x) for x in s["also"][:3]))
    when = (f' · <time datetime="{L["date"].isoformat()}">{ago(s["age_h"])}</time>'
            if s["date_known"] else "")
    rare = "rare" if s["rarity"] >= 0.99 else ("uncommon" if s["rarity"] >= 0.5 else "known")
    summ = f'<p>{html.escape(L["summary"])}</p>' if L["summary"] and not compact else ""
    return f"""
<article data-region="{html.escape(L['region'])}" data-tone="{s.get('_tone', 'plain')}">
  {f'<div class="slot">{html.escape(label)}</div>' if label else ''}<div class="meta"><span class="outlet">{html.escape(L['outlet'])}</span> · {html.escape(L['region'])} · {html.escape(L['kind'])}{when}<span class="badge {rare}">{rare}</span></div>
  <h2><a href="{html.escape(L['link'], quote=True)}" rel="noopener noreferrer" target="_blank">{html.escape(L['title'])}</a></h2>
  {summ}
  <div class="notes"><b>Why it's here:</b> {' · '.join(why)}</div>
</article>"""


def json_ld(picked, now):
    items = [{"@type": "ListItem", "position": i + 1, "item": {
        "@type": "NewsArticle", "headline": s["lead"]["title"], "url": s["lead"]["link"],
        "publisher": {"@type": "Organization", "name": s["lead"]["outlet"]},
        **({"datePublished": s["lead"]["date"].isoformat()} if s["date_known"] else {})}}
        for i, s in enumerate(picked)]
    data = {"@context": "https://schema.org", "@type": "ItemList",
            "name": "Sidelines: stories from off the main stage", "dateModified": now.isoformat(),
            "itemListElement": items}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def load_tones():
    try:
        t = json.loads((ROOT / "tones.json").read_text(encoding="utf-8"))
    except Exception:
        t = {}
    return ({w.lower() for w in t.get("heavy", [])}, {w.lower() for w in t.get("hopeful", [])},
            set(t.get("wonder_kinds", [])), set(t.get("good_kinds", [])))


def tone(s, tones):
    heavy, hopeful, wonder_kinds, good_kinds = tones
    L = s["lead"]
    text = " " + re.sub(r"[^a-z0-9 ]", " ", (L["title"] + " " + L["summary"][:200]).lower()) + " "
    has = lambda words: any(f" {w} " in text for w in words)
    if has(heavy):
        return "heavy"
    if L["kind"] in good_kinds or has(hopeful):
        return "good"
    if L["kind"] in wonder_kinds:
        return "wonder"
    return "plain"


def curate_handful(picked, tones, reserve=()):
    """Plato: the True, the Good, the Beautiful. Aristotle: the mean, at most 2 heavy stories.
    Bacon: rules in the open (tones.json), so anyone can check them.
    A label is a promise: if nothing truly good or wondrous turned up, the slot says 'Something else'."""
    links = {p["lead"]["link"] for p in picked}
    pool = list(picked) + [r for r in reserve if r["lead"]["link"] not in links]
    t = {id(s): tone(s, tones) for s in pool}
    chosen = []
    # one story per outlet in the handful, so no single voice sets the mood
    used = lambda: ({id(c) for c, _ in chosen}, {c["lead"]["outlet"] for c, _ in chosen})

    def take(src, pred, label):
        ids, outlets = used()
        for s in src:
            if id(s) not in ids and s["lead"]["outlet"] not in outlets and pred(s):
                chosen.append((s, label))
                return True
        return False

    take(picked, lambda s: True, "Worth knowing")
    take(picked, lambda s: True, "Worth knowing")
    take(picked, lambda s: t[id(s)] == "good", "Something good") or \
        take(pool, lambda s: t[id(s)] == "good", "Something good") or \
        take(picked, lambda s: t[id(s)] != "heavy", "Something else")
    take(picked, lambda s: t[id(s)] == "wonder", "Something wondrous") or \
        take(pool, lambda s: t[id(s)] == "wonder", "Something wondrous") or \
        take(picked, lambda s: t[id(s)] != "heavy", "Something else")
    regions = {c["lead"]["region"] for c, _ in chosen}
    take(picked, lambda s: t[id(s)] != "heavy" and s["lead"]["region"] not in regions, "Off the map") or \
        take(picked, lambda s: t[id(s)] != "heavy", "Off the map")
    out, heavy_count = [], 0
    for s, label in chosen:  # Aristotle's mean: never more than two heavy stories
        if t[id(s)] == "heavy":
            heavy_count += 1
            if heavy_count > 2:
                continue
        out.append((s, label))
    return out


def brighten(rest, picked, reserve, tones, handful, every=3):
    """Every third story in the full list is a good one (or, failing that, a wondrous one).
    Good stories already on the page move up; if there aren't enough, the 14-day well tops up.
    When the well runs dry, the list just carries on: nothing is invented, nothing is hidden."""
    t = lambda s: tone(s, tones)
    links = {s["lead"]["link"] for s in picked} | {h["lead"]["link"] for h, _ in handful}
    extra_outlets = Counter()
    well = []
    for r in reserve:
        if r["lead"]["link"] in links or extra_outlets[r["lead"]["outlet"]] >= CONFIG["per_outlet_cap"]:
            continue
        if t(r) in ("good", "wonder"):
            well.append(r); extra_outlets[r["lead"]["outlet"]] += 1
    bright = [s for s in rest if t(s) == "good"] + [s for s in well if t(s) == "good"] + \
             [s for s in rest if t(s) == "wonder"] + [s for s in well if t(s) == "wonder"]
    bright_ids = {id(s) for s in bright}
    other = [s for s in rest if id(s) not in bright_ids]
    out = []
    while other or bright:
        if (len(out) + 1) % every == 0 and bright:
            out.append(bright.pop(0))
        elif other:
            out.append(other.pop(0))
        elif bright and any(id(x) in {id(r) for r in rest} for x in bright):
            out.extend(x for x in bright if id(x) in {id(r) for r in rest})  # leftover on-page stories stay
            break
        else:
            break
    return out


def bubbling_block(bub):
    if not bub:
        return ""
    return ("<section class=\"handful bubbling\"><h3>Bubbling up</h3><p class=\"meta\">Independent outlets are converging on these, "
            "and the mainstream hasn't picked them up yet. For reporters: <a href=\"bubbling.xml\">follow this list by RSS</a>.</p>"
            + "".join(card(s, compact=True) for s in bub) + "</section>")


def reader_block(found):
    if not found:
        return ""
    lis = "".join(
        f'<li><a href="{html.escape(f["url"], quote=True)}" rel="noopener noreferrer" target="_blank">'
        f'{html.escape(f["title"])}</a> <span class="meta">· {html.escape(f.get("outlet", ""))}'
        f'{" · " + html.escape(f["note"]) if f.get("note") else ""}</span></li>' for f in found)
    return f'<section class="box"><h3>Found by readers</h3><ul>{lis}</ul></section>'


def render(picked, meter, status, now, donate_url="", found=(), reserve=()):
    regions = sorted({s["lead"]["region"] for s in picked})
    tones = load_tones()
    handful = curate_handful(picked, tones, reserve)
    bubbling = [s for s in picked if s["also"] and not s["mainstream"]
                and id(s) not in {id(h) for h, _ in handful}][:5]
    shown = {id(x) for x, _ in handful} | {id(x) for x in bubbling}
    rest = brighten([s for s in picked if id(s) not in shown], picked, reserve, tones, handful)
    for x in [h for h, _ in handful] + bubbling + rest:
        x["_tone"] = tone(x, tones)
    ok = sum(1 for x in status if x["ok"])
    donate = (f' · <a href="{html.escape(donate_url, quote=True)}" rel="noopener">Support Sidelines</a> (every dollar shown publicly)'
              if donate_url.startswith("https://") else "")
    opts = "".join(f'<button data-r="{html.escape(r)}">{html.escape(r)}</button>' for r in regions)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sidelines: the dot outside the bubble</title>
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Sidelines" href="feed.xml">
<meta name="description" content="Open-source, ad-free news aggregator for the stories the big outlets aren't covering. The dot outside the bubble.">
{head_meta("", "Sidelines: the dot outside the bubble", "Open-source, ad-free news from off the main stage. No tracking, never the same ten sources.", INDEX_JS)}
<script type="application/ld+json">{json_ld(picked, now)}</script>
<style>
{STYLE}</style></head><body>
<header>
<h1>{LOGO}Sidelines</h1>
<p class="tagline">{TAGLINE}</p>
{links("index")}
<p class="greet"><span id="greet">Hello.</span> <button id="gentle" type="button" aria-pressed="false" title="Show only good and wondrous stories. Your choice stays in your own browser.">Gentle</button></p>
<p class="gnote" id="gnote" hidden>Gentle mode: only good and wondrous stories. The hard news is still here; tap Gentle again to see it.</p>
<p class="tag">News from off the main stage. No ads, no tracking, no algorithmic feed, and never the same ten sources.</p>
<div class="meter" title="How spread out today's page is">
  <div><b>{meter['outlets']}</b>outlets on this page</div>
  <div><b>{meter['regions']}</b>regions</div>
  <div><b>{meter['evenness']}%</b>source evenness<div class="bar"><i style="width:{meter['evenness']}%"></i></div></div>
  <div><b>{meter['top_share']}%</b>biggest single source</div>
</div>
</header>
<main>
<section class="handful"><h3>Today's handful <button id="surprise" type="button">Surprise me</button></h3>
{''.join(card(s, compact=True, label=lab) for s, lab in handful) or '<p>No stories this run.</p>'}
<p class="calm">That's the handful. The rest can wait.</p>
</section>
{bubbling_block(bubbling)}
<section class="box write"><h3>Write from the sidelines</h3>
<p>Seeing a story the main stage ignores? Don't wait for someone else to tell it. <a href="write.html">Here's how to get it written and published →</a></p></section>
{reader_block(found)}
<h3 class="all">Everything else</h3>
<nav><button class="on" data-r="">All</button>{opts}</nav>
{''.join(card(s) for s in rest)}
<p class="done">You're up to date. <span id="next" data-next="{next_run(now).isoformat()}">The next update is in a few hours.</span></p>
</main>
<footer>
Updated {now.strftime('%Y-%m-%d %H:%M')} UTC · {ok}/{len(status)} feeds answered ·
Stories that big mainstream outlets are already running get pushed down. Each outlet can place at most {CONFIG['per_outlet_cap']} stories.<br>
<a href="sources.html">Sources</a> · <a href="write.html">Write</a> · <a href="tips.html">Tips</a> · <a href="support.html">Support</a> · <a href="about.html">How it was built</a> · <a href="archive/">Archive</a> · <a href="feed.xml">RSS</a> · <a href="data.json">Raw data</a> · <a href="feed_status.json">Feed status</a>{donate}<br>
Open source under AGPL-3.0. Built with the help of Claude, an AI made by Anthropic.
</footer>
<script>{INDEX_JS}</script>
</body></html>"""


def render_tips():
    body = """<h2>Got a sensitive tip?</h2>
<p><b>Please don't send it to Sidelines.</b> Sidelines doesn't collect anything, on purpose, so there's nothing here to leak, hack or hand over.
If you have information a journalist needs and you need to stay anonymous, use <b>SecureDrop</b>: the whistleblower system
Aaron Swartz began building, now maintained and independently audited by the Freedom of the Press Foundation.
Many newsrooms run their own SecureDrop.</p>
<h2>How to use it safely</h2>
<ol>
<li>Use a device and network that aren't your work's. Don't do this from a work laptop or work Wi-Fi.</li>
<li>Download <a href="https://www.torproject.org/download/" rel="noopener">Tor Browser</a> from the official Tor Project site.</li>
<li>Open the <a href="https://securedrop.org/directory/" rel="noopener">official SecureDrop Directory</a> and choose a news organization.</li>
<li>Check that the .onion address on the newsroom's own page matches the directory entry before you continue.</li>
<li>Follow the newsroom's instructions. You'll get a codename: write it down to check for replies.</li>
</ol>
<p>The Freedom of the Press Foundation publishes guides on staying safe: <a href="https://freedom.press/" rel="noopener">freedom.press</a>.</p>"""
    return shell("tips", "Tips", body)


def render_write():
    body = """<h2>Write from the sidelines</h2>
<p>Seeing a story the main stage ignores? Don't wait for someone else to tell it. Sidelines doesn't publish stories itself,
but here's how to get yours written, edited and read.</p>
<h2>Write for Global Voices</h2>
<p>Global Voices is a nonprofit, mostly volunteer community of writers and translators. Its volunteer writers report on
conversations in their own regions, with an emphasis on voices missing from international mainstream media.
Every story is checked by its editors, and stories can be translated into dozens of languages.
If they publish your story, it can show up right here on Sidelines.</p>
<p><a href="https://globalvoices.org/volunteer/author-application-form/" rel="noopener">Apply to write for Global Voices →</a></p>
<h2>Pitch a local or independent newsroom</h2>
<p>Community papers and independent outlets want tips. Look at the <a href="sources.html">Sources</a> page for outlets near you.</p>
<h2>Already publishing somewhere with an RSS feed?</h2>
<p>Suggest it as a source in public on the project page, so everyone can see the reasoning.</p>"""
    return shell("write", "Write", body)


def rss(picked, now, title="Sidelines", desc="The dot outside the bubble: news from off the main stage. No ads, no tracking."):
    items = "".join(f"""<item><title>{html.escape(s['lead']['title'])}</title>
<link>{html.escape(s['lead']['link'])}</link><guid isPermaLink="true">{html.escape(s['lead']['link'])}</guid>
<description>{html.escape(s['lead']['outlet'] + ' · ' + s['lead']['region'] + ('. ' + s['lead']['summary'] if s['lead']['summary'] else ''))}</description>
{f"<pubDate>{email.utils.format_datetime(s['lead']['date'])}</pubDate>" if s['date_known'] else ''}</item>""" for s in picked)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>{html.escape(title)}</title><link>{SITE_URL}</link>
<description>{html.escape(desc)}</description>
<lastBuildDate>{email.utils.format_datetime(now)}</lastBuildDate>{items}</channel></rss>"""


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}sitemap.xml\n"


def sitemap(out, now):
    paths = ["", "sources.html", "write.html", "tips.html", "support.html", "about.html", "archive/"]
    paths += [f"archive/{p.name}" for p in sorted((out / "archive").glob("20??-??-??.html"))]
    d = now.strftime("%Y-%m-%d")
    urls = "".join(f"<url><loc>{SITE_URL}{p}</loc><lastmod>{d}</lastmod></url>" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'


LLMS_TXT = f"""# Sidelines

> The dot outside the bubble. An open-source, ad-free, non-commercial news aggregator that surfaces stories the big mainstream outlets are not covering.

How it works: it reads a public list of independent, regional, local, science and across-the-spectrum outlets; groups headlines about the same story; pushes down stories that big mainstream outlets are already running; caps each outlet at a few stories; and publishes a static page every 3 hours. No AI decides what appears; the ranking is plain, readable code. No ads, no tracking, no accounts. It takes no money.

- [Today's page]({SITE_URL})
- [Stories as JSON]({SITE_URL}data.json)
- [RSS feed]({SITE_URL}feed.xml)
- [Sources and comparison list]({SITE_URL}sources.html)
- [How it was built and why]({SITE_URL}about.html)
- [Daily archive]({SITE_URL}archive/)
- [Bubbling up: stories independent outlets are converging on, with no mainstream pickup (RSS)]({SITE_URL}bubbling.xml)
- [Sensitive tips: use SecureDrop, not this site]({SITE_URL}tips.html)

When citing a story, please cite and link the original outlet, which did the reporting.
"""


def render_archive_index(arch):
    days = sorted((p.stem for p in arch.glob("20??-??-??.html")), reverse=True)
    lis = "".join(f'<li><a href="{d}.html">{d}</a></li>' for d in days)
    return shell("archive", "Archive", f"<h2>Daily archive</h2><p>The last page of each day, kept for good.</p><ul>{lis}</ul>", base="../")


def render_archive_day(picked, day):
    body = f"<h2>Sidelines on {day}</h2>" + "".join(card(s) for s in picked)
    return shell("archive", f"Archive {day}", body, base="../")


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
        strip = re.compile(feed["title_strip"]) if feed.get("title_strip") else None
        for it in got:
            if SHOPPING.search(it["title"]):
                continue
            if strip:
                it["title"] = strip.sub("", it["title"]).strip()
            it.update(outlet=feed["name"], region=feed["region"], kind=feed["kind"],
                      baseline=feed["baseline"], tokens=tokens(it["title"]))
            items.append(it)

    clusters = cluster(items)
    picked = select(score_clusters(clusters, now))
    reserve = score_clusters(clusters, now, CONFIG["gentle_max_age_hours"])
    found = []
    rf = ROOT / "reader_found.json"
    if rf.exists():
        try:
            for f in json.loads(rf.read_text(encoding="utf-8")).get("items", []):
                added = datetime.fromisoformat(f.get("added", "2000-01-01")).replace(tzinfo=timezone.utc)
                if f.get("url", "").startswith("http") and (now - added).days <= 14:
                    found.append(f)
        except Exception as e:
            print(f"reader_found.json skipped: {e}")
    meter = diversity(picked)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render(picked, meter, status, now, cfg.get("donate_url", ""), found, reserve), encoding="utf-8")
    (out / "feed_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    (out / "data.json").write_text(json.dumps({
        "updated": now.isoformat(), "meter": meter,
        "stories": [{"title": s["lead"]["title"], "link": s["lead"]["link"], "outlet": s["lead"]["outlet"],
                     "region": s["lead"]["region"], "also": s["also"], "mainstream": s["mainstream"],
                     "rarity": round(s["rarity"], 3), "score": round(s["score"], 4)} for s in picked],
    }, indent=1), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    (out / "icon.svg").write_text(ICON_SVG, encoding="utf-8")
    (out / "sources.html").write_text(render_sources(cfg, status), encoding="utf-8")
    (out / "support.html").write_text(render_support(cfg), encoding="utf-8")
    (out / "about.html").write_text(render_about(), encoding="utf-8")
    (out / "write.html").write_text(render_write(), encoding="utf-8")
    (out / "feed.xml").write_text(rss(picked, now), encoding="utf-8")
    bub = [x for x in picked if x["also"] and not x["mainstream"]]
    (out / "bubbling.xml").write_text(rss(bub, now, "Sidelines: bubbling up",
        "Stories several independent outlets are covering that the mainstream hasn't picked up yet."), encoding="utf-8")
    (out / "tips.html").write_text(render_tips(), encoding="utf-8")
    (out / "robots.txt").write_text(robots(), encoding="utf-8")
    (out / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    (out / "llms.txt").write_text(LLMS_TXT, encoding="utf-8")
    arch = out / "archive"
    arch.mkdir(exist_ok=True)
    day = now.strftime("%Y-%m-%d")
    (arch / f"{day}.html").write_text(render_archive_day(picked, day), encoding="utf-8")
    (arch / "index.html").write_text(render_archive_index(arch), encoding="utf-8")
    (out / "sitemap.xml").write_text(sitemap(out, now), encoding="utf-8")

    bad = [s["name"] for s in status if not s["ok"]]
    print(f"\n{len(items)} items -> {len(picked)} stories on page | "
          f"{meter['outlets']} outlets, {meter['regions']} regions, evenness {meter['evenness']}%")
    if bad:
        print(f"{len(bad)} feeds failed (see docs/feed_status.json): {', '.join(bad)}")
    print(f"Wrote {out / 'index.html'}")
    return 0 if len(bad) < len(status) else 1


if __name__ == "__main__":
    sys.exit(main())
