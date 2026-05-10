# Job Application Automation System

Automated job application pipeline using GitHub Actions to monitor job boards, generate AI-tailored resumes and cover letters, and streamline the application process.

## What This Does

1. **Scrapes job boards** every 30 minutes for roles matching your keywords (SOC analyst, software engineer, data/ML)
2. **Generates tailored LaTeX resumes** — Gemini 2.0 Flash rewrites the summary and selects the most relevant projects per job
3. **Writes cover letters** using the Brock Co-op framework via Gemini 2.0 Flash
4. **Compiles PDFs** using Tectonic (LaTeX engine) inside GitHub Actions
5. **Tracks applications** in a local JSON database

## Tech Stack

| Layer | Technology |
|---|---|
| Scripting | Python 3.11 (scraper, resume/cover letter generators) |
| Resume output | LaTeX `.tex` → PDF via **Tectonic** |
| Node.js | `generate-resume.js` (JSON resume builder, `docx` dep) |
| AI | **Google Gemini 2.0 Flash** REST API (free tier, 1500 req/day) |
| CI/CD | GitHub Actions (scheduled + on-demand workflows) |
| Job sources | Remotive API, RemoteOK API, We Work Remotely RSS, intern-list.com |
| HTML parsing | `beautifulsoup4` + `lxml` |
| Data storage | `data/jobs.json`, `data/applied.json` (flat JSON files) |

## Project Structure

```
job-automation/
├── .github/workflows/
│   ├── job-monitor.yml              # Runs every 30 min — scrapes + commits new jobs
│   └── generate-applications.yml   # On-demand — generates LaTeX resume + PDF
├── scripts/
│   ├── scrape_jobs.py               # Scrapes Remotive, RemoteOK, WWR, intern-list
│   ├── generate-resume-latex.py     # LaTeX resume builder (Gemini-tailored)
│   ├── generate-resume.js           # JSON resume builder (Node.js)
│   └── generate-cover-letter.py    # Cover letter generator (Gemini API)
├── data/
│   ├── jobs.json                    # Discovered jobs database
│   └── applied.json                 # Application tracking log
├── applications/
│   ├── pending/                     # Generated materials awaiting review
│   └── approved/                    # Reviewed and ready to submit
├── templates/                       # Reserved for future templates
├── config.yml                       # Job search configuration
├── requirements.txt                 # Python dependencies
├── package.json                     # Node.js dependencies
└── setup.sh                         # One-time local setup script
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/job-automation.git
cd job-automation
bash setup.sh
```

`setup.sh` installs Python and Node.js dependencies and initializes `data/jobs.json` and `data/applied.json`.

### 2. Add GitHub Secrets

