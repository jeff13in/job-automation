# internship-stack

Cold-application pipeline: find roles → track them in one sheet → tailor a resume →
fill the application → read the replies → hand you only what needs you.

```
finder ──roles──▶ sheet ◀──status── listener ◀──replies── inbox
                    │  ▲                                     ▲
              next row  new rows                             │
                    ▼  │                                     │
   resumes ──pdf──▶ applier ───────────── codes ─────────────┘
                    │
                 blocked ──▶ you
```

| Box in the diagram | Code | Runs |
|---|---|---|
| 01 role finder | `stack/finder/` | daily |
| 02 application tracker | `stack/sheet.py` (Google Sheet or local CSV) | — |
| 03 master + variants | `resumes/`, `skills/internship-applications/SKILL.md`, `stack/resumes/tailor.py` | per application |
| 04 applier | `stack/applier/` | a few times a day |
| 05 inbox listener | `stack/listener/` | every 15 min |
| 06 you | sheet filter: `blocked_reason` is not empty | when you have time |

## Setup (about 30 minutes)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env            # add ANTHROPIC_API_KEY
```

1. **Fill in `resumes/master.yaml`** (every `TODO`) and **`profile.yaml`**. Nothing
   gets submitted with a `TODO` in it; those fields block instead.
2. **Google Sheet.** Create a Google Cloud project, enable the Sheets API, create a
   service account, download its key to `secrets/service_account.json`. Make a blank
   sheet, share it with the service account's email (Editor), put the sheet id in
   `config.yaml`, set `sheet.backend: google`. The header row is written on first run.
   Add a filter view `blocked_reason is not empty`: that's your queue.
   (Want to try everything first? Leave `backend: csv`.)
3. **Application inbox.** Make a new Gmail account just for applications. In the same
   Cloud project enable the Gmail API, create an OAuth client (Desktop app), save it as
   `secrets/gmail_credentials.json`. The first command that touches Gmail opens a
   browser to sign in to that account.
4. **Job alerts.** Turn on email alerts on LinkedIn, Handshake, Indeed and Intern
   Insider, sent to the application inbox, and add a Gmail filter that labels them
   `job-alerts`. The finder reads those instead of automating the sites, which their
   terms forbid and which gets accounts banned.

## Use it

```bash
python -m stack.finder run --dry-run        # see what it would add (no keys needed)
python -m stack.finder run                  # add new roles to the sheet
python -m stack.resumes --build-variants    # the 8 base PDFs in data/resumes/variants/
python -m stack.applier run --headed        # prepare the next few applications, watch it work
python -m stack.listener once --dry-run     # see how it would read your inbox
```

The applier starts in **draft mode**: it fills the whole form, saves a packet in
`data/packets/<id>/` (`resume.pdf`, `answers.json`, `filled.png`), marks the row
`drafted`, and does not press submit. Review the packet, edit `answers.json` if you
want, then:

```bash
python -m stack.applier submit <id>
```

Once drafts consistently look right, set `applier.mode: submit` in `config.yaml`.

When a row is blocked on a question (sponsorship, graduation date, ...), add your
answer to `profile.yaml` under `answers:` and run `python -m stack.applier requeue <id>`.
Next time that question appears anywhere, it's answered.

## Schedule it

`scripts/crontab.example` runs the finder daily, the applier three times a day and the
listener every 15 minutes on any always-on machine. `prompts/indeed-finder.md` is a
prompt for a Claude scheduled task that searches Indeed with the Indeed connector and
pushes results in with `python -m stack.finder add --json`.

## What it will and won't do

- Supported forms: Greenhouse, Lever, Ashby. Workday, iCIMS and the rest go straight
  to `blocked` with the URL; apply to those yourself.
- It never answers sponsorship, citizenship, demographic, salary, graduation, GPA,
  start-date or legal-attestation questions unless *you* put the answer in
  `profile.yaml`. It never guesses a dropdown it can't map.
- Tailoring can only select and reword bullets from `master.yaml`. Output that cites a
  bullet that doesn't exist, adds a number, or lists a skill you don't have is rejected,
  retried once, and then replaced with the base variant.
- CAPTCHAs block; it doesn't try to solve them.

## Tests

```bash
pytest
```

`tests/test_applier_e2e.py` drives the real applier in headless Chromium against a
local Greenhouse-style form, including the emailed security-code step, with Claude and
Gmail stubbed.
