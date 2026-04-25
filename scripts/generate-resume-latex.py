#!/usr/bin/env python3
"""
LaTeX resume generator.
Template: 11pt, 0.29in margins, fontawesome5, two-page with repeated header.
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
    text = text.replace("->", r"$\rightarrow$")
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

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[letterpaper,margin=0.29in]{geometry}
\usepackage[colorlinks=true, linkcolor=blue, urlcolor=blue]{hyperref}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{longtable}
\usepackage{array}
\usepackage{booktabs}
\usepackage{setspace}
\usepackage{graphicx}

\titleformat{\section}{\Large\bfseries}{}{0em}{}[\titlerule]

\begin{document}"""


# ── Base resume content ───────────────────────────────────────────────────────

BASE_SUMMARY = (
    "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on experience "
    "in cybersecurity frameworks, risk assessment, and security advisory. Practical background applying "
    "NIST CSF and CIS controls, conducting threat analysis using SIEM platforms, and delivering technical "
    "security guidance. Strong communicator with experience presenting cybersecurity content through "
    "workshops and technical documentation."
)

SKILLS = [
    (r"Security Frameworks \& Standards",
     r"NIST Cybersecurity Framework, CIS Controls, PCI-DSS, GDPR, OWASP, Risk Assessment \& Quantification, Security Control Gap Analysis, Compliance Documentation"),
    (r"Security Operations \& Tools",
     r"Splunk SIEM, SIEM/IDS/IPS Concepts, Threat Intelligence Integration (VirusTotal, AbuseIPDB, OTX AlienVault, CVE CIRCL), Incident Response, IOC Identification, Log Analysis, Burp Suite, Nmap, Metasploit, Wireshark, Kali Linux"),
    (r"Technical \& Infrastructure",
     r"Python (automation, scripting), Bash, PowerShell (basic), SQL, Identity \& Access Management Concepts, Active Directory, Cloud Security (AWS, Azure), Linux/Windows Administration, Docker, CI/CD"),
    (r"Advisory \& Communication",
     r"Technical Documentation, Security Reporting, Stakeholder Communication, Workshop Facilitation, Event Coordination, Webinar Content Development, Cross-Functional Collaboration"),
    (r"Soft Skills",
     r"Analytical Thinking, Problem-Solving, Self-Directed Learning, Team Collaboration, Adaptability, Attention to Detail, Curiosity"),
]

# Header strings contain pre-escaped LaTeX (e.g. \textbar{}) — do not re-escape
EXPERIENCE = [
    {
        "header": r"Software Engineer Intern \textbar{} Karmeka \textbar{} Toronto, ON \textbar{} Aug 2025 - Present",
        "bullets": [
            r"Implemented secure API integration practices and input validation across enterprise platforms, applying defense-in-depth principles to protect data flows and prevent unauthorized access.",
            r"Established automated CI/CD pipelines with integrated security controls, reducing manual deployment errors and ensuring consistent security posture across development and production environments.",
            r"Collaborated with cross-functional stakeholders to translate business requirements into technical security solutions, demonstrating advisory skills in fast-paced agile environment.",
        ],
    },
    {
        "header": r"Software Developer/AI Engineer \textbar{} Venture for Canada Intrapreneurship \textbar{} Remote \textbar{} Oct 2025 - Nov 2025",
        "bullets": [
            r"Built data filtering and validation pipelines processing 50+ sources daily, applying data integrity controls and improving signal-to-noise ratio by 60\%.",
            r"Documented system architecture, security decisions, and operational workflows to support maintainability and knowledge transfer, reducing new developer onboarding time by 40\%.",
            r"Implemented systematic troubleshooting processes to identify and resolve root causes rather than patching symptoms, achieving 99.5\% uptime for production services.",
        ],
    },
    {
        "header": r"Supervisor \textbar{} Digital Attractions \textbar{} Mar 2025 - Present",
        "bullets": [
            r"Led structured onboarding and training for new team members, improving operational efficiency by 35\% through process documentation.",
            r"Implemented systematic troubleshooting processes to resolve technical issues, reducing customer wait times by 25\%.",
        ],
    },
]

