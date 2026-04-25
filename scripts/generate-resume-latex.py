#!/usr/bin/env python3
"""
LaTeX resume generator.
Base content = resume.pdf exactly.
Gemini tailors summary + selects/rewrites project bullets per job description.
Falls back to base content if GEMINI_API_KEY is not set or Gemini fails.
"""

import json
import os
import re
import sys
import time
import requests
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


# ── Helpers ───────────────────────────────────────────────────────────────────

def tex_escape(text: str) -> str:
    """Escape LaTeX special characters in plain text (e.g. Gemini output)."""
    for old, new in [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]:
        text = text.replace(old, new)
    return text


def clean_gemini(text: str) -> str:
    """Normalize Gemini output for safe LaTeX insertion."""
    text = text.replace("–", "--").replace("—", "---")
    text = text.replace("’", "'").replace("‘", "`")
    text = text.replace("“", "``").replace("”", "''")
    text = text.replace("→", "->")
    text = tex_escape(text)
    text = text.replace("->", "$\\rightarrow$")
    return text


def fetch_description(url: str) -> str:
    """Scrape plain text from a job listing URL."""
    if not url:
        return ""
    try:
        class _Strip(HTMLParser):
            def __init__(self):
                super().__init__()
                self.chunks = []
                self._skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "header", "footer"):
                    self._skip = True
            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "header", "footer"):
                    self._skip = False
            def handle_data(self, data):
                if not self._skip and data.strip():
                    self.chunks.append(data.strip())

        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            p = _Strip()
            p.feed(r.text)
            return " ".join(p.chunks)[:4000]
    except Exception:
        pass
    return ""


# ── LaTeX preamble ────────────────────────────────────────────────────────────

PREAMBLE = r"""\documentclass[10.5pt, letterpaper]{article}

\usepackage[top=0.5in, bottom=0.5in, left=0.6in, right=0.6in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{XCharter}
\usepackage{microtype}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage[hidelinks]{hyperref}
\usepackage{textcomp}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}

\titleformat{\section}{\bfseries\normalsize}{}{0em}{\uppercase}
  [\vspace{1pt}\rule{\linewidth}{0.5pt}]
\titlespacing*{\section}{0pt}{10pt}{4pt}

\setlist[itemize]{leftmargin=14pt, label=\textbullet, itemsep=2pt, topsep=3pt, parsep=0pt}

\begin{document}"""


# ── Base resume content — matches resume.pdf exactly ─────────────────────────

BASE_SUMMARY = (
    "Fourth-year Computer Science (Honours) student graduating April 2026, with production experience "
    "building full-stack and mobile applications at an AI startup. Strong front-end craft in React and "
    "TypeScript, paired with full-stack backend skills across REST APIs, CI/CD, and cloud deployment. "
    "Proven ability to translate complex data and AI outputs into polished, intuitive interfaces."
)

SKILLS = [
    (r"Frontend",          r"React, React Native, TypeScript, JavaScript, HTML/CSS, Tailwind, Expo SDK, Responsive Design, Component Libraries"),
    (r"Backend \& APIs",   r"Java, C++, Python (Flask, Django), Node.js, RESTful APIs, GraphQL, OAuth 2.0, Webhooks"),
    (r"Databases",         r"PostgreSQL, SQLite, Supabase, Firebase, SQL queries, data modeling"),
    (r"DevOps \& Cloud",   r"GitHub Actions CI/CD, Docker, AWS, Git/GitHub, Gunicorn, Vercel, Render"),
    (r"Data \& AI",        r"scikit-learn, pandas, NumPy, OpenAI API, Claude API, ECharts, Tableau, Power BI, ETL pipelines"),
    (r"Design \& Tooling", r"Design systems, Figma, Postman, ESLint, Agile / Scrum"),
]

