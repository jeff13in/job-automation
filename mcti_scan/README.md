# MCTI partner job scanner

Sweeps the job boards of all 24 University of Guelph MCTI industry partners, filters
to roles worth your time, and tells you **what's new since the last run** — so a daily
check is reading one table instead of opening 24 career sites.

Built to sit alongside `internship-stack`: the scan writes `reports/new_jobs.json`,
which the applier can consume directly.

---

## The workflow

```
discover  →  scan  →  read report  →  hand new_jobs.json to the applier
  (rare)     (daily)
```

### 1. One-time setup

```bash
cd ~/Desktop/job_automation/mcti_scan
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Discover the boards (run once, then whenever a partner starts erroring)

```bash
python -m mcti_scan.cli discover --write -v
```

This probes each company's slug against the keyless ATS APIs — Greenhouse, Lever,
Ashby, SmartRecruiters, Workable, Recruitee — and writes whatever it confirms into
`partners.yml`. Anything it can't resolve falls back to scraping schema.org
`JobPosting` data from the careers page, and if that finds nothing the company gets
listed under "check by hand" with a link, rather than disappearing.

Your previous `partners.yml` is kept as `partners.yml.bak`. **Discovery rewrites the
file through a YAML dumper, so the inline comments are lost** — that's what the backup
is for. Re-add any notes you care about afterwards.

### 3. Scan (this is the daily action)

```bash
python -m mcti_scan.cli scan
```

Writes three files into `reports/`:

| File | What it's for |
|---|---|
| `latest.md` (+ `YYYY-MM-DD.md`) | The report to read. New roles first, then student/co-op roles, then what's still open. |
| `shortlist.csv` | Everything that passed the filter — sort and triage in a spreadsheet. |
| `new_jobs.json` | Only the new ones, as structured records. Feed this to the applier. |

Useful flags:

```bash
python -m mcti_scan.cli scan --dry                 # don't update seen-state
python -m mcti_scan.cli scan --company co-op       # one partner at a time
python -m mcti_scan.cli scan --min-score 10        # widen the net
python -m mcti_scan.cli show                       # reprint last report
```

---

## How the filtering works

Each posting is scored additively, and every job carries the tags that earned its
score — so when the shortlist looks wrong you can see which rule to change instead
of guessing. All the tables live at the top of `mcti_scan/filters.py`.

- **Role match** (required) — security/cyber/SOC/pentest, software/backend/Python/LLM,
  DevOps/cloud/QA, analyst. No role keyword, no shortlist.
- **Level** — intern, co-op, student, new grad, junior, entry-level and Tier 1 get large
  boosts; senior, staff, principal, lead, manager, director, architect get penalised out.
- **Location** — Guelph scores highest, then Toronto/Niagara/KW, then Ontario, then
  remote-Canada. US-, India-, Ireland- and UK-only postings are dropped.
- **Hard excludes** — sales, marketing, HR, finance, legal, retail, clinical, underwriting.
  These never appear regardless of keywords.

Threshold is `min_score: 25` in `partners.yml`. Tune it there, or per-run with
`--min-score`.

To add your own weights without touching the code, put them in `partners.yml`:

```yaml
filters:
  min_score: 25
  extra_keywords:
    kubernetes: 14
    splunk: 16          # you already have Splunk experience — surface those
  extra_excludes:
    - salesforce        # you've flagged this as a gap
```

---

## What's new vs. what's open

`state/seen.json` records the first time each posting was seen, keyed by
company + title + location (deliberately *not* URL — several boards mint a fresh URL
when a posting is edited, which would otherwise look like a new job every day).

So "New since last run" means genuinely new. Delete `state/seen.json` to reset and
treat everything as new again.

---

## Scheduling it

**GitHub Actions (recommended — nothing to keep running on your laptop).**
`.github/workflows/mcti-partner-scan.yml` runs Mon–Fri at 7:40 am Toronto time and:

1. runs `discover --write` for any partner still on `platform: auto` (so the first
   run wires up the boards automatically, and later runs skip it)
2. runs `scan` across all 24 partners
3. commits `reports/` and `state/seen.json` back to the repo, so "new" is tracked
   across runs — `git pull` locally and you share the same history
4. puts the full report in the run's **Summary** tab
5. opens a **GitHub issue** listing the new roles (you get an email / app notification)

Run it by hand from **Actions → MCTI Partner Job Scan → Run workflow**. Options:
re-probe every board, scan one company, override `min_score`, or a dry run that
commits nothing.

**Or locally:**

**macOS, via launchd** (survives reboots; better than cron on a laptop). Save as
`~/Library/LaunchAgents/com.jeffin.mctiscan.plist`, then
`launchctl load ~/Library/LaunchAgents/com.jeffin.mctiscan.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.jeffin.mctiscan</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/jeffin/Desktop/job_automation/mcti_scan/.venv/bin/python</string>
    <string>-m</string><string>mcti_scan.cli</string><string>scan</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/jeffin/Desktop/job_automation/mcti_scan</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>40</integer></dict>
  <key>StandardOutPath</key><string>/tmp/mctiscan.log</string>
  <key>StandardErrorPath</key><string>/tmp/mctiscan.err</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
