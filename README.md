# Bílaplan Þróttar – TM Mótið í Eyjum

Driver shuttle plan generator for Þróttur Reykjavík’s five girls’ teams at TM Mótið in Vestmannaeyjar. Two cars shuttle all five teams between accommodation (gisting), the dining hall (matsalur), and four playing venues.

This README is written as an executable spec: an AI agent with web access should be able to follow it end-to-end to generate the plan for **Friday (föstudagur)** and **Saturday (laugardagur)** once those match schedules are published.

-----

## 1. Goal

For a given tournament day, produce a self-contained HTML page (same structure as `fimmtudagur.html` / the Thursday plan) that tells each of two drivers exactly which trips to drive, when, with which team, from where to where. `index.html` is just a redirect to the current day's plan — repoint it when a new day goes live.

Output language: **Icelandic**. All times 24h format (`HH:MM`).

## 2. Data sources

### 2.1 Match schedule (primary, fetch live)

- **Scraper:** `scrape.py` in this repo implements this section (stdlib-only Python 3). `python3 scrape.py --probe` discovers populated day codes; `python3 scrape.py --day B --json` emits the parsed Þróttur matches.
- Results site: `https://urslit.tmmotid.is/index?day=<DAY>`
  - `day=A` = fimmtudagur (Thursday). Confirmed populated.
  - `day=B` = föstudagur (Friday). Confirmed 2026-06-11 via the iframe on `https://tmmotid.is/page/urslit-fostudagur`.
  - `day=C` = laugardagur (Saturday). Confirmed populated 2026-06-12 (“C - Laugardagur” in the day picker).
  - A populated day page is ≫ 10 KB and contains an HTML `<table>`.
- Table row format (after HTML-entity unescaping), `<td>` cells in order:
  `Riðill | Tími | Völlur | Lið 1 | Lið 2 | Úrslit Lið-1 | Úrslit Lið-2`
  Example: `A01 | 08:20 | Hásteinsvöllur 2 | Þróttur-1 | Fjölnir-1 | |`
- Filter: keep rows where either team cell contains `Þróttur` (note: page uses HTML entities like `&eth;` — unescape before matching; match on the unescaped string `Þróttur`).
- Our five teams are named `Þróttur-1` … `Þróttur-5`. The suffix maps 1:1 to “Lið 1–5” in the roster below.
- Saturday is a knockout/finals day: which match each team plays may depend on group results. If the schedule shows placeholder names (e.g. “Sigurvegari A01”), map Þróttur teams to matches via their group (riðill) standings on `https://urslit.tmmotid.is/index/ridlar?day=A` and flag any assumption made.

### 2.2 Meal time rules (static, from the TM food schedule “TÍMASETNINGAR Í MAT”)

Meal sitting is determined by the team’s **first match kickoff of the day**.

**Fimmtudagur og föstudagur (Thu & Fri) — identical mapping:**

|First kickoff|Morgunmatur|Hádegismatur|Kvöldmatur|
|-------------|-----------|------------|----------|
|08:20        |07:00      |12:30       |16:30     |
|09:00        |07:30      |13:00       |17:00     |
|13:00        |08:00      |11:30       |17:30     |
|13:40        |08:30      |12:00       |18:00     |

**Laugardagur (Sat):**

|First kickoff|Morgunmatur|Hádegismatur|
|-------------|-----------|------------|
|08:00        |07:00      |12:45       |
|08:30        |07:30      |11:15       |
|09:00        |08:00      |11:45       |
|09:30        |08:30      |12:15       |

(No kvöldmatur listed for Saturday — teams travel home. If a Þróttur team’s first kickoff is not in the table, pick the nearest listed kickoff and flag it for human review.)

### 2.3 Boat trips (bátsferðir — Rib Safari excursions)

- Schedule PDF: `https://d5hu1uk9q8r1p.cloudfront.net/tmmotid.is/skrar/tm-motid-2026/tmmotid-batsferdir-2026.pdf` (2 pages: Wednesday + Thursday departures, teams listed under each time slot).
- Þróttur slots (all on **Thursday**): **10:40 — Þróttur-3 + Þróttur-5** · **15:20 — Þróttur-1 + Þróttur-2 + Þróttur-4**. No Þróttur trips on Wednesday or Friday.
- Logistics: depart from RibSafari dock at **Tangagata 7** (next to the playground, near Herjólfur). Teams must arrive **15 min before departure**; the trip lasts **30 min**; 1 fararstjóri accompanies each team. RibSafari phone: 661 1810.
- The shuttle plan must include gisting/venue → dock trips (arrive ≥ 15 min early) and dock → next-commitment trips after return (departure + 30 min). Re-fetch the PDF when generating Friday/Saturday in case the plan changes (comments go to [siggainga@ibv.is](mailto:siggainga@ibv.is)).