EXPERIENCE = [
    {
        "header": r"Software Engineer Intern | Karmeka | Toronto, ON | Aug 2025 -- Present",
        "bullets": [
            r"Owned the full design system for the Karmeka Customers mobile app --- defined brand tokens, card layouts, status badges, and reusable component library across 4 tab screens and 6+ additional screens in React Native / Expo SDK 54 / TypeScript.",
            r"Built and maintained a typed REST API client covering 15+ endpoints (vehicles, appointments, workshops, quotes) with TTL-based in-memory caching and foreground-resume auto-refresh, eliminating redundant network calls and keeping UI state consistent.",
            r"Integrated OpenAI and Claude APIs to automate internal business workflows and document parsing (OCR pipelines), reducing manual data entry by 60\% and surfacing AI outputs through clean, actionable UI components.",
            r"Established GitHub Actions CI/CD pipelines automating build, test, and deployment across environments, cutting release cycle time by 40\% and enforcing consistent cross-platform delivery.",
            r"Collaborated in fast-moving agile sprints, translating business requirements into shippable features while iterating on UX based on stakeholder feedback.",
        ],
    },
    {
        "header": r"Software Developer/AI Engineer | Venture for Canada Intrapreneurship | Remote | Oct 2025 -- Nov 2025",
        "bullets": [
            r"Built an AI-powered full-stack platform serving 500+ active users --- React/TypeScript frontend with Python backend enabling personalized newsletter and social media content generation from user-defined topics and sources.",
            r"Designed a content aggregation pipeline using n8n/Make automation to collect, filter, and summarize data from 50+ sources daily --- Python NLP/ML models improved content relevance signal by 60\%.",
            r"Implemented prompt engineering systems using OpenAI and Claude APIs for automated outreach, increasing booking response rates by 40\% and cutting manual effort by 70\%.",
            r"Maintained 99.5\% uptime with Docker containerization --- documented architecture and workflows, reducing new developer onboarding time by 40\%.",
        ],
    },
    {
        "header": r"Supervisor | Digital Attractions | Mar 2025 -- Present",
        "bullets": [
            r"Led structured onboarding and training for new team members, improving operational efficiency by 35\% through process documentation.",
            r"Implemented systematic troubleshooting processes to resolve technical issues, reducing customer wait times by 25\%.",
        ],
    },
]

