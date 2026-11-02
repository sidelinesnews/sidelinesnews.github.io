"""Builds fake local feeds (file:// URLs) so the pipeline can be tested offline."""
import json, sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
now = datetime.now(timezone.utc)
def d(h): return format_datetime(now - timedelta(hours=h))

HYPE = "President signs sweeping tariff order targeting electronics imports"
pool = {
 "Indie Africa":  ("Africa", [("Kenyan farmers revive drought-proof sorghum varieties in Turkana", 3),
                              ("Lagos fishermen map illegal trawlers using cheap GPS trackers", 10),
                              (HYPE + " from Asia", 2)]),
 "Asia Weekly":   ("East Asia", [("Taiwan village turns abandoned school into seed library", 5),
                                 ("President signs sweeping tariff order on electronics imports", 1)]),
 "Science Mag":   ("Global", [("Deep-sea microbes found digesting plastic at hydrothermal vents", 6),
                              ("Deep-sea microbes digesting plastic discovered near hydrothermal vents", 8),
                              ("Mathematicians settle decades-old knot conjecture", 30)]),
 "Spammy Outlet": ("Global", [(t, 1) for t in ["Volcano monitoring drones","Regional bakery strike spreads","Glacier lake outburst warning","Chess prodigy beats grandmaster","Library fines abolished citywide","Rare orchid rediscovered highland","Ferry union wage dispute","Desert solar farm lizards"]]),
 "Old News":      ("Europe", [("Ancient story from last month about harbour bridge", 24*20)]),
}
base = {"Big TV": [HYPE, "Celebrity wedding draws crowds downtown"],
        "Big Paper": ["President signs sweeping tariff order targeting electronics", "Stock markets slide on tariff news"]}

def rss(items):
    body = "".join(f"<item><title>{t}</title><link>https://example.org/{abs(hash(t))}</link>"
                   f"<description>&lt;p&gt;Summary of {t}&lt;/p&gt;</description><pubDate>{d(h)}</pubDate></item>" for t, h in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'

def atom(items):
    body = "".join(f'<entry><title>{t}</title><link href="https://example.org/a{i}"/><updated>{(now-timedelta(hours=h)).isoformat()}</updated><summary>s</summary></entry>' for i,(t,h) in enumerate(items))
    return f'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">{body}</feed>'

cfg = {"pool": [], "baseline": []}
for i, (name, (region, items)) in enumerate(pool.items()):
    p = out / f"p{i}.xml"
    p.write_text(atom(items) if name == "Science Mag" else rss(items))
    cfg["pool"].append({"name": name, "url": p.as_uri(), "region": region, "kind": "test"})
for i, (name, titles) in enumerate(base.items()):
    p = out / f"b{i}.xml"; p.write_text(rss([(t, 1) for t in titles]))
    cfg["baseline"].append({"name": name, "url": p.as_uri()})
cfg["pool"].append({"name": "Dead Feed", "url": "file:///nope/missing.xml", "region": "Global", "kind": "test"})
(out / "feeds_test.json").write_text(json.dumps(cfg, indent=1))
print(out / "feeds_test.json")
