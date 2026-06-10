#!/usr/bin/env python3
"""Scraper for Þróttur matches on urslit.tmmotid.is (TM Mótið í Eyjum).

Implements §2.1 of the README: fetches a day page, parses the results
table, unescapes HTML entities and filters for Þróttur teams. Reusable
for Friday/Saturday once those schedules are published — use --probe to
discover which day codes are populated.

Examples:
    python3 scrape.py                  # Thursday (day=A), Þróttur only
    python3 scrape.py --day B          # another day code
    python3 scrape.py --probe          # find populated day codes
    python3 scrape.py --json           # machine-readable output
    python3 scrape.py --team Fjölnir   # different team filter
    python3 scrape.py --all-teams      # full schedule, no filter

No dependencies beyond the Python 3 standard library.
"""

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request

BASE_URL = "https://urslit.tmmotid.is/index"
DEFAULT_TEAM = "Þróttur"
# A populated day page is ≫ 10 KB and contains a results <table>;
# unpublished days return a ~5 KB shell page.
MIN_POPULATED_BYTES = 10_000

ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "throttur-akstursplan-scraper"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(cell):
    return html.unescape(TAG_RE.sub("", cell)).strip()


def parse_matches(page):
    """Yield one dict per match row: Riðill | Tími | Völlur | Lið 1 | Lið 2 | Úrslit x2."""
    matches = []
    for row in ROW_RE.findall(page):
        cells = [clean(c) for c in CELL_RE.findall(row)]
        if len(cells) < 5:
            continue
        # Guard against header/filler rows: time cell must look like HH:MM.
        if not re.fullmatch(r"\d{1,2}:\d{2}", cells[1]):
            continue
        matches.append({
            "ridill": cells[0],
            "time": cells[1],
            "venue": cells[2],
            "home": cells[3],
            "away": cells[4],
            "score_home": cells[5] if len(cells) > 5 else "",
            "score_away": cells[6] if len(cells) > 6 else "",
        })
    return matches


def filter_team(matches, team):
    """Keep matches involving `team`; annotate with our side and opponent."""
    out = []
    for m in matches:
        if team in m["home"]:
            side, opponent = m["home"], m["away"]
        elif team in m["away"]:
            side, opponent = m["away"], m["home"]
        else:
            continue
        out.append({**m, "team": side, "opponent": opponent})
    out.sort(key=lambda m: (m["team"], m["time"]))
    return out


def probe(day_codes):
    """Report which day codes serve a populated schedule."""
    results = []
    for code in day_codes:
        url = f"{BASE_URL}?day={code}"
        try:
            page = fetch(url)
        except (urllib.error.URLError, OSError) as e:
            results.append((code, f"error: {e}"))
            continue
        n = len(parse_matches(page))
        if len(page.encode()) >= MIN_POPULATED_BYTES and n:
            results.append((code, f"POPULATED — {n} matches"))
        else:
            results.append((code, f"empty ({len(page.encode())} bytes)"))
    return results


def print_table(matches, team):
    if not matches:
        print(f"No matches found for '{team}'.", file=sys.stderr)
        return
    current = None
    for m in matches:
        if m["team"] != current:
            current = m["team"]
            print(f"\n{current}")
        score = f"  {m['score_home']}-{m['score_away']}" if m["score_home"] else ""
        print(f"  {m['time']}  {m['venue']:<18}  vs {m['opponent']}  ({m['ridill']}){score}")


def main():
    ap = argparse.ArgumentParser(description="Scrape Þróttur matches from urslit.tmmotid.is")
    ap.add_argument("--day", default="A", help="day code, e.g. A = fimmtudagur (default: A)")
    ap.add_argument("--team", default=DEFAULT_TEAM, help=f"team name filter (default: {DEFAULT_TEAM})")
    ap.add_argument("--all-teams", action="store_true", help="no team filter, dump the full schedule")
    ap.add_argument("--json", action="store_true", help="output JSON instead of a table")
    ap.add_argument("--probe", action="store_true", help="probe day codes A–H for published schedules")
    args = ap.parse_args()

    if args.probe:
        for code, status in probe("ABCDEFGH"):
            print(f"day={code}: {status}")
        return

    page = fetch(f"{BASE_URL}?day={args.day}")
    matches = parse_matches(page)
    if not args.all_teams:
        matches = filter_team(matches, args.team)

    if args.json:
        json.dump(matches, sys.stdout, ensure_ascii=False, indent=2)
        print()
    elif args.all_teams:
        for m in matches:
            score = f"  {m['score_home']}-{m['score_away']}" if m["score_home"] else ""
            print(f"{m['time']}  {m['venue']:<18}  {m['home']} vs {m['away']}  ({m['ridill']}){score}")
    else:
        print_table(matches, args.team)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # Output piped to e.g. `head` — exit quietly.
        sys.exit(0)