# All 5 projects — Gemini selects 3-4 and rewrites bullets
ALL_PROJECTS = [
    {
        "name": "WatchNext Mobile App",
        "label": "Brock Uni Project",
        "dates": "Jan 2026 -- April 2026",
        "github_url": "",
        "live_url": "",
        "tech": "Java, Firebase Auth, Supabase, TMDb API",
        "bullets": [
            r"Built a content-based recommendation engine in Java that constructs a weighted taste profile from user activity (liked +2, watched +1, disliked $-$2) across genre tags, scoring unseen candidates with a custom formula combining tag overlap, mood adjustment, TMDb rating, and popularity signals.",
            r"Implemented a mood-aware filtering layer (Happy, Excited, Relaxed, Scared, Emotional) that dynamically re-weights genre preferences and expands the candidate pool, surfacing top-20 recommendations with per-item explanations --- integrated Firebase Auth, Supabase (PostgreSQL REST), and TMDb API via Retrofit.",
            r"Built a full-featured Android application in Java using MVC architecture --- browse/discover, real-time search, personalized watchlist management, and a custom content-based recommendation engine with mood filtering.",
        ],
    },
    {
        "name": "AI Threat Detection System",
        "label": "Personal Project",
        "dates": "Dec 2025",
        "github_url": "https://github.com/jeff13in/AI-threat-Detection",
        "live_url": "",
        "tech": r"Python, scikit-learn, TensorFlow, VirusTotal API, AbuseIPDB, CVE CIRCL, PostgreSQL, Docker",
        "bullets": [
            r"Built ML-powered anomaly detection system using Isolation Forest and DBSCAN clustering to identify suspicious behavioral patterns in log and event data --- aligned with SOC threat monitoring and incident triage workflows.",
            r"Integrated four threat intelligence APIs (VirusTotal, AbuseIPDB, OTX AlienVault, CVE CIRCL) to build a comprehensive multi-source intelligence aggregation pipeline, mirroring enterprise threat enrichment architectures.",
            r"Deployed Kafka event streaming with Elasticsearch for scalable log ingestion and indexed alerting, directly replicating modern SIEM data pipeline architecture.",
        ],
    },
    {
        "name": "VibeMap",
        "label": "Personal Project",
        "dates": "Jan 2026 -- Feb 2026",
        "github_url": "https://github.com/jeff13in/VibeMap",
        "live_url": "https://vibemap.vercel.app",
        "tech": r"Python, pandas, scikit-learn, SQL, Flask, React, TypeScript, Docker, ECharts, Power BI, Tableau",
        "bullets": [
            r"Designed an end-to-end data pipeline (CSV ingestion $\rightarrow$ SQL cleaning $\rightarrow$ K-Means/KNN model training) and built interactive Power BI/Tableau dashboards to surface insights from processed datasets.",
            r"Built and deployed an 8-endpoint REST API with React/TypeScript frontend --- delivered 125 unit tests at 88\% code coverage, demonstrating data validation discipline and quality assurance practices.",
            r"Deployed full-stack solution to production (Vercel/Render) with SQLite backend and serialized ML models, owning end-to-end delivery from design through launch.",
        ],
    },
    {
        "name": "SecureShop Risk Assessment",
        "label": "Personal Project",
        "dates": "Feb 2025",
        "github_url": "https://github.com/jeff13in/SecureShop-Risk-Assessment",
        "live_url": "",
        "tech": "NIST CSF, PCI-DSS, GDPR, OWASP, Excel",
        "bullets": [
            r"Quantified risk exposure through loss expectancy calculations (\$450K exposure, \$93K remediation, 383\% ROI) and produced a prioritized remediation roadmap with cost-justified controls and a 24-KRI Excel dashboard.",
        ],
    },
    {
        "name": "Instagram Engagement Automation Platform",
        "label": "Brock Uni Project",
        "dates": "Sept 2025 -- Dec 2025",
        "github_url": "https://github.com/jeff13in/Instagram-Comment-to-Get-Automation",
        "live_url": "",
        "tech": "Python, Flask, SQLAlchemy, OAuth 2.0, GitHub Actions",
        "bullets": [
            r"Implemented OAuth 2.0 authentication and SQLAlchemy-backed webhook processing achieving 98.7\% automated response success rate --- CI/CD via GitHub Actions for zero-downtime deployments.",
        ],
    },
]

PROFESSIONAL_DEVELOPMENT = [
    {
        "header": r"Cybersecurity Executive | Brock's Cybersecurity Club | Sept 2023 -- Present",
        "bullets": [
            r"Organize and host CTF competitions and cybersecurity workshops, including sessions with the Chief Security Officer of Microsoft.",
        ],
    },
    {
        "header": r"Toronto CTF | Cybersecurity Ontario | Oct 2025",
        "bullets": [
            r"Investigated simulated enterprise security incidents using Splunk SIEM, analyzing log entries to identify IOCs, suspicious authentication patterns, and attacker behavior in a time-pressured environment.",
        ],
    },
    {
        "header": r"CTF Practice | TryHackMe \& HackTheBox | Jan 2023 -- Present",
        "bullets": [
            r"Regularly practice offensive and defensive techniques including web exploitation, privilege escalation, network enumeration, and reverse engineering across realistic lab environments.",
        ],
    },
]

# Pairs: (left column, right column) — None = empty cell
CERTIFICATIONS = [
    (r"\textbf{Google Cybersecurity Professional Certificate} | Coursera | Jul 2024",
     r"\textbf{Virtual Security Analyst} | Deloitte"),
    (r"\textbf{AWS Cloud Practitioner Essentials} | IBM | Feb 2026",
     r"\textbf{Security Engineer Path} | TryHackMe"),
    (r"\textbf{Jr Penetration Tester Path} | TryHackMe | Sept 2024",
     r"\textbf{CompTIA Security+} | In Preparation"),
    (r"\textbf{HTB Certified Junior Cybersecurity Associate Path} | HackTheBox | Dec 2025",
     None),
]


# ── Gemini tailoring ──────────────────────────────────────────────────────────