### 2.4 Venues

Hásteinsvöllur, Þórsvöllur, Týsvöllur, Herjólfshöll. All within **2–5 min driving** of each other and of gisting/matsalur. Týsvöllur, Hásteinsvöllur and Herjólfshöll are walkable; walking is the fallback if both cars are busy, but car trips matter most for meal/accommodation runs.

## 3. Roster: teams and drivers

**Scraper:** `scrape_drivers.py` fetches the live roster and per-day shift signups (plus Herjólfur ferry drivers and gisting) from the shared "Bílstjóravaktir og nestisnefnd" Google Sheet — `python3 scrape_drivers.py --json`. Rerun it before generating each day's plan; the table below is a snapshot.

|Lið|Drivers (name · phone)                                      |
|---|------------------------------------------------------------|
|1  |Hilmar · 898 9249 — Ágúst · 696 7931 — Valur · 663 4411     |
|2  |Andri · 666 1313 — Jón Levy · 779 8217 — Ágúst · 696 7931   |
|3  |Kristján · 698 0088 — Leví · 839 3667 — Einar Örn · 896 9577|
|4  |Sæmi · 695 9582 — Sif · 888 4628 — Egill · 849 0691         |
|5  |Bjarki · 697 5490 — Valtýr · 625 5195 — Arna · 692 5515     |

Note: **Ágúst is registered with both lið 1 and lið 2** — ideal reserve when those teams play simultaneously.

### Thursday assignments (already used — rotate away from these)

|Shift                 |Bíll 1      |Bíll 2    |Reserve     |Teams playing|
|----------------------|------------|----------|------------|-------------|
|Morgunvakt 06:40–12:00|Kristján (3)|Bjarki (5)|Valtýr (5)  |1, 2, 4      |
|Miðvakt 11:45–15:30   |Hilmar (1)  |Andri (2) |Ágúst (1+2) |3, 5         |
|Kvöldvakt 15:15–18:45 |Valur (1)   |Egill (4) |Jón Levy (2)|3, 5         |

**CRITICAL assignment rule (learned from parent feedback):** A driver must NEVER be on shift while their own team is playing — drivers shuttle the *other* teams and would miss their daughter’s matches. Assign drivers to shifts where their team is idle: e.g. if lið 1, 2, 4 play in the morning block, the morning shift is staffed by lið 3/5 parents, and vice versa. Boat trips and meals are acceptable overlaps (only 1 fararstjóri accompanies the boat), but flag them.

**Rotation rule:** No one drives two days in a row unless unavoidable. Thursday’s final drivers (per `index.html`) were Andri (2), Egill (4), Kristján (3), Valtýr (5), Hilmar (1), Valur (1), Einar Örn (3). Friday’s drivers (per `fostudagur.html`) are Leví (3), Andri (2, self-signed two days in a row), Einar Örn (3, second day in a row — unavoidable, the day shift needs a lið 3/5 parent and none were fresh), Bjarki (5), Svavar (2 — not in the roster; phone 820 9091), Sæmi (4), Jón Levy (2), Ágúst (1+2) — so Saturday priority goes to **Hilmar (1), Valur (1), Egill (4), Kristján (3), Valtýr (5), Sif (4), Arna (5)**, still subject to the critical rule above. Einar Örn has now driven two days running — keep him off Saturday.

Saturday’s final drivers (per `laugardagur.html`, all last drove Thursday or not at all): Sif (4), Arna (5), Valtýr (5), Egill (4), Hilmar (1), Kristján (3) — short shifts cut around each team’s kickoffs so every driver sees all of their own team’s matches.

**Signup rule (learned from parent feedback):** a parent who signed up for a specific slot in the “Bilstjóra plan” sheet gets **exactly that slot** — never extend, move or drop their shift without asking them first. Fill remaining gaps around the signups.

**Couple constraint:** Bjarki and Arna (lið 5) are a couple and can never drive at the same time — they have another child to look after; at most one of them per shift.