# All projects — Gemini selects 3-4 and rewrites bullets per job
ALL_PROJECTS = [
    {
        "name": "SecureShop Risk Assessment",
        "label": "Personal Project",
        "dates": "Feb 2025",
        "github_url": "https://github.com/jeff13in/SecureShop-Risk-Assessment",
        "live_url": "",
        "tech": r"NIST CSF, PCI-DSS, GDPR, OWASP, Excel",
        "bullets": [
            r"Conducted comprehensive security assessment of simulated e-commerce environment applying NIST CSF, PCI-DSS, GDPR, and OWASP frameworks to identify 18 control gaps across technical and administrative domains.",
            r"Quantified risk exposure through loss expectancy calculations (\$450K identified exposure) and delivered prioritized remediation roadmap with cost-justified security controls demonstrating 383\% ROI.",
            r"Produced executive-level security documentation and technical recommendations suitable for presenting to institutional leadership and governance bodies.",
        ],
    },
    {
        "name": "AI Threat Detection System",
        "label": "Personal Project",
        "dates": "Dec 2025",
        "github_url": "https://github.com/jeff13in/AI-threat_Detection",
        "live_url": "",
        "tech": r"Python, scikit-learn, TensorFlow, VirusTotal API, AbuseIPDB, CVE CIRCL, PostgreSQL, Docker",
        "bullets": [
            r"Built ML-powered anomaly detection system using Isolation Forest and DBSCAN clustering to identify suspicious behavioral patterns in log and event data, mirroring enterprise SIEM threat detection workflows.",
            r"Integrated multiple threat intelligence APIs (VirusTotal, AbuseIPDB, OTX AlienVault, CVE CIRCL) to build comprehensive multi-source data aggregation and correlation pipeline for threat enrichment.",
            r"Deployed scalable event streaming architecture with Kafka and Elasticsearch for real-time log ingestion and indexed alerting, demonstrating understanding of enterprise security monitoring infrastructure.",
        ],
    },
    {
        "name": "VibeMap",
        "label": "Personal Project",
        "dates": "Jan 2026 - Feb 2026",
        "github_url": "https://github.com/jeff13in/VibeMap",
        "live_url": "https://vibe-map-azure.vercel.app/",
        "tech": r"Python, pytest, scikit-learn, SQL, Flask, React, TypeScript, Docker, ECharts, Power BI, Tableau",
        "bullets": [
            r"Built full-stack application with 8-endpoint REST API, delivering 125 unit tests at 88\% code coverage demonstrating disciplined quality assurance practices.",
            r"Designed end-to-end data pipeline (CSV ingestion $\rightarrow$ SQL cleaning $\rightarrow$ K-Means/KNN model training) with deployment to production, showcasing data analysis and visualization capabilities relevant to security analytics reporting.",
        ],
    },
    {
        "name": "WatchNext Mobile App",
        "label": "Brock Uni Project",
        "dates": "Jan 2026 - April 2026",
        "github_url": "",
        "live_url": "",
        "tech": r"Java, JUnit, Firebase Auth, Supabase, TMDb API",
        "bullets": [
            r"Developed full-featured Java Android application with Firebase Auth, Supabase database, and TMDb REST API integration using Retrofit library for API communication and data retrieval.",
            r"Implemented MVC architecture with comprehensive manual testing across authentication flows, database CRUD operations, API response handling, and recommendation engine accuracy.",
            r"Performed database testing with SQL queries to validate data integrity, user watchlist operations, and rating/review storage in Supabase PostgreSQL backend.",
        ],
    },
    {
        "name": "Instagram Engagement Automation Platform",
        "label": "Brock Uni Project",
        "dates": "Sept 2025 - Dec 2025",
        "github_url": "https://github.com/jeff13in/Instagram-Comment-to-Get-Automation",
        "live_url": "",
        "tech": r"Python, Flask, SQLAlchemy, OAuth 2.0, GitHub Actions",
        "bullets": [
            r"Implemented OAuth 2.0 authentication and SQLAlchemy-backed webhook processing achieving 98.7\% automated response success rate CI/CD via GitHub Actions for zero-downtime deployments.",
        ],
    },
]

