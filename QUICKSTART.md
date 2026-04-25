# Quick Start Guide

## ⚡ Get Running in 5 Minutes

### Step 1: Upload to GitHub

1. Create a new **private** repository on GitHub (name: `job-automation`)
2. Upload all files from the `job-automation` folder
3. Commit and push

```bash
cd job-automation
git init
git add .
git commit -m "Initial commit: job automation system"
git remote add origin git@github.com:YOUR_USERNAME/job-automation.git
git branch -M main
git push -u origin main
```

### Step 2: Set Up Claude API Key

1. Get your API key from https://console.anthropic.com/
2. Go to your GitHub repo → Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `ANTHROPIC_API_KEY`
5. Value: (paste your API key)
6. Click "Add secret"

### Step 3: Enable GitHub Actions

1. Go to the "Actions" tab in your repo
2. Click "I understand my workflows, go ahead and enable them"

### Step 4: Test It Out

**Option A: Let it run automatically**
- Wait until 9am or 5pm (it runs twice daily)
- Check Actions tab to see results

**Option B: Run manually now**
1. Go to Actions → "Job Board Monitor"
2. Click "Run workflow" → "Run workflow"
3. Wait ~30 seconds for it to complete
4. Check if any jobs were found

### Step 5: Generate Your First Application

1. Go to Actions → "Generate Application Materials"
2. Click "Run workflow"
3. Enter a job ID from `data/jobs.json` (or test with: `test-job-001`)
4. Click "Run workflow"
5. Download the artifacts to review generated resume + cover letter

## 🎯 Real-World Usage

### Daily Routine

**Morning (after 9am run):**
```bash
# Pull latest jobs
git pull

# Check new jobs
cat data/jobs.json | grep -A5 '"status": "new"'

# Pick one to apply to (e.g., tmx-group-soc-analyst)
```

**Generate materials:**
- Go to GitHub Actions → "Generate Application Materials"
- Enter job ID
- Wait for completion
- Review in `applications/pending/`

**Review and edit:**
```bash
# Edit locally
nano applications/pending/tmx-group-soc-analyst-cover-letter.txt

# Or download from GitHub and edit in your text editor
```

**Approve when ready:**
```bash
mv applications/pending/tmx-group-soc-analyst-* applications/approved/
git add applications/
git commit -m "Approved TMX SOC Analyst application"
git push
```

## 🔧 Customization Checklist

Before your first real run, customize these:

- [ ] `config.yml` - Your target locations and companies
- [ ] `scripts/scrape_jobs.py` - Add specific job board URLs
- [ ] `scripts/generate-resume.js` - Update PROFILE with your details
- [ ] `scripts/generate-cover-letter.py` - Verify your experience stories

## 📊 Tracking Your Applications

Create a simple tracking spreadsheet or use the built-in JSON:

```bash
# View all applications
cat data/applied.json | jq '.applications'

# Count by status
cat data/applied.json | jq '.applications | group_by(.status)'

# This month's applications
cat data/applied.json | jq '.applications | map(select(.applied_date | startswith("2026-04")))'
```

## 🚨 Important Notes

### Before You Auto-Apply to Everything

**DON'T:**
- Spam apply without reviewing materials
- Use the same resume for every role
- Submit without checking company details
- Apply to jobs you're not interested in

**DO:**
- Review every generated cover letter
- Edit out AI-pattern language
- Research the company before applying
- Track your applications properly
- Maintain genuine interest in roles

### Privacy & Security

- This repo should be **PRIVATE**
- Never commit API keys or credentials
- Review generated materials for personal info leaks
- Set artifact retention to 90 days max

### Rate Limits

**Claude API:**
- Free tier: Limited requests
- Pay-as-you-go: ~$0.10-0.50 per cover letter
- Budget accordingly

**Job Boards:**
- Don't scrape too frequently
- Respect robots.txt
- Use delays between requests

## 🐛 Common Issues

### "No jobs found"
- Job boards may have changed HTML structure
- Check if your keywords are too specific
- Try broader search terms

### "Cover letter generation failed"
- Verify API key is set in GitHub Secrets
- Check your Claude API usage limits
- Review error logs in Actions

### "Workflow didn't run"
- Check if Actions are enabled
- Verify cron schedule timezone
- Manually trigger to test

## 📈 Next Features to Build

Once comfortable with the basics, consider adding:

1. **Email notifications** when new jobs arrive
2. **Web dashboard** for easier review
3. **Local Playwright script** for auto-filling applications
4. **Interview tracker** module
5. **Response rate analytics**

## 💡 Pro Tips

**For Cybersecurity Roles:**
- Lead with AI Threat Detection or SecureShop project
- Emphasize Splunk, CTF experience in summary
- Use security-specific keywords from posting

**For Software Engineering:**
- Lead with VibeMap or Karmeka experience
- Focus on CI/CD, API integration, testing
- Highlight deployment and scalability

**For Data/ML Roles:**
- Lead with VibeMap
- Emphasize Power BI, Tableau, ML pipelines
- Show end-to-end data flow ownership

---

**Need Help?** Create an issue in the repo or review README.md for detailed docs.