**Friday learning (carry into Saturday):** the venues are all in the same area — teams **walk between venues**, drivers only run gisting ↔ matsalur ↔ venue-area trips. Skip step 4’s venue → venue trips entirely. Also cross-check the per-team meal times against the parents’ live `DAGSKRÁ` sheet (same spreadsheet as the rosters): the fararstjórar move teams between sittings (e.g. Friday: lið 4 swim trip with 12:00 lunch / 18:00 dinner) and the official kickoff→sitting table is only the fallback.

## 4. Scheduling algorithm

1. **Fetch & parse** all Þróttur matches for the target day (§2.1). Build per-team match list sorted by kickoff: `(time, venue)`.
1. **Derive meal times** per team from first kickoff (§2.2).
1. **Group teams** into morning-block and afternoon-block by first kickoff (Thursday split was 1/2/4 morning, 3/5 afternoon — Friday may differ; recompute, don’t assume).
1. **Generate trips** per team:
- Gisting → matsalur, arrive ≥ meal time. Pickup ~15 min before the meal.
- Matsalur → first venue: depart so the team arrives **25–30 min before kickoff** (drive ≤ 5 min). Floor: never less than 20 min before kickoff; if a trip lands under 20 min, restructure (earlier sitting departure or extra reserve-driver trip) and flag it.
- Venue → venue between consecutive matches: depart ~10 min after the previous match’s expected end. Matches run in 40-min slots; assume a match ends ~40 min after kickoff.
- Last venue → matsalur or gisting depending on meal timing.
- Matsalur → gisting after each meal (~30–45 min dining time; sittings are staggered every 30 min so default to pickup 30–40 min after sitting start).
1. **Assign trips to the two cars** such that:
- No car has two trips scheduled < 10 min apart at different origins.
- Each car’s trip sequence is geographically sane (it can physically chain).
- Three teams sharing one transfer window (à la Thursday 09:10–09:30) is fine: two cars do three moves because drives are short; stagger by 10 min.
1. **Define shifts** (morning / mid / evening, Saturday likely just morning + mid) and assign drivers per §3 rotation.
1. **Validate** (checklist below) before producing output.

### Validation checklist

- [ ] Every Þróttur match on the day’s schedule is covered by an inbound trip.
- [ ] Every team arrives ≥ 20 min (target 25–30) before each kickoff.
- [ ] Every meal sitting has a drop-off at or before the sitting time.
- [ ] No car is double-booked (two trips overlapping in time from different places).
- [ ] Each driver’s shift covers all trips assigned to their car in that window.
- [ ] Phone numbers in output match §3 exactly.
- [ ] Flag a “naumur tími” warning on any arrival margin of 20–24 min (like lið 4 Thursday morning).

## 5. Output format

Produce a single self-contained HTML file modeled on the Thursday file (`fimmtudagur.html` in this repo):

- Sticky car picker: **Bíll 1 (red `#C8102E`) / Bíll 2 (blue `#1D4E89`) / Allt** — JS class-toggle filtering (`body.show-c1` hides `.trip.c2`, etc.).
- One `.trip` card per trip: big time, `Hvaðan → Hvert`, team chips (lið colors: 1 `#F6C9CF`, 2 `#D96A5B`, 3 `#E89AA4`, 4 `#C8102E`, 5 `#F2B8C0`), one-line “why” note, car label.
- Green `.gamerow` dividers at each kickoff (hidden in single-car view).
- Per-shift driver cards with `tel:` links; reserve driver listed under each shift.
- Collapsible `<details>` overview table (matches + meal times per team).
- Notes section + warning box for anything flagged during validation.
- Fonts: Barlow + Barlow Condensed (Google Fonts). `<meta charset="UTF-8">`. Print CSS shows both cars.

Name the file `fostudagur.html` / `laugardagur.html` and link the days together with a simple nav in the header.

## 6. Deployment

GitHub Pages serves this repo from `main` branch root. To publish updates:

```bash
git add . && git commit -m "Plan fyrir föstudag" && git push
```

Page rebuilds automatically (~1 min).

## 7. Known gotchas

- The results site serves HTML entities (`&eth;`, `&iacute;`) — unescape before string-matching team names.
- `web_fetch`-style tools may fail on `tmmotid.is`; plain `curl` worked. The iframe URL (`urslit.tmmotid.is`) is the real data source, not the WordPress page.
- Day codes beyond `A` are unconfirmed — discover them from the live site, don’t guess.
- Driver phone numbers are personal data: keep the repo’s audience in mind before sharing the URL publicly.
- Times on the food schedule are sitting *start* times; the hall expects each sitting to clear in ~30 min.