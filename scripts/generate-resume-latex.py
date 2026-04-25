#!/usr/bin/env python3
"""
LaTeX resume generator — two-page format with XCharter font.
Compile with: tectonic <file>.tex
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tex_escape(text: str) -> str:
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


# ── Profile data ──────────────────────────────────────────────────────────────

SUMMARIES = {
    "cybersecurity": (
        "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on experience "
        "in security operations, threat detection, and automation. Built ML-based anomaly detection "
        "systems, integrated multi-source threat intelligence APIs, and applied NIST CSF, PCI-DSS, "
        "and OWASP in a comprehensive GRC assessment. Active CTF competitor with certifications in "
        "penetration testing and security engineering."
    ),
    "software_engineering": (
        "Fourth-year Computer Science (Honours) student graduating April 2026, with production experience "
        "building full-stack and mobile applications at an AI startup. Strong front-end craft in React "
        "and TypeScript, paired with full-stack backend skills across REST APIs, CI/CD, and cloud "
        "deployment. Proven ability to translate complex data and AI outputs into polished, intuitive interfaces."
    ),
    "data_ml": (
        "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on experience "
        "in data engineering, ML model deployment, and analytics. Built end-to-end data pipelines, "
        "deployed production ML systems, and created interactive dashboards using Power BI and Tableau. "
        "Proficient in Python, SQL, and cloud deployment."
    ),
}

SKILLS = {
    "cybersecurity": [
        (r"Security Operations \& Tools", r"Splunk SIEM, Burp Suite, Nmap, Metasploit, Wireshark, Kali Linux, IDS/IPS, EDR concepts"),
        (r"Scripting \& Automation",       r"Python (automation, ML, API integration), Bash, PowerShell, GitHub Actions CI/CD"),
        (r"Cloud \& Platforms",            r"AWS Cloud Practitioner, Docker, Linux (Kali/Ubuntu), Windows, Azure (familiarity)"),
        (r"Frameworks \& GRC",             r"NIST CSF, PCI-DSS, GDPR, OWASP, Identity \& Access Management"),
        (r"Development",                   r"React/TypeScript, Flask REST APIs, PostgreSQL, OAuth 2.0, n8n/Make automation"),
    ],
    "software_engineering": [
        (r"Frontend",          r"React, React Native, TypeScript, JavaScript, HTML/CSS, Tailwind, Expo SDK, Responsive Design, Component Libraries"),
        (r"Backend \& APIs",   r"Java, C++, Python (Flask, Django), Node.js, RESTful APIs, GraphQL, OAuth 2.0, Webhooks"),
        (r"Databases",         r"PostgreSQL, SQLite, Supabase, Firebase, SQL queries, data modeling"),
        (r"DevOps \& Cloud",   r"GitHub Actions CI/CD, Docker, AWS, Git/GitHub, Gunicorn, Vercel, Render"),
        (r"Data \& AI",        r"scikit-learn, pandas, NumPy, OpenAI API, Claude API, ECharts, Tableau, Power BI, ETL pipelines"),
        (r"Design \& Tooling", r"Design systems, Figma, Postman, ESLint, Agile / Scrum"),
    ],
    "data_ml": [
        (r"Data \& Analytics", r"SQL (PostgreSQL, SQLite), Python (pandas, NumPy, scikit-learn), ETL Pipelines, Power BI, Tableau, ECharts"),
        (r"ML \& AI",          r"TensorFlow, scikit-learn, Isolation Forest, DBSCAN, K-Means, KNN, NLP, OpenAI API, Claude API"),
        (r"DevOps \& Cloud",   r"AWS, Docker, CI/CD (GitHub Actions), Git/GitHub, Vercel, Render"),
        (r"Development",       r"Python, JavaScript/TypeScript, Flask, React, RESTful APIs, n8n/Make automation"),
        (r"Design \& Tooling", r"Figma, Postman, Agile / Scrum"),
    ],
}

EXPERIENCE = [
    {
        "title": "Software Engineer Intern",
        "company": "Karmeka",
        "location": "Toronto, ON",
        "dates": "Aug 2025 -- Present",
        "bullets": {
            "cybersecurity": [
                r"Developed and maintained RESTful APIs integrating external data sources and AI services, applying secure coding practices and input validation across enterprise platforms.",
                r"Established GitHub Actions CI/CD pipelines automating build, test, and deployment, cutting release cycle time by 40\% and ensuring consistent cross-environment delivery.",
                r"Built automated OCR document parsing pipelines reducing manual data entry by 60\% --- directly analogous to automating routine security operations and log processing tasks.",
                r"Integrated OpenAI and Claude APIs for internal business workflow automation, bridging security requirements with technical execution in fast-moving agile sprints.",
            ],
            "software_engineering": [
                r"Owned the full design system for the Karmeka Customers mobile app --- defined brand tokens, card layouts, status badges, and reusable component library across 4 tab screens and 6+ additional screens in React Native / Expo SDK 54 / TypeScript.",
                r"Built and maintained a typed REST API client covering 15+ endpoints (vehicles, appointments, workshops, quotes) with TTL-based in-memory caching and foreground-resume auto-refresh, eliminating redundant network calls and keeping UI state consistent.",
                r"Integrated OpenAI and Claude APIs to automate internal business workflows and document parsing (OCR pipelines), reducing manual data entry by 60\% and surfacing AI outputs through clean, actionable UI components.",
                r"Established GitHub Actions CI/CD pipelines automating build, test, and deployment across environments, cutting release cycle time by 40\% and enforcing consistent cross-platform delivery.",
                r"Collaborated in fast-moving agile sprints, translating business requirements into shippable features while iterating on UX based on stakeholder feedback.",
            ],
            "data_ml": [
                r"Designed and maintained REST APIs integrating AI services and external data sources, optimizing data flow and enabling real-time delivery across enterprise platforms.",
                r"Integrated OpenAI and Claude APIs to automate document parsing (OCR pipelines), reducing manual data entry by 60\% through intelligent data extraction and processing.",
                r"Established GitHub Actions CI/CD pipelines, reducing release cycle time by 40\% while ensuring cross-environment consistency.",
                r"Developed cross-platform mobile and full-stack web solutions (React Native, Python/Flask), demonstrating adaptability across technology stacks in agile environments.",
            ],
        },
    },
    {
        "title": "Software Developer / AI Engineer",
        "company": "Venture for Canada Intrapreneurship",
        "location": "Remote",
        "dates": "Oct 2025 -- Nov 2025",
        "bullets": {
            "all": [
                r"Built an AI-powered full-stack platform serving 500+ active users --- React/TypeScript frontend with Python backend enabling personalized newsletter and social media content generation from user-defined topics and sources.",
                r"Designed a content aggregation pipeline using n8n/Make automation to collect, filter, and summarize data from 50+ sources daily --- Python NLP/ML models improved content relevance signal by 60\%.",
                r"Implemented prompt engineering systems using OpenAI and Claude APIs for automated outreach, increasing booking response rates by 40\% and cutting manual effort by 70\%.",
                r"Maintained 99.5\% uptime with Docker containerization --- documented architecture and workflows, reducing new developer onboarding time by 40\%.",
            ],
        },
    },
    {
        "title": "Supervisor",
        "company": "Digital Attractions",
        "location": "Niagara Falls, ON",
        "dates": "Mar 2025 -- Present",
        "bullets": {
            "all": [
                r"Led structured onboarding and training for new team members, improving operational efficiency by 35\% through process documentation.",
                r"Implemented systematic troubleshooting processes to resolve technical issues, reducing customer wait times by 25\%.",
            ],
        },
    },
]

PROJECTS = {
    "cybersecurity": [
        {
            "name": "AI Threat Detection System",
            "url": "https://github.com/jeff13in/AI-threat-Detection",
            "url_display": r"github.com/jeff13in/AI-threat-Detection",
            "date": "Dec 2025",
            "tech": r"Python, scikit-learn, TensorFlow, VirusTotal API, AbuseIPDB, CVE CIRCL, PostgreSQL, Docker",
            "bullets": [
                r"Built ML-powered anomaly detection using Isolation Forest and DBSCAN clustering to identify suspicious behavioral patterns in log and event data, aligned with SOC threat monitoring and incident triage workflows.",
                r"Integrated four threat intelligence APIs (VirusTotal, AbuseIPDB, OTX AlienVault, CVE CIRCL) to build a comprehensive multi-source intelligence aggregation pipeline, mirroring enterprise threat enrichment architectures.",
                r"Deployed Kafka event streaming with Elasticsearch for scalable log ingestion and indexed alerting, directly replicating modern SIEM data pipeline architecture.",
            ],
        },
        {
            "name": "SecureShop Risk Assessment",
            "url": "https://github.com/jeff13in/SecureShop-Risk-Assessment",
            "url_display": r"github.com/jeff13in/SecureShop-Risk-Assessment",
            "date": "Feb 2025",
            "tech": r"NIST CSF, PCI-DSS, GDPR, OWASP, Excel",
            "bullets": [
                r"Conducted a comprehensive security assessment of a simulated e-commerce environment applying NIST CSF, PCI-DSS, GDPR, and OWASP frameworks to identify 18 control gaps.",
                r"Quantified risk exposure through loss expectancy calculations (\$450K exposure, \$93K remediation, 383\% ROI) and produced a prioritized remediation roadmap with a 24-KRI Excel dashboard.",
            ],
        },
        {
            "name": "VibeMap",
            "url": "https://github.com/jeff13in/VibeMap",
            "url_display": "github.com/jeff13in/VibeMap",
            "date": "Jan -- Feb 2026",
            "tech": r"Python, pandas, scikit-learn, SQL, Flask, React, TypeScript, Docker",
            "bullets": [
                r"Built and deployed full-stack application with 8-endpoint REST API --- delivered 125 unit tests at 88\% code coverage across data cleaning, recommender, and clustering modules.",
            ],
        },
    ],
    "software_engineering": [
        {
            "name": "WatchNext Mobile App",
            "url": "https://github.com/jeff13in/WatchNext",
            "url_display": "github.com/jeff13in/WatchNext",
            "date": "Jan 2026 -- Apr 2026",
            "tech": r"Java, Firebase Auth, Supabase, TMDb API, Android, MVC",
            "bullets": [
                r"Built a content-based recommendation engine in Java that constructs a weighted taste profile from user activity (liked +2, watched +1, disliked $-$2) across genre tags, scoring unseen candidates with a custom formula combining tag overlap, mood adjustment, TMDb rating, and popularity signals.",
                r"Implemented a mood-aware filtering layer (Happy, Excited, Relaxed, Scared, Emotional) that dynamically re-weights genre preferences and expands the candidate pool, surfacing top-20 recommendations with per-item explanations.",
                r"Built a full-featured Android app using MVC architecture --- browse/discover, real-time search, personalized watchlist management, integrated Firebase Auth, Supabase (PostgreSQL REST), and TMDb API via Retrofit.",
            ],
        },
        {
            "name": "VibeMap",
            "url": "https://github.com/jeff13in/VibeMap",
            "url_display": "github.com/jeff13in/VibeMap",
            "date": "Jan -- Feb 2026",
            "tech": r"Python, pandas, scikit-learn, SQL, Flask, React, TypeScript, Docker, ECharts, Power BI",
            "bullets": [
                r"Designed an end-to-end data pipeline (CSV ingestion $\rightarrow$ SQL cleaning $\rightarrow$ K-Means/KNN model training) and built interactive Power BI/Tableau dashboards to surface insights from processed datasets.",
                r"Built and deployed an 8-endpoint REST API with React/TypeScript frontend --- 125 unit tests at 88\% code coverage, deployed to production on Vercel/Render with SQLite backend and serialized ML models.",
            ],
        },
        {
            "name": "Instagram Engagement Automation Platform",
            "url": "https://github.com/jeff13in/Instagram-Comment-to-Get-Automation",
            "url_display": r"github.com/jeff13in/Instagram-Automation",
            "date": "Sept -- Dec 2025",
            "tech": r"Python, Flask, SQLAlchemy, OAuth 2.0, GitHub Actions",
            "bullets": [
                r"Implemented OAuth 2.0 authentication and SQLAlchemy-backed webhook processing achieving 98.7\% automated response success rate --- CI/CD via GitHub Actions for zero-downtime deployments.",
            ],
        },
    ],
    "data_ml": [
        {
            "name": "VibeMap",
            "url": "https://github.com/jeff13in/VibeMap",
            "url_display": "github.com/jeff13in/VibeMap",
            "date": "Jan -- Feb 2026",
            "tech": r"Python, pandas, scikit-learn, SQL, Flask, React, TypeScript, Docker, ECharts, Power BI, Tableau",
            "bullets": [
                r"Designed an end-to-end data pipeline (CSV ingestion $\rightarrow$ SQL cleaning $\rightarrow$ K-Means/KNN model training) and built interactive Power BI/Tableau dashboards to surface insights from processed datasets.",
                r"Built and deployed an 8-endpoint REST API with React/TypeScript frontend --- 125 unit tests at 88\% code coverage, deployed to production on Vercel/Render with serialized ML models.",
                r"Owned end-to-end delivery from data design through production launch, demonstrating full-stack data engineering ownership.",
            ],
        },
        {
            "name": "AI Threat Detection System",
            "url": "https://github.com/jeff13in/AI-threat-Detection",
            "url_display": r"github.com/jeff13in/AI-threat-Detection",
            "date": "Dec 2025",
            "tech": r"Python, scikit-learn, TensorFlow, VirusTotal API, Kafka, Elasticsearch, PostgreSQL, Docker",
            "bullets": [
                r"Built ML-powered anomaly detection using Isolation Forest and DBSCAN clustering; integrated multi-source threat intelligence APIs for comprehensive data aggregation.",
                r"Deployed data pipeline with Kafka event streaming and Elasticsearch for scalable ingestion and indexed search, demonstrating production-grade data engineering.",
            ],
        },
    ],
}

PROFESSIONAL_DEVELOPMENT = [
    {
        "title": "Cybersecurity Executive",
        "org": r"Brock's Cybersecurity Club",
        "dates": "Sept 2023 -- Present",
        "bullets": [
            r"Organize and host CTF competitions and cybersecurity workshops, including sessions with the Chief Security Officer of Microsoft.",
        ],
    },
    {
        "title": "Toronto CTF",
        "org": "Cybersecurity Ontario",
        "dates": "Oct 2025",
        "bullets": [
            r"Investigated simulated enterprise security incidents using Splunk SIEM, analyzing log entries to identify IOCs, suspicious authentication patterns, and attacker behavior in a time-pressured environment.",
        ],
    },
    {
        "title": r"CTF Practice",
        "org": r"TryHackMe \& HackTheBox",
        "dates": "Jan 2023 -- Present",
        "bullets": [
            r"Regularly practice offensive and defensive techniques including web exploitation, privilege escalation, network enumeration, and reverse engineering across realistic lab environments.",
        ],
    },
]

CERTIFICATIONS = [
    (r"\textbf{Google Cybersecurity Professional Certificate} \textbar{} Coursera \textbar{} Jul 2024",
     r"\textbf{Virtual Security Analyst} \textbar{} Deloitte"),
    (r"\textbf{AWS Cloud Practitioner Essentials} \textbar{} IBM \textbar{} Feb 2026",
     r"\textbf{Security Engineer Path} \textbar{} TryHackMe"),
    (r"\textbf{Jr Penetration Tester Path} \textbar{} TryHackMe \textbar{} Sept 2024",
     r"\textbf{CompTIA Security+} \textbar{} In Preparation"),
    (r"\textbf{HTB Junior Cybersecurity Associate} \textbar{} HackTheBox \textbar{} Dec 2025",
     None),
]


# ── Section builders ──────────────────────────────────────────────────────────

def build_header() -> str:
    return r"""