Go to repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key — get one at [aistudio.google.com](https://aistudio.google.com/) |

### 3. Customize config

Edit `config.yml` to set your target locations, role keywords, and priority companies.

### 4. Enable GitHub Actions

Go to the Actions tab in your repo and enable workflows, or use the CLI:

```bash
gh workflow enable job-monitor.yml
gh workflow enable generate-applications.yml
```

> **Note:** Both workflows are currently disabled. Re-enable them when you're ready to resume automated scraping.

## Usage

### Automated scraping (currently disabled)

`job-monitor.yml` is configured to run every 30 minutes but is currently **disabled**. Re-enable it with:

```bash
gh workflow enable job-monitor.yml
```

When active, new jobs are committed to `data/jobs.json` with a message like `🔍 Found 3 new job(s)`.

### Review new jobs

```bash
git pull
cat data/jobs.json | jq '.jobs[] | select(.status == "new") | {id, title, company, url}'
```

### Generate a resume + cover letter

1. Go to **Actions → Generate Application Materials → Run workflow**
2. Enter the `job_id` from `jobs.json`
3. The workflow will:
   - Call Gemini to tailor the resume summary and select relevant projects
   - Build a `.tex` file and compile it to PDF via Tectonic
   - Upload the PDF as a workflow artifact (retained 90 days)
   - Commit the `.tex` file to `applications/pending/`

Or run locally:

```bash
# Resume (LaTeX, requires GEMINI_API_KEY env var)
GEMINI_API_KEY=your_key python3 scripts/generate-resume-latex.py <job_id>

# Cover letter
GEMINI_API_KEY=your_key python3 scripts/generate-cover-letter.py <job_id>

# JSON resume (no API key needed)
node scripts/generate-resume.js <job_id>
```

### Review and approve

```bash
git pull
ls applications/pending/

# Edit if needed, then approve:
mv applications/pending/<job_id>-* applications/approved/
git add applications/
git commit -m "Approved <job_id>"
git push
```

## Job Sources

| Source | Tracks | Method |
|---|---|---|
| [Remotive](https://remotive.com) | `software_engineering`, `data_ml` | JSON API |
| [RemoteOK](https://remoteok.com) | `cybersecurity`, `software_engineering`, `data_ml` | JSON API |
| [We Work Remotely](https://weworkremotely.com) | All | RSS feed |
| [intern-list.com](https://intern-list.com) | `software_engineering`, `data_ml` | HTML scrape |

Jobs are classified into three role tracks via keyword matching on title + description:
- `cybersecurity` — SOC analyst, security engineer, incident response, GRC, etc.
- `software_engineering` — backend, full stack, platform engineer, etc.
- `data_ml` — data analyst, ML engineer, data scientist, etc.

## Resume Generation

`generate-resume-latex.py` builds a two-page LaTeX resume:

1. **Base content** — hardcoded experience, skills, certifications, and five candidate projects
2. **Gemini tailoring** — given the job description, Gemini selects 3–4 projects and rewrites their bullets, and rewrites the summary to target the role
3. **Fallback** — if `GEMINI_API_KEY` is unset or Gemini fails, base content is used as-is
4. **PDF compilation** — Tectonic compiles the `.tex` file in CI without a local LaTeX install

## Cover Letter Generation

`generate-cover-letter.py` uses the Brock Co-op framework:
- Extracts 3–5 key requirements from the job posting
- Builds narrative paragraphs linking Jeffin's experience to those requirements
- Fetches the live job page if no description is stored in `jobs.json`
- Rate-limit retry: up to 4 attempts with 20s backoff on HTTP 429

## Data Format

**`data/jobs.json`**
```json
{
  "jobs": [
    {
      "id": "acme-corp-backend-engineer",
      "title": "Backend Engineer",
      "company": "Acme Corp",
      "url": "https://...",
      "location": "Remote",
      "source": "remotive",
      "categories": ["software_engineering"],
      "discovered_date": "2026-05-09T10:00:00",
      "status": "new"
    }
  ],
  "last_updated": "2026-05-09T10:00:00"
}
```

Status values: `new` → `reviewed` → `applied` → `interview` → `rejected` / `accepted`

## Troubleshooting

**Scraper finds no jobs** — Job board HTML may have changed; check `scrape_jobs.py` selectors. RemoteOK and Remotive are API-based and more stable.

**Cover letter / resume generation fails** — Verify `GEMINI_API_KEY` is set in GitHub Secrets. Check the Actions log for HTTP error codes.

**PDF not generated** — Tectonic setup step may have failed. Check the Actions log for the `Set up Tectonic` step.

**Duplicate jobs accumulating** — Jobs are deduped by ID (`{company}-{title}` slug). Rename collisions are possible if two companies have identical slugs.

## Best Practices

- **Always review generated materials** before submitting — edit out AI-pattern language ("demonstrating", "directly applicable to")
- **Verify company and role details** in each cover letter
- **Keep this repo private** — it contains your personal information
- **Never commit API keys** — use GitHub Secrets

## License

Personal use only.

---

**Jeffin Sam Joji** | [LinkedIn](https://linkedin.com/in/jeffin-sam-joji) | [GitHub](https://github.com/jeff13in)
