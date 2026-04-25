#!/usr/bin/env python3
"""
LaTeX resume generator — produces a role-specific .tex file from structured profile data.
Compile the output with: tectonic <file>.tex
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tex_escape(text: str) -> str:
    """Escape LaTeX special characters in externally-sourced strings (job title, company)."""
    for old, new in [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]:
        text = text.replace(old, new)
    return text


# ---------------------------------------------------------------------------
# Profile data  (LaTeX-escaped inline where needed)
# ---------------------------------------------------------------------------

SUMMARIES = {
    "cybersecurity": (
        "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on "
        "experience in security operations, threat detection, and scripting. Practical background "
        "using Splunk SIEM for log analysis and IOC identification, CTF participation, and building "
        "ML-based anomaly detection systems. Familiar with NIST frameworks, vulnerability "
        "assessment, and automation using Python and Bash."
    ),
    "software_engineering": (
        "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on "
        "experience building integrations, APIs, and full-stack applications. Proven track record "
        "designing data exchange systems, implementing CI/CD pipelines, and working in agile "
        "environments to deliver high-quality solutions at scale."
    ),
    "data_ml": (
        "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on "
        "experience in data engineering, ML model deployment, and analytics. Built end-to-end data "
        "pipelines, deployed production ML systems, and created interactive dashboards using "
        "Power BI and Tableau. Proficient in Python, SQL, and cloud deployment."
    ),
}

EXPERIENCE = [
    {
        "title": "Software Engineer Intern",
        "company": "Karmeka",
        "location": "Toronto, ON",
        "dates": "Aug 2025 -- Present",
        "bullets": {
            "cybersecurity": [
                r"Developed and maintained RESTful APIs integrating external data sources and AI services, applying secure coding practices and validating data flows across enterprise platforms.",
                r"Established CI/CD pipelines with GitHub Actions to automate build, test, and deployment workflows, cutting release cycle time by 40\% and ensuring consistent cross-environment deployments.",
                r"Built automated document parsing pipelines using OCR and Python scripting, reducing manual processing by 60\% --- directly analogous to automating routine security operations tasks.",
                r"Translated business requirements into AI-powered automation solutions, bridging stakeholder needs with technical execution in fast-moving agile sprints.",
            ],
            "software_engineering": [
                r"Designed and maintained RESTful APIs integrating external data sources and AI services, optimizing data flow and enabling real-time information delivery across enterprise platforms.",
                r"Established CI/CD pipelines using GitHub Actions, automating build, test, and deployment workflows --- reducing release cycle time by 40\% while ensuring consistent cross-environment deployments.",
                r"Translated business process requirements into AI-powered automation solutions using OpenAI platform, bridging stakeholder needs and technical execution in an iterative product development cycle.",
                r"Developed cross-platform mobile and full-stack web solutions (React Native, React, Python/Flask), demonstrating adaptability across technology stacks in fast-moving agile sprints.",
            ],
            "data_ml": [
                r"Designed and maintained RESTful APIs integrating external data sources and AI services, optimizing data flow and enabling real-time information delivery across enterprise platforms.",
                r"Established CI/CD pipelines using GitHub Actions, automating build, test, and deployment workflows --- reducing release cycle time by 40\% while ensuring consistent cross-environment deployments.",
                r"Applied OCR and automated document parsing pipelines to streamline business workflows, reducing manual data entry by 60\% through process improvement and intelligent automation.",
                r"Developed cross-platform mobile and full-stack web solutions (React Native, React, Python/Flask), demonstrating adaptability across technology stacks in fast-moving agile sprints.",
            ],
        },
    },
    {
        "title": "Software Developer / AI Engineer",
        "company": "Venture for Canada",
        "location": "Remote",
        "dates": "Oct 2025 -- Nov 2025",
        "bullets": {
            "all": [
                r"Engineered content aggregation and curation pipelines using Python-based NLP/ML models to process and filter data from 50+ online sources daily, improving signal-to-noise ratio by 60\%.",
                r"Built scalable backend services with Docker containerization achieving 99.5\% uptime; tracked and resolved recurring system issues by identifying root causes rather than patching symptoms.",
                r"Documented system architecture, technical decisions, and workflows to support maintainability --- reducing new developer onboarding time by 40\%.",
            ]
        },
    },
    {
        "title": "Supervisor",
        "company": "Digital Attractions",
        "location": "Niagara Falls, ON",
        "dates": "Mar 2025 -- Present",
        "bullets": {
            "all": [
                r"Led onboarding and training for new team members, improving operational efficiency by 35\% through structured documentation.",
                r"Implemented systematic troubleshooting processes to resolve technical issues, reducing customer wait times by 25\%.",
            ]
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
            "bullets": [
                r"Built ML-powered anomaly detection using Isolation Forest and DBSCAN clustering to identify suspicious behavioral patterns in log and event data, aligned with SOC threat monitoring workflows.",
                r"Integrated VirusTotal, AbuseIPDB, OTX AlienVault, and CVE CIRCL APIs to build a comprehensive multi-source threat intelligence aggregation pipeline.",
                r"Deployed with Kafka event streaming and Elasticsearch for scalable log ingestion and indexed alerting, mirroring enterprise SIEM architectures.",
            ],
        },
        {
            "name": "SecureShop Risk Assessment",
            "url": "https://github.com/jeff13in/SecureShop-Risk-Assessment",
            "url_display": r"github.com/jeff13in/SecureShop-Risk-Assessment",
            "subtitle": r"GRC --- NIST CSF, PCI-DSS, GDPR, OWASP",
            "date": "Feb 2025",
            "bullets": [
                r"Conducted a comprehensive security assessment of a simulated e-commerce environment, applying NIST CSF, PCI-DSS, GDPR, and OWASP frameworks to identify 18 control gaps.",
                r"Quantified risk exposure through loss expectancy calculations (\$450K) and delivered a prioritized remediation roadmap with cost-justified controls.",
            ],
        },
    ],
    "software_engineering": [
        {
            "name": "Instagram Engagement Automation Platform",
            "url": "https://github.com/jeff13in/Instagram-Comment-to-Get-Automation",
            "url_display": r"github.com/jeff13in/Instagram-Automation",
            "date": "Sept -- Dec 2025",
            "bullets": [
                r"Implemented OAuth 2.0 authentication and SQLAlchemy-backed webhook processing achieving 98.7\% automated response success rate.",
                r"Established CI/CD via GitHub Actions for zero-downtime deployments across staging and production environments.",
            ],
        },
        {
            "name": "VibeMap",
            "url": "https://github.com/jeff13in/VibeMap",
            "url_display": "github.com/jeff13in/VibeMap",
            "date": "Jan -- Feb 2026",
            "bullets": [
                r"Built and deployed full-stack application with 8-endpoint REST API; delivered 125 unit tests at 88\% code coverage across data cleaning, recommender, and clustering modules.",
                r"Designed end-to-end data pipeline (CSV ingestion \textrightarrow{} SQL cleaning \textrightarrow{} K-Means/KNN model training) and deployed to production on Vercel/Render.",
            ],
        },
    ],
    "data_ml": [
        {
            "name": "VibeMap",
            "url": "https://github.com/jeff13in/VibeMap",
            "url_display": "github.com/jeff13in/VibeMap",
            "date": "Jan -- Feb 2026",
            "bullets": [
                r"Built and deployed full-stack application with 8-endpoint REST API; delivered 125 unit tests at 88\% code coverage across data cleaning, recommender, and clustering modules.",
                r"Designed end-to-end data pipeline (CSV ingestion \textrightarrow{} SQL cleaning \textrightarrow{} K-Means/KNN model training) and deployed to production on Vercel/Render with serialized ML models.",
                r"Created interactive Power BI and Tableau dashboards to visualize recommendation patterns and clustering results.",
            ],
        },
        {
            "name": "AI Threat Detection System",
            "url": "https://github.com/jeff13in/AI-threat-Detection",
            "url_display": r"github.com/jeff13in/AI-threat-Detection",
            "date": "Dec 2025",
            "bullets": [
                r"Built ML-powered anomaly detection using Isolation Forest and DBSCAN clustering; integrated multi-source threat intelligence APIs (VirusTotal, AbuseIPDB, OTX AlienVault) for data aggregation.",
                r"Deployed data pipeline with Kafka event streaming and Elasticsearch for scalable ingestion and indexed search.",
            ],
        },
    ],
}

SKILLS = {
    "cybersecurity": [
        (r"Security Operations \& Tools", r"Splunk SIEM, Burp Suite, Nmap, Metasploit, Wireshark, EDR concepts, Kali Linux, IDS/IPS familiarity"),
        (r"Scripting \& Automation", r"Python (automation, ML, API integration), Bash, PowerShell (basic), GitHub Actions CI/CD"),
        (r"Cloud \& OS Platforms", r"AWS Cloud Practitioner, Docker, Linux (Kali/Ubuntu), Windows, Azure (familiarity)"),
        (r"Security Frameworks", r"NIST CSF, PCI-DSS, GDPR, OWASP, Identity \& Access Management concepts"),
        (r"Development", r"Flask REST APIs, React/TypeScript, SQLite/PostgreSQL, OAuth 2.0, n8n/Make automation"),
    ],
    "software_engineering": [
        (r"Languages \& Frameworks", r"Python, JavaScript/TypeScript, Java, C++, React, Node.js, Flask, Django"),
        (r"Cloud \& DevOps", r"AWS, Docker, CI/CD (GitHub Actions), Git/GitHub, Vercel/Render"),
        (r"Data \& APIs", r"PostgreSQL, SQLite, RESTful APIs, OAuth 2.0, Webhooks, API Integration"),
        (r"Development Tools", r"Linux (Ubuntu), Windows, Bash scripting, n8n/Make automation"),
    ],
    "data_ml": [
        (r"Data \& Analytics", r"SQL (PostgreSQL, SQLite), Python (pandas, NumPy, scikit-learn), ETL Pipelines, Power BI, Tableau"),
        (r"ML \& AI", r"TensorFlow, PyTorch, Isolation Forest, DBSCAN, K-Means, KNN, NLP, Model deployment"),
        (r"Cloud \& DevOps", r"AWS, Docker, CI/CD (GitHub Actions), Git/GitHub"),
        (r"Development", r"Python, JavaScript, Flask, React/TypeScript, RESTful APIs"),
    ],
}

CERTIFICATIONS = [
    r"Google Cybersecurity Professional",
    r"TryHackMe Jr.\ Penetration Tester \& Security Engineer",
    r"HackTheBox Junior Cybersecurity Associate",
    r"AWS Cloud Practitioner",
    r"Deloitte \& PwC Virtual Security Analyst",
]

# ---------------------------------------------------------------------------
# LaTeX builders
# ---------------------------------------------------------------------------

PREAMBLE = r"""\documentclass[10pt, letterpaper]{article}

