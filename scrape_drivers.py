#!/usr/bin/env python3
"""Scraper for the drivers roster and shift signups from the shared
"Bílstjóravaktir og nestisnefnd" Google Sheet.

Reads the first two sheets via the public xlsx export endpoint:
  1. "Bílstjóravaktir og nestisnefnd" — driver roster (name, phone,
     daughter, lið) per §3 of the README.
  2. "Bilstjóra plan" — per-day shift signups (Fimmtudagur, Föstudagur,
     Laugardagur), Herjólfur ferry drivers and the accommodation note.

Reusable for subsequent days: rerun before generating each day's plan to
pick up the latest signups. The legacy section below the "Ekki nota!"
marker on sheet 2 is ignored.

Examples:
    python3 scrape_drivers.py            # human-readable summary
    python3 scrape_drivers.py --json     # machine-readable output

No dependencies beyond the Python 3 standard library.
"""

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

SPREADSHEET_ID = "1HyWgXXJ4YRu6ijjLCrt-WWWFdRg7l3-H"
EXPORT_URL = "https://docs.google.com/spreadsheets/d/{id}/export?format=xlsx"

ROSTER_SHEET = "Bílstjóravaktir og nestisnefnd"
PLAN_SHEET = "Bilstjóra plan"
DAYS = ("Fimmtudagur", "Föstudagur", "Laugardagur")

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
TIME_RANGE_RE = re.compile(r"\d{1,2}:\d{2}\s*-")


def fetch_workbook(spreadsheet_id):
    url = EXPORT_URL.format(id=spreadsheet_id)
    req = urllib.request.Request(url, headers={"User-Agent": "throttur-akstursplan-scraper"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return zipfile.ZipFile(BytesIO(resp.read()))


def col_to_idx(ref):
    n = 0
    for ch in ref:
        if ch.isdigit():
            break
        n = n * 26 + ord(ch) - 64
    return n - 1


def load_sheets(z):
    """Return {sheet name: grid} where grid is {(row, col): value}."""
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))

    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid2target = {
        rel.get("Id"): rel.get("Target").lstrip("/")
        for rel in rels
    }

    sheets = {}
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    for sheet in wb.find("m:sheets", NS):
        name = sheet.get("name")
        target = rid2target[sheet.get(REL_NS)]
        if not target.startswith("xl/"):
            target = "xl/" + target
        grid = {}
        ws = ET.fromstring(z.read(target))
        for c in ws.iter(f"{{{NS['m']}}}c"):
            ref = c.get("r")
            t = c.get("t")
            if t == "inlineStr":
                val = "".join(n.text or "" for n in c.iter(f"{{{NS['m']}}}t"))
            else:
                v = c.find("m:v", NS)
                if v is None or v.text is None:
                    continue
                val = shared[int(v.text)] if t == "s" else v.text
            val = val.strip()
            if val:
                row = int(re.search(r"\d+", ref).group())
                grid[(row, col_to_idx(ref))] = val
        sheets[name] = grid
    return sheets


def clean_phone(raw):
    """'6661313.0' / '695-9582' → '6959582'-style digit string."""
    digits = re.sub(r"\.0$", "", raw)
    digits = re.sub(r"\D", "", digits)
    return digits or None


def parse_roster(grid):
    """Rows below the 'Bílstjóri' header: name | phone | daughter | lið."""
    header_row = next(r for (r, c), v in grid.items() if c == 0 and v == "Bílstjóri")
    drivers = []
    for row in range(header_row + 1, header_row + 40):
        name = grid.get((row, 0))
        lid = grid.get((row, 3))
        if not name or not lid:
            continue
        drivers.append({
            "name": name,
            "phone": clean_phone(grid.get((row, 1), "")),
            "daughter": grid.get((row, 2)),
            "lid": int(float(lid)),
        })
    return drivers


def parse_plan(grid):
    """Day blocks: header row '<Day> | Bíll 1 | ... | Bíll 2', then
    time-range rows with name/phone pairs in cols B/C (Bíll 1) and D/E
    (Bíll 2). Everything from the 'Ekki nota!' marker down is legacy."""
    cutoff = min(
        (r for (r, c), v in grid.items() if "Ekki nota" in v),
        default=10**9,
    )

    def driver_at(row, col):
        name = grid.get((row, col))
        if not name:
            return None
        return {"name": name, "phone": clean_phone(grid.get((row, col + 1), ""))}

    plan = {}
    for (r, c), v in sorted(grid.items()):
        if c != 0 or v not in DAYS or r >= cutoff:
            continue
        shifts = []
        for row in range(r + 1, r + 10):
            label = grid.get((row, 0), "")
            if not TIME_RANGE_RE.match(label):
                break
            shifts.append({
                "shift": label,
                "bill1": driver_at(row, 1),
                "bill2": driver_at(row, 3),
            })
        plan[v] = shifts
    return plan


def parse_extras(grid):
    """Ferry drivers (under 'Bílstjóri í Herjólf...') and gisting note."""
    extras = {"ferry": {}, "gisting": None}
    for (r, c), v in sorted(grid.items()):
        if v.startswith("Bílstjóri í Herjólf"):
            for row in range(r + 1, r + 4):
                car = grid.get((row, c))
                if car in ("Bíll 1", "Bíll 2"):
                    extras["ferry"][car] = grid.get((row, c + 1))
        if v == "Gisting:":
            extras["gisting"] = grid.get((r + 1, c))
    return extras


def print_summary(data):
    print("Bílstjórar (roster):")
    for d in data["drivers"]:
        print(f"  lið {d['lid']}: {d['name']:<10} {d['phone'] or '—':<8} ({d['daughter']})")
    for day, shifts in data["plan"].items():
        print(f"\n{day}:")
        if not shifts:
            print("  (engar vaktir skráðar)")
        for s in shifts:
            def fmt(side):
                return f"{side['name']} ({side['phone']})" if side else "— ÓSKRÁÐ —"
            print(f"  {s['shift']:<12} Bíll 1: {fmt(s['bill1']):<24} Bíll 2: {fmt(s['bill2'])}")
    if data["ferry"]:
        print("\nHerjólfur (ferja bílana):")
        for car, who in data["ferry"].items():
            print(f"  {car}: {who}")
    if data["gisting"]:
        print(f"\nGisting: {data['gisting']}")


def main():
    ap = argparse.ArgumentParser(description="Scrape drivers and shift plan from the shared sheet")
    ap.add_argument("--id", default=SPREADSHEET_ID, help="Google spreadsheet id")
    ap.add_argument("--json", action="store_true", help="output JSON instead of a summary")
    args = ap.parse_args()

    sheets = load_sheets(fetch_workbook(args.id))
    for required in (ROSTER_SHEET, PLAN_SHEET):
        if required not in sheets:
            sys.exit(f"Sheet '{required}' not found; got: {list(sheets)}")

    data = {
        "drivers": parse_roster(sheets[ROSTER_SHEET]),
        "plan": parse_plan(sheets[PLAN_SHEET]),
        **parse_extras(sheets[PLAN_SHEET]),
    }

    if args.json:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_summary(data)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
