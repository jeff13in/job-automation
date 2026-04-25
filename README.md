# Job Application Automation System

Automated job application pipeline using GitHub Actions to monitor job boards, generate tailored resumes and cover letters, and streamline your application process.

## 🎯 What This Does

1. **Monitors job boards** daily for roles matching your keywords (SOC analyst, software engineer, data analyst, etc.)
2. **Generates custom resumes** tailored to each role category (cybersecurity, SWE, data/ML)
3. **Creates cover letters** using the Brock Co-op framework with Claude API
4. **Tracks applications** in a centralized database
5. **Provides review workflow** before submission

## 📁 Project Structure

```
job-automation/
├── .github/workflows/
│   ├── job-monitor.yml              # Scheduled job scraping (9am/5pm daily)
│   └── generate-applications.yml    # On-demand material generation
├── scripts/
│   ├── scrape_jobs.py               # Job board scraper
│   ├── generate-resume.js           # Resume generator (Node.js)
│   └── generate-cover-letter.py     # Cover letter generator (Claude API)
├── data/
│   ├── jobs.json                    # Discovered jobs database
│   └── applied.json                 # Application tracking log
├── applications/
│   ├── pending/                     # Generated materials awaiting review
│   └── approved/                    # Reviewed and ready to submit
├── templates/                       # Resume/cover letter templates
├── config.yml                       # Configuration file
└── README.md
```

## 🚀 Setup Instructions

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/job-automation.git
cd job-automation
```

### 2. Set Up GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add:
- `ANTHROPIC_API_KEY` - Your Claude API key (get from https://console.anthropic.com/)

### 3. Configure Job Search Parameters

Edit `config.yml` to customize:
- Target locations
- Role keywords
- Priority companies
- Company career portal URLs

### 4. Initialize Data Files

```bash
# Create empty jobs database
echo '{"jobs": [], "last_updated": null}' > data/jobs.json

# Create tracking log
echo '{"applications": []}' > data/applied.json