\usepackage[top=0.45in, bottom=0.45in, left=0.55in, right=0.55in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage[hidelinks]{hyperref}
\usepackage{tabularx}
\usepackage{textcomp}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}

\titleformat{\section}{\bfseries\normalsize}{}{0em}{\uppercase}[\vspace{2pt}\hrule\vspace{4pt}]
\titlespacing*{\section}{0pt}{10pt}{2pt}

\setlist[itemize]{leftmargin=14pt, label=\textbullet, itemsep=1pt, topsep=3pt, parsep=0pt}

\begin{document}"""


def build_header() -> str:
    return r"""
\begin{center}
  {\huge \textbf{JEFFIN SAM JOJI}} \\[5pt]
  \small
  Niagara Falls, ON \quad$|$\quad
  (289) 501-1917 \quad$|$\quad
  \href{mailto:ejffinsam14@gmail.com}{ejffinsam14@gmail.com} \quad$|$\quad
  \href{https://linkedin.com/in/jeffin-sam-joji}{LinkedIn} \quad$|$\quad
  \href{https://github.com/jeff13in}{GitHub} \quad$|$\quad
  \href{https://jeff13in.github.io/Portfolio}{Portfolio}
\end{center}"""


def build_summary(category: str) -> str:
    text = SUMMARIES.get(category, SUMMARIES["software_engineering"])
    return f"\n\\section{{Summary}}\n{text}"


def build_experience(category: str) -> str:
    lines = ["\n\\section{Experience}"]
    for exp in EXPERIENCE:
        bullets = exp["bullets"].get(category) or exp["bullets"].get("all", [])
        lines.append(
            f"\n\\noindent\\textbf{{{tex_escape(exp['title'])}}} \\hfill \\textit{{{exp['dates']}}} \\\\\n"
            f"\\textit{{{tex_escape(exp['company'])}, {tex_escape(exp['location'])}}}"
        )
        lines.append("\\begin{itemize}")
        for b in bullets:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_projects(category: str) -> str:
    projects = PROJECTS.get(category, PROJECTS["software_engineering"])
    lines = ["\n\\section{Projects}"]
    for p in projects:
        subtitle = f" \\textit{{\\small --- {p['subtitle']}}}" if p.get("subtitle") else ""
        lines.append(
            f"\n\\noindent\\textbf{{{tex_escape(p['name'])}}}{subtitle} \\hfill \\textit{{{p['date']}}} \\\\\n"
            f"\\href{{{p['url']}}}{{\\small {p['url_display']}}}"
        )
        lines.append("\\begin{itemize}")
        for b in p["bullets"]:
            lines.append(f"  \\item {b}")
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_skills(category: str) -> str:
    skill_set = SKILLS.get(category, SKILLS["software_engineering"])
    lines = ["\n\\section{Technical Skills}"]
    lines.append("\\begin{itemize}[label={}, leftmargin=0pt, itemsep=2pt, topsep=2pt]")
    for label, items in skill_set:
        lines.append(f"  \\item \\textbf{{{label}:}} {items}")
    lines.append("\\end{itemize}")
    return "\n".join(lines)


def build_education() -> str:
    return r"""
\section{Education}

\noindent\textbf{Bachelor of Science (Honours) --- Computer Science} \hfill \textit{Sept 2021 -- Apr 2026} \\
\textit{Brock University, St.\ Catharines, ON} \\
\small Concentration in Software Engineering"""


def build_certifications() -> str:
    lines = ["\n\\section{Certifications}"]
    lines.append("\\begin{itemize}[itemsep=1pt, topsep=3pt]")
    for cert in CERTIFICATIONS:
        lines.append(f"  \\item {cert}")
    lines.append("\\end{itemize}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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

    print(f"Generating LaTeX resume for: {job['title']} at {job['company']} [{category}]")

    doc = "\n".join([
        PREAMBLE,
        build_header(),
        build_summary(category),
        build_experience(category),
        build_projects(category),
        build_skills(category),
        build_education(),
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