\begin{center}
  {\huge\bfseries Jeffin Sam Joji}\\[4pt]
  \small
  Ontario, Canada \textbar{}
  (289) 501-1917 \textbar{}
  \href{mailto:ejffinsam14@gmail.com}{ejffinsam14@gmail.com} \textbar{}
  \href{https://linkedin.com/in/jeffin-sam-joji}{LinkedIn} \textbar{}
  \href{https://jeff13in.github.io/Portfolio}{Portfolio} \textbar{}
  \href{https://github.com/jeff13in}{GitHub}
\end{center}"""


def build_summary(category: str) -> str:
    text = SUMMARIES.get(category, SUMMARIES["software_engineering"])
    return f"\n\\section{{Summary}}\n{text}"


def build_education() -> str:
    return r"""
\section{Education}

\noindent\textbf{Bachelor of Science (Honours) Computer Science, Concentration in Software Engineering} \hfill \textit{Sept 2021 -- Apr 2026}\\[-4pt]
\textit{Brock University, St.\ Catharines, ON}"""


def build_skills(category: str) -> str:
    skill_set = SKILLS.get(category, SKILLS["software_engineering"])
    lines = ["\n\\section{Skills}",
             r"\begin{itemize}[label={}, leftmargin=0pt, itemsep=1pt, topsep=2pt]"]
    for label, items in skill_set:
        lines.append(f"  \\item \\textbf{{{label}:}} {items}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def build_experience(category: str) -> str:
    lines = ["\n\\section{Experience}"]
    for exp in EXPERIENCE:
        bullets = exp["bullets"].get(category) or exp["bullets"].get("all", [])
        lines.append(
            f"\n\\noindent\\textbf{{{tex_escape(exp['title'])}}} "
            f"\\hfill \\textit{{{exp['dates']}}}\\\\[-4pt]\n"
            f"\\textit{{{tex_escape(exp['company'])}, {tex_escape(exp['location'])}}}"
        )
        lines.append("\\begin{itemize}")
        for b in bullets:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_projects(category: str) -> str:
    projects = PROJECTS.get(category, PROJECTS["software_engineering"])
    lines = ["\n\\section{Academic Projects}"]
    for p in projects:
        lines.append(
            f"\n\\noindent\\textbf{{{tex_escape(p['name'])}}} "
            f"\\textbar{{}} \\href{{{p['url']}}}{{\\small GitHub}} "
            f"\\hfill \\textit{{{p['date']}}}\\\\[-4pt]\n"
            f"\\textit{{\\small Technologies: {p['tech']}}}"
        )
        lines.append("\\begin{itemize}")
        for b in p["bullets"]:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_professional_development() -> str:
    lines = ["\n\\section{Professional Development}"]
    for item in PROFESSIONAL_DEVELOPMENT:
        lines.append(
            f"\n\\noindent\\textbf{{{tex_escape(item['title'])}}} "
            f"\\textbar{{}} {item['org']} "
            f"\\hfill \\textit{{{item['dates']}}}"
        )
        lines.append("\\begin{itemize}")
        for b in item["bullets"]:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_certifications() -> str:
    lines = ["\n\\section{Certifications}",
             r"\begin{tabular}{@{}p{0.5\linewidth}@{\hspace{4pt}}p{0.5\linewidth}@{}}"]
    for left, right in CERTIFICATIONS:
        right_cell = right if right else ""
        lines.append(f"  $\\bullet$~{left} & $\\bullet$~{right_cell} \\\\[2pt]")
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

    category = (job.get("categories") or ["software_engineering"])[0]
    if category not in ("cybersecurity", "software_engineering", "data_ml"):
        category = "software_engineering"

    print(f"Generating resume: {job['title']} at {job['company']} [{category}]")

    doc = "\n".join([
        PREAMBLE,
        build_header(),
        build_summary(category),
        build_education(),
        build_skills(category),
        build_experience(category),
        build_projects(category),
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