# Commit and push
git add data/*.json
git commit -m "Initialize data files"
git push
```

### 5. Enable GitHub Actions

Go to your repo → Actions → Enable workflows

### 6. Test the Workflow

1. Go to Actions tab
2. Select "Job Board Monitor"
3. Click "Run workflow"
4. Wait for completion and check results

## 🔄 Daily Workflow

### Automated (No Action Required)

**9am & 5pm daily:**
1. GitHub Actions scrapes job boards
2. New jobs are added to `data/jobs.json`
3. Commit is pushed to repo
4. You get a notification (if configured)

### Manual Review & Generation

**When you see new jobs:**

1. **Review discovered jobs:**
   ```bash
   git pull
   cat data/jobs.json | jq '.jobs[] | select(.status == "new")'
   ```

2. **Generate materials for a specific job:**
   - Go to Actions → "Generate Application Materials"
   - Click "Run workflow"
   - Enter job ID (from jobs.json)
   - Wait for completion

3. **Download and review generated files:**
   ```bash
   git pull
   ls applications/pending/
   cat applications/pending/JOB_ID-cover-letter.txt
   ```

4. **Edit as needed:**
   - Customize cover letter
   - Adjust resume bullets
   - Fix any AI-pattern language

5. **Approve for submission:**
   ```bash
   mv applications/pending/JOB_ID-* applications/approved/
   git add applications/
   git commit -m "Approved materials for JOB_ID"
   git push
   ```

## 📝 Usage Examples

### Generate materials for one job

```bash
# Via GitHub Actions UI
Actions → Generate Application Materials → Run workflow
Job ID: tmx-group-soc-analyst-2026

# Or locally
node scripts/generate-resume.js tmx-group-soc-analyst-2026
python scripts/generate-cover-letter.py tmx-group-soc-analyst-2026
```

### Batch generate for all new jobs

```bash
# Loop through new jobs
for job_id in $(jq -r '.jobs[] | select(.status == "new") | .id' data/jobs.json); do
  node scripts/generate-resume.js "$job_id"
  python scripts/generate-cover-letter.py "$job_id"
done
```

### Check job categories

```bash
# See how jobs are categorized
jq '.jobs[] | {title, company, categories}' data/jobs.json
```

## 🔧 Customization

### Add New Job Boards

Edit `scripts/scrape_jobs.py`:

```python
def scrape_custom_board(url):
    # Add your scraping logic
    pass

# In main():
custom_jobs = scrape_custom_board("https://company.com/careers")
```

### Customize Resume Templates

Edit `scripts/generate-resume.js`:

```javascript
const PROFILE = {
  // Update your experience, projects, skills
  experience: [...],
  projects: {...}
};
```

### Adjust Cover Letter Framework

Edit `scripts/generate-cover-letter.py`:

```python
BROCK_FRAMEWORK_PROMPT = """
Your custom prompt here...
"""
```

## 📊 Tracking Applications

### Log an application

```python
# scripts/log_application.py
import json
from datetime import datetime

log = {
    "job_id": "tmx-group-soc-analyst-2026",
    "company": "TMX Group",
    "title": "SOC Analyst",
    "applied_date": datetime.now().isoformat(),
    "status": "applied",
    "materials_used": {
        "resume": "applications/approved/tmx-group-soc-analyst-2026-resume.pdf",
        "cover_letter": "applications/approved/tmx-group-soc-analyst-2026-cover.pdf"
    }
}

with open('data/applied.json', 'r+') as f:
    data = json.load(f)
    data['applications'].append(log)
    f.seek(0)
    json.dump(data, f, indent=2)
```

### View statistics

```bash
# Total applications
jq '.applications | length' data/applied.json

# Applications by status
jq '.applications | group_by(.status) | map({status: .[0].status, count: length})' data/applied.json

# Applications this month
jq '.applications | map(select(.applied_date | startswith("2026-04")))' data/applied.json
```

## 🛡️ Best Practices

### Quality Control
- **Always review generated materials** before submitting
- **Edit out AI patterns** ("— demonstrating", "— directly applicable to")
- **Customize the opening** of each cover letter
- **Verify company/role details** are accurate

### Ethical Considerations
- **Respect robots.txt** and terms of service
- **Don't spam apply** to every job
- **Maintain genuine interest** in roles you apply to
- **Avoid fully automated submission** without human review

### Security
- **Never commit API keys** to the repository
- **Use GitHub Secrets** for sensitive credentials
- **Set artifact retention** to 90 days max
- **Review logs** for exposed data

## 🐛 Troubleshooting

### Job scraper finds no jobs
- Check if job board changed HTML structure
- Verify internet connectivity in GitHub Actions
- Review user-agent string requirements

### Cover letter generation fails
- Verify `ANTHROPIC_API_KEY` is set in GitHub Secrets
- Check API rate limits
- Review Claude API error messages

### Resume generation produces errors
- Ensure Node.js version 18+ in workflow
- Check JSON syntax in jobs.json
- Verify file paths exist

## 📚 Next Steps

### Enhancements to Build
1. **Email notifications** when new jobs are found (using GitHub Actions + SendGrid)
2. **Slack integration** for real-time alerts
3. **Web dashboard** to review/approve materials
4. **Local Playwright script** for form submission
5. **Interview tracking** module
6. **Response rate analytics**

### Integration Ideas
- Connect to Brock Career Zone API (if available)
- Add LinkedIn job scraping
- Parse email job alerts automatically
- Export to ATS tracking spreadsheet

## 📄 License

Personal use only. Do not redistribute without permission.

## 🤝 Contributing

This is a personal project but suggestions welcome via Issues.

---

**Built by Jeffin Sam Joji** | [LinkedIn](https://linkedin.com/in/jeffin-sam-joji) | [GitHub](https://github.com/jeff13in)