# Header strings contain pre-escaped LaTeX — do not re-escape
PROFESSIONAL_DEVELOPMENT = [
    {
        "header": r"Cybersecurity Executive \textbar{} Brock's Cybersecurity Club \textbar{} Sept 2023 - Present",
        "bullets": [
            r"Organize and host CTF competitions and cybersecurity workshops, including sessions with the \href{https://experiencebu.brocku.ca/event/260543}{Chief Security Officer of Microsoft}.",
        ],
    },
    {
        "header": r"Toronto CTF \textbar{} Cybersecurity Ontario \textbar{} Oct 2025",
        "bullets": [
            r"Investigated simulated enterprise security incidents using Splunk SIEM, analyzing log entries to identify IOCs, suspicious authentication patterns, and attacker behavior in a time-pressured environment.",
        ],
    },
    {
        "header": r"CTF Practice \textbar{} TryHackMe \href{https://tryhackme.com/p/Jeffin14}{link} \& HackTheBox \textbar{} Jan 2023 - Present",
        "bullets": [
            r"Regularly practice offensive and defensive techniques including web exploitation, privilege escalation, network enumeration, and reverse engineering across realistic lab environments.",
        ],
    },
]

CERTIFICATIONS_LEFT = [
    r"\textbf{CompTIA Security+} \textbar{} In Preparation",
    r"\textbf{Google Cybersecurity Professional Certificate} \textbar{} Coursera \textbar{} Jul 2024",
    r"\textbf{AWS Cloud Practitioner Essentials} \textbar{} IBM \textbar{} Feb 2026",
    r"\textbf{HTB Certified Junior Cybersecurity Associate Path} \textbar{} HackTheBox \textbar{} Dec 2025",
]