```

Fix the paths to match your actual username. `launchctl unload` the same path to stop it.

**Or cron**, if you'd rather:

```cron
40 7 * * 1-5 cd ~/Desktop/job_automation/mcti_scan && .venv/bin/python -m mcti_scan.cli scan >> /tmp/mctiscan.log 2>&1
```

---

## Handing off to the applier

`reports/new_jobs.json` is an array of records shaped like:

```json
[
  {
    "key": "a1b2c3d4e5f60718",
    "company": "The Co-operators",
    "title": "Cybersecurity Analyst, Co-op (Summer 2027)",
    "url": "https://...",
    "location": "Guelph, Ontario",
    "department": "Security",
    "posted_at": "2026-11-16",
    "score": 122,
    "is_student_role": true,
    "tags": ["role:cyber", "level:co-op", "loc:guelph"],
    "source": "greenhouse"
  }
]
```

`key` is stable across runs, so the applier can mark progress against it. `SeenStore`
has `mark_applied(key)` / `applied(key)` if you want application state tracked here
instead of in the applier's own store.

---

## Adding or fixing a partner

```yaml
- name: Some Company
  platform: greenhouse        # or lever / ashby / smartrecruiters / workable /
                              # recruitee / workday / jsonld / auto / manual
  token: somecompany          # for the keyless board APIs
  careers_url: https://...    # fallback + the link shown in manual-check lists
```

For Workday, give the host and site instead — the tenant is derived from the host's
first label:

```yaml
- name: BlackBerry
  platform: workday
  host: bb.wd3.myworkdayjobs.com
  site: BlackBerry
```

Set `platform: auto` with `candidates: [slug1, slug2]` to let discovery figure it out.

---

## Verified vs. assumed

Two boards are confirmed against live postings:

- **Magnet Forensics** → Lever (`jobs.lever.co/magnetforensics`) — posts Waterloo
  Software Developer Co-op terms
- **BlackBerry** → Workday (`bb.wd3.myworkdayjobs.com/BlackBerry`) — Waterloo and
  Ottawa/QNX, runs a student program

Arctic Wolf's own hiring FAQ states applications go through Workday, and eSentire is
syndicated onto Georgian's portfolio board — both are marked with hints for discovery.
Everything else in `partners.yml` is a **candidate guess until `discover` proves it**.
The notes field flags why each partner matters; `The Co-operators` is worth watching
most closely, since its head office is in Guelph.

Four partners have no machine-readable board and are permanently manual: CSE/Canadian
Centre for Cyber Security, RCMP, Toronto Police Service, CCTX. Microsoft and Mandiant
run their own large boards and are also set to manual — their search URLs are
pre-filtered in `partners.yml`.

## A caution on the public-sector ones

CSE requires Canadian citizenship and Top Secret clearance, and the timeline runs
months. If that path interests you, the student program (FSWEP/co-op) is the usual
entry route and is worth starting well before you need it.

---

## Tests

```bash
python -m pytest tests/ -q
```

13 tests, no network: adapter parsing against real ATS response shapes, scoring
behaviour (student roles up, senior/sales/foreign out), dedupe, and seen-state
diffing including recovery from a corrupt state file.

## Being a good guest

Requests go out through one session with a browser User-Agent, retry with backoff on
429/5xx, honour `Retry-After`, pause 0.4–1.1s between calls, and run at most 6
concurrent workers. Don't raise those numbers — these are other people's servers, and
a scanner that gets your IP blocked is worse than no scanner.