TAILOR_PROMPT = """\
You are tailoring a software engineer's resume for a specific job.

JOB DESCRIPTION:
{job_description}

CURRENT SUMMARY:
{summary}

AVAILABLE PROJECTS (pick 3-4 most relevant):
{projects_json}

INSTRUCTIONS:
1. Rewrite the summary (2-3 sentences) to target this specific job. Keep all facts accurate.
2. Select 3-4 projects from the list that are most relevant to the job.
3. For each selected project, write 2-3 bullet points emphasizing the aspects most relevant to this job.
4. Keep all facts accurate: same technologies, same numbers, same outcomes. Do NOT invent anything.
5. Use plain ASCII text only. Use -> for arrows, -- for dashes. Write USD 450K, not $450K.

Return ONLY valid JSON, no other text:
{{
  "summary": "tailored summary here",
  "selected_projects": [
    {{
      "name": "exact project name from the list above",
      "bullets": ["bullet 1", "bullet 2", "bullet 3"]
    }}
  ]
}}"""


def tailor_with_gemini(job: dict) -> dict:
    """
    Returns dict with 'summary' (str) and 'projects' (list matching ALL_PROJECTS shape).
    Falls back to base content on any failure.
    """
    base = {"summary": BASE_SUMMARY, "projects": ALL_PROJECTS}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY -- using base resume content")
        return base

    description = job.get("description", "")
    if not description and job.get("url"):
        print(f"Fetching job description from {job['url']}")
        description = fetch_description(job["url"])
    if not description:
        description = f"{job['title']} position at {job['company']}."

    projects_for_prompt = [
        {"name": p["name"], "tech": p["tech"], "current_bullets": p["bullets"]}
        for p in ALL_PROJECTS
    ]

    prompt = TAILOR_PROMPT.format(
        job_description=description,
        summary=BASE_SUMMARY,
        projects_json=json.dumps(projects_for_prompt, indent=2),
    )

    for attempt in range(4):
        try:
            resp = requests.post(
                GEMINI_URL,
                params={"key": api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60,
            )
            if resp.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"Rate limited. Waiting {wait}s (attempt {attempt + 1}/4)...")
                time.sleep(wait)
                continue
            resp.raise_for_status()

            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]

            # Parse JSON — handle cases where Gemini wraps it in prose
            data = None
            try:
                data = json.loads(raw)
            except Exception:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group())
                    except Exception:
                        pass

            if not data:
                print("Gemini returned unparseable JSON -- using base content")
                return base

            tailored_summary = clean_gemini(data.get("summary", BASE_SUMMARY))

            project_map = {p["name"]: p for p in ALL_PROJECTS}
            tailored_projects = []
            for sp in data.get("selected_projects", []):
                name = sp.get("name", "")
                base_proj = project_map.get(name)
                if not base_proj:
                    print(f"  Skipping unknown project: '{name}'")
                    continue
                proj = dict(base_proj)
                proj["bullets"] = [clean_gemini(b) for b in sp.get("bullets", base_proj["bullets"])]
                tailored_projects.append(proj)

            if not tailored_projects:
                print("Gemini selected no valid projects -- using base content")
                return {"summary": tailored_summary, "projects": ALL_PROJECTS}

            print(f"Gemini tailored summary + {len(tailored_projects)} projects")
            return {"summary": tailored_summary, "projects": tailored_projects}

        except Exception as e:
            print(f"Gemini error (attempt {attempt + 1}): {e}")
            if attempt < 3:
                time.sleep(10)

    print("Gemini failed after 4 attempts -- using base content")
    return base


# ── LaTeX section builders ────────────────────────────────────────────────────

def build_header() -> str:
    return r"""
\begin{center}
  {\huge\bfseries Jeffin Sam Joji}\\[3pt]
  \small
  Ontario, Canada \textbar{}
  (289) 501-1917 \textbar{}
  \href{mailto:ejffinsam14@gmail.com}{ejffinsam14@gmail.com} \textbar{}
  \href{https://linkedin.com/in/jeffin-sam-joji}{LinkedIn} \textbar{}
  \href{https://jeff13in.github.io/Portfolio}{Portfolio} \textbar{}
  \href{https://github.com/jeff13in}{GitHub}
\end{center}"""