CERTIFICATIONS_RIGHT = [
    r"\textbf{Virtual Security Analyst} \textbar{} Deloitte",
    r"\textbf{Security Engineer Path} \textbar{} TryHackMe",
    r"\textbf{Jr Penetration Tester} \textbar{} TryHackMe",
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
   Do NOT write a Technologies line — it is appended automatically from the project data.
4. Keep all facts accurate: same technologies, same numbers, same outcomes. Do NOT invent anything.
5. Use plain ASCII text only. Use -> for arrows, -- for dashes. Write USD 450K not $450K.

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
    """Returns dict with 'summary' (str) and 'projects' (list). Falls back to base on failure."""
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
                print("Gemini selected no valid projects -- using base projects")
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
    return r"""\begin{center}
    {\Huge \textbf{Jeffin Sam Joji}}

 Ontario, Canada \textbar{} (289) 501-1917 \textbar{} \href{mailto:ejffinsam14@gmail.com}{ejffinsam14@gmail.com} \textbar{} \href{https://linkedin.com/in/jeffin-sam-joji}{Linkedin} \textbar{} \href{https://jeff13in.github.io/Portfolio/}{Portfolio} \textbar{} \href{https://github.com/jeff13in}{Github}
\end{center}"""


def build_summary(text: str) -> str:
    return f"\n\\section*{{SUMMARY}}\n{text}"


def build_education() -> str:
    return r"""
\section*{EDUCATION}

\textbf{Bachelor of Science (Honours) Computer Science, Concentration in Software Engineering} \\
Brock University, St. Catharines, ON \hfill Sept 2021 -- Apr 2026"""


def build_skills() -> str:
    skill_lines = [f"\\textbf{{{label}:}} {items}" for label, items in SKILLS]
    return "\n\\section*{SKILLS}\n" + ("\\\\\n".join(skill_lines))


def build_experience() -> str:
    lines = ["\n\\section*{EXPERIENCE}"]
    for exp in EXPERIENCE:
        lines.append(f"\\textbf{{{exp['header']}}} ")
        lines.append(r"\begin{itemize}[ leftmargin=1.5em,  topsep=0pt,itemsep=0pt, parsep=0pt]")
        for b in exp["bullets"]:
            lines.append(f"\\item    {b}")
        lines.append("")
        lines.append(r"\end{itemize}")
    return "\n".join(lines)


def build_page2_header() -> str:
    return r"""\newpage
\begin{center}
    {\Huge \textbf{Jeffin Sam Joji}}

 Ontario, Canada \textbar{} (289) 501-1917 \textbar{} \href{mailto:ejffinsam14@gmail.com}{ejffinsam14@gmail.com} \textbar{} \href{https://linkedin.com/in/jeffin-sam-joji}{Linkedin} \textbar{} \href{https://jeff13in.github.io/Portfolio/}{Portfolio} \textbar{} \href{https://github.com/jeff13in}{Github}
\end{center}"""


def build_projects(projects: list) -> str:
    lines = ["\n\\section*{ACADEMIC PROJECTS}"]
    for p in projects:
        name_part = p["name"]
        if p.get("github_url"):
            name_part += f" \\href{{{p['github_url']}}}{{GitHub}}"
        if p.get("live_url"):
            name_part += f" \\textbar{{}} \\href{{{p['live_url']}}}{{Live Demo}}"
        header = f"\\textbf{{{name_part} \\textbar{{}} {p['label']} \\textbar{{}} {p['dates']}}}"

        lines.append(header)
        lines.append(r"\begin{itemize}[leftmargin=1.5em, topsep=0pt, itemsep=0pt, parsep=0pt]")
        for b in p["bullets"]:
            lines.append(f"\\item    {b}")
        lines.append(f"\\item    Technologies: {p['tech']}")
        lines.append(r"\end{itemize}")
    return "\n".join(lines)


def build_professional_development() -> str:
    lines = ["\n\\section*{PROFESSIONAL DEVELOPMENT}"]
    for item in PROFESSIONAL_DEVELOPMENT:
        lines.append(f"\\textbf{{{item['header']}}} ")
        lines.append(r"\begin{itemize}[leftmargin=1.5em, topsep=0pt,itemsep=0pt, parsep=0pt]")
        for b in item["bullets"]:
            lines.append(f"\\item    {b}")
        lines.append("")
        lines.append(r"\end{itemize}")
    return "\n".join(lines)


def build_certifications() -> str:
    lines = [
        "\n\\vfill",
        "{\\footnotesize",
        "\\section*{CERTIFICATIONS}",
        "\\vspace{-10pt}",
        "\\noindent",
        "\\begin{minipage}[t]{0.70\\textwidth}",
        "\\begin{itemize}[leftmargin=*, itemsep=0pt, topsep=0pt, parsep=0pt, partopsep=0pt]",
    ]
    for cert in CERTIFICATIONS_LEFT:
        lines.append(f"\\item {cert}")
    lines += [
        "\\end{itemize}",
        "\\end{minipage}",
        "\\hfill",
        "\\begin{minipage}[t]{0.46\\textwidth}",
        "\\begin{itemize}[leftmargin=*, itemsep=0pt, topsep=0pt, parsep=0pt, partopsep=0pt]",
    ]
    for cert in CERTIFICATIONS_RIGHT:
        lines.append(f"\\item {cert}")
    lines += [
        "\\end{itemize}",
        "\\end{minipage}",
        "}",
    ]
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
        build_page2_header(),
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