def build_summary(text: str) -> str:
    return f"\n\\section{{Summary}}\n{text}"


def build_education() -> str:
    return r"""
\section{Education}

\noindent\textbf{Bachelor of Science (Honours) Computer Science, Concentration in Software Engineering}\\
\noindent Brock University, St.\ Catharines, ON \hfill \textit{Sept 2021 -- Apr 2026}"""


def build_skills() -> str:
    lines = ["\n\\section{Skills}",
             r"\begin{itemize}[label={}, leftmargin=0pt, itemsep=1pt, topsep=2pt]"]
    for label, items in SKILLS:
        lines.append(f"  \\item \\textbf{{{label}:}} {items}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def build_experience() -> str:
    lines = ["\n\\section{Experience}"]
    for exp in EXPERIENCE:
        parts = exp["header"].split(" | ")
        title = parts[0]
        dates = parts[-1]
        org_line = ", ".join(parts[1:-1])
        lines.append(
            f"\n\\noindent\\textbf{{{title}}} \\hfill \\textit{{{dates}}}\\\\[-4pt]\n"
            f"\\textit{{{org_line}}}"
        )
        lines.append("\\begin{itemize}")
        for b in exp["bullets"]:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_projects(projects: list) -> str:
    lines = ["\n\\section{Academic Projects}"]
    for p in projects:
        meta_parts = [f"\\textbf{{{p['name']}}}"]
        if p.get("github_url"):
            meta_parts.append(f"\\href{{{p['github_url']}}}{{\\small GitHub}}")
        if p.get("live_url"):
            meta_parts.append(f"\\href{{{p['live_url']}}}{{\\small Live Demo}}")
        meta_parts.append(p["label"])
        header_line = " \\textbar{} ".join(meta_parts) + f" \\hfill \\textit{{{p['dates']}}}"

        lines.append(f"\n\\noindent{header_line}\\\\[-4pt]")
        lines.append(f"\\textit{{\\small Technologies: {p['tech']}}}")
        lines.append("\\begin{itemize}")
        for b in p["bullets"]:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_professional_development() -> str:
    lines = ["\n\\section{Professional Development}"]
    for item in PROFESSIONAL_DEVELOPMENT:
        parts = item["header"].split(" | ")
        role = parts[0]
        dates = parts[-1]
        org_str = " \\textbar{} ".join(parts[1:-1])
        header_line = f"\\noindent\\textbf{{{role}}} \\textbar{{}} {org_str} \\hfill \\textit{{{dates}}}"
        lines.append(f"\n{header_line}")
        lines.append("\\begin{itemize}")
        for b in item["bullets"]:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_certifications() -> str:
    lines = [
        "\n\\section{Certifications}",
        r"\begin{tabular}{@{}p{0.50\linewidth}@{\hspace{6pt}}p{0.46\linewidth}@{}}",
    ]
    for left, right in CERTIFICATIONS:
        right_cell = right if right else ""
        lines.append(f"  $\\bullet$~{left} & $\\bullet$~{right_cell} \\\\[3pt]")
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def generate(job_id: str) -> str:
    jobs_path = os.path.join(BASE_DIR, "data", "jobs.json")
    with open(jobs_path) as f:
        jobs_data = json.load(f)

    job = next((j for j in jobs_data["jobs"] if j["id"] == job_id), None)
    if not job:
        print(f"Job not found: {job_id}")
        sys.exit(1)

    print(f"Job: {job['title']} at {job['company']}")

    tailored = tailor_with_gemini(job)
    summary = tailored["summary"]
    projects = tailored["projects"]

    doc = "\n".join([
        PREAMBLE,
        build_header(),
        build_summary(summary),
        build_education(),
        build_skills(),
        build_experience(),
        build_projects(projects),
        build_professional_development(),
        build_certifications(),
        "\n\\end{document}",
    ])

    out_path = os.path.join(BASE_DIR, "applications", "pending", f"{job_id}-resume.tex")
    with open(out_path, "w") as f:
        f.write(doc)

    print(f"Written: {out_path}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate-resume-latex.py <job_id>")
        sys.exit(1)
    generate(sys.argv[1])
