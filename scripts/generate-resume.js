#!/usr/bin/env node
/**
 * Resume generator for job applications
 * Generates role-specific resumes using the docx library
 */

const fs = require('fs');
const path = require('path');

// Resume data structure based on Jeffin's profile
const PROFILE = {
  name: "Jeffin Sam Joji",
  location: "Niagara Falls, ON",
  phone: "(289) 501-1917",
  email: "ejffinsam14@gmail.com",
  linkedin: "linkedin.com/in/jeffin-sam-joji",
  github: "github.com/jeff13in",
  portfolio: "jeff13in.github.io/Portfolio",
  
  education: {
    degree: "Bachelor of Science (Honours) — Computer Science",
    concentration: "Concentration in Software Engineering",
    school: "Brock University",
    location: "St. Catharines, ON",
    dates: "Sept 2021 - Apr 2026"
  },
  
  experience: [
    {
      title: "Software Engineer Intern",
      company: "Karmeka",
      location: "Toronto, ON",
      dates: "Aug 2025 - Present",
      bullets_cybersecurity: [
        "Developed and maintained RESTful APIs integrating external data sources and AI services, applying secure coding practices and validating data flows across enterprise platforms.",
        "Established CI/CD pipelines with GitHub Actions to automate build, test, and deployment workflows, cutting release cycle time by 40% and ensuring consistent cross-environment deployments.",
        "Built automated document parsing pipelines using OCR and Python scripting, reducing manual processing by 60% — directly analogous to automating routine security operations tasks.",
        "Translated business requirements into AI-powered automation solutions, bridging stakeholder needs with technical execution in fast-moving agile sprints."
      ],
      bullets_swe: [
        "Designed and maintained RESTful APIs integrating external data sources and AI services, optimizing data flow and enabling real-time information delivery across enterprise platforms.",
        "Established CI/CD pipelines using GitHub Actions, automating build, test, and deployment workflows — reducing release cycle time by 40% while ensuring consistent cross-environment deployments.",
        "Translated business process requirements into AI-powered automation solutions using OpenAI platform, bridging stakeholder needs and technical execution in an iterative product development cycle.",
        "Developed cross-platform mobile and full-stack web solutions (React Native, React, Python/Flask), demonstrating adaptability across technology stacks in fast-moving agile sprints."
      ],
      bullets_data: [
        "Designed and maintained RESTful APIs integrating external data sources and AI services, optimizing data flow and enabling real-time information delivery across enterprise platforms.",
        "Established CI/CD pipelines using GitHub Actions, automating build, test, and deployment workflows — reducing release cycle time by 40% while ensuring consistent cross-environment deployments.",
        "Applied OCR and automated document parsing pipelines to streamline business workflows, reducing manual data entry by 60% through process improvement and intelligent automation.",
        "Developed cross-platform mobile and full-stack web solutions (React Native, React, Python/Flask), demonstrating adaptability across technology stacks in fast-moving agile sprints."
      ]
    },
    {
      title: "Software Developer/AI Engineer",
      company: "Venture for Canada",
      location: "Remote",
      dates: "Oct 2025 - Nov 2025",
      bullets_all: [
        "Engineered content aggregation and curation pipelines using Python-based NLP/ML models to process and filter data from 50+ online sources daily, improving signal-to-noise ratio by 60%.",
        "Built scalable backend services with Docker containerization achieving 99.5% uptime; tracked and resolved recurring system issues by identifying root causes rather than patching symptoms.",
        "Documented system architecture, technical decisions, and workflows to support maintainability — reducing new developer onboarding time by 40%."
      ]
    },
    {
      title: "Supervisor",
      company: "Digital Attractions",
      location: "Niagara Falls, ON",
      dates: "Mar 2025 - Present",
      bullets_all: [
        "Led onboarding and training for new team members, improving operational efficiency by 35% through structured documentation.",
        "Implemented systematic troubleshooting processes to resolve technical issues, reducing customer wait times by 25%."
      ]
    }
  ],
  
  projects: {
    cybersecurity: [
      {
        name: "AI Threat Detection System",
        url: "github.com/jeff13in/AI-threat_Detection",
        date: "Dec 2025",
        bullets: [
          "Built ML-powered anomaly detection system using Isolation Forest and DBSCAN clustering to identify suspicious behavioral patterns in log and event data — aligned with SOC threat monitoring workflows.",
          "Integrated multiple threat intelligence APIs (VirusTotal, AbuseIPDB, OTX AlienVault, CVE CIRCL) to build a comprehensive multi-source data aggregation and analysis pipeline.",
          "Deployed pipeline with Kafka event streaming and Elasticsearch for scalable log ingestion and indexed alerting, mirroring enterprise SIEM architectures."
        ]
      },
      {
        name: "SecureShop Risk Assessment",
        url: "github.com/jeff13in/SecureShop-Risk-Assessment",
        subtitle: "GRC, NIST CSF, PCI-DSS, GDPR, OWASP",
        date: "Feb 2025",
        bullets: [
          "Conducted a comprehensive security assessment of a simulated e-commerce environment, applying NIST CSF, PCI-DSS, GDPR, and OWASP frameworks to identify 18 control gaps.",
          "Quantified risk exposure through loss expectancy calculations and delivered a prioritized remediation roadmap with cost-justified controls — demonstrating security documentation and reporting skills."
        ]
      }
    ],
    data_ml: [
      {
        name: "VibeMap",
        url: "github.com/jeff13in/VibeMap",
        live_url: "vibemap.vercel.app",
        date: "Jan - Feb 2026",
        bullets: [
          "Built and deployed full-stack application with 8-endpoint REST API; delivered 125 unit tests at 88% code coverage across data cleaning, recommender, and clustering modules.",
          "Designed end-to-end data pipeline (CSV ingestion → SQL cleaning → K-Means/KNN model training) and deployed to production on Vercel/Render with serialized ML models.",
          "Created interactive Power BI and Tableau dashboards to visualize recommendation patterns and clustering results."
        ]
      }
    ],
    swe: [
      {
        name: "Instagram Engagement Automation Platform",
        url: "github.com/jeff13in/Instagram-Comment-to-Get-Automation",
        date: "Sept - Dec 2025",
        bullets: [
          "Implemented OAuth 2.0 authentication and SQLAlchemy-backed webhook processing achieving 98.7% automated response success rate; established CI/CD via GitHub Actions for zero-downtime deployments."
        ]
      }
    ]
  }
};

/**
 * Select skills based on role category
 */
function getSkillsForRole(category) {
  const skillSets = {
    cybersecurity: [
      {
        label: "Security Operations & Tools",
        items: "Splunk SIEM, Burp Suite, Nmap, Metasploit, Wireshark, EDR concepts, Kali Linux, IDS/IPS familiarity"
      },
      {
        label: "Scripting & Automation",
        items: "Python (automation, ML, API integration), Bash, PowerShell (basic), GitHub Actions CI/CD"
      },
      {
        label: "Cloud & OS Platforms",
        items: "AWS Cloud Practitioner, Docker, Linux (Kali/Ubuntu), Windows, Azure (familiarity)"
      },
      {
        label: "Security Frameworks",
        items: "NIST CSF, PCI-DSS, GDPR, OWASP (applied in GRC project), Identity & Access Management concepts"
      },
      {
        label: "Development",
        items: "Flask REST APIs, React/TypeScript, SQLite/PostgreSQL, OAuth 2.0, RESTful APIs, n8n/Make automation"
      }
    ],
    software_engineering: [
      {
        label: "Languages & Frameworks",
        items: "Python, JavaScript/TypeScript, Java, C++, React, Node.js, Flask, Django"
      },
      {
        label: "Cloud & DevOps",
        items: "AWS, Docker, CI/CD (GitHub Actions), Git/GitHub, Vercel/Render deployment"
      },
      {
        label: "Data & APIs",
        items: "PostgreSQL, SQLite, RESTful APIs, OAuth 2.0, Webhooks, API Integration"
      },
      {
        label: "Development Tools",
        items: "Linux (Ubuntu), Windows, Bash scripting, n8n/Make automation"
      }
    ],
    data_ml: [
      {
        label: "Data & Analytics",
        items: "SQL (PostgreSQL, SQLite), Python (pandas, NumPy, scikit-learn), ETL Pipelines, K-Means, KNN, Data Visualization (Power BI, Tableau)"
      },
      {
        label: "ML & AI",
        items: "TensorFlow, PyTorch, Isolation Forest, DBSCAN, NLP, Model deployment"
      },
      {
        label: "Cloud & DevOps",
        items: "AWS, Docker, CI/CD (GitHub Actions), Git/GitHub"
      },
      {
        label: "Development",
        items: "Python, JavaScript, Flask, React/TypeScript, RESTful APIs"
      }
    ]
  };
  
  return skillSets[category] || skillSets.software_engineering;
}

/**
 * Select projects based on role category
 */
function getProjectsForRole(category) {
  const projectMap = {
    cybersecurity: [...PROFILE.projects.cybersecurity],
    software_engineering: [...PROFILE.projects.swe, PROFILE.projects.data_ml[0]],
    data_ml: [...PROFILE.projects.data_ml]
  };
  
  return projectMap[category] || projectMap.software_engineering;
}

/**
 * Generate summary based on role category
 */
function getSummaryForRole(category, jobTitle = "") {
  const summaries = {
    cybersecurity: "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on experience in security operations, threat detection, and scripting. Practical background using Splunk SIEM for log analysis and IOC identification, CTF participation, and building ML-based anomaly detection systems. Familiar with NIST frameworks, vulnerability assessment, and automation using Python and Bash.",
    
    software_engineering: "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on experience building integrations, APIs, and full-stack applications. Proven track record designing data exchange systems, implementing CI/CD pipelines, and working in agile environments to deliver high-quality solutions at scale.",
    
    data_ml: "Fourth-year Computer Science (Honours) student graduating April 2026, with hands-on experience in data engineering, ML model deployment, and analytics. Built end-to-end data pipelines, deployed production ML systems, and created interactive dashboards using Power BI and Tableau. Proficient in Python, SQL, and cloud deployment."
  };
  
  return summaries[category] || summaries.software_engineering;
}

/**
 * Main resume generation function
 */
function generateResume(jobData) {
  console.log(`\n=== Generating Resume ===`);
  console.log(`Job: ${jobData.title} at ${jobData.company}`);
  console.log(`Categories: ${jobData.categories.join(', ')}`);
  
  // Determine primary category
  const primaryCategory = jobData.categories[0] || 'software_engineering';
  
  // Build resume structure
  const resume = {
    profile: PROFILE,
    summary: getSummaryForRole(primaryCategory, jobData.title),
    skills: getSkillsForRole(primaryCategory),
    projects: getProjectsForRole(primaryCategory),
    category: primaryCategory
  };
  
  const outputPath = path.join(__dirname, '..', 'applications', 'pending', `${jobData.id}-resume.json`);
  fs.writeFileSync(outputPath, JSON.stringify(resume, null, 2));
  
  console.log(`✓ Resume generated: ${outputPath}`);
  
  return resume;
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('Usage: node generate-resume.js <job_id>');
    process.exit(1);
  }
  
  const jobId = args[0];
  
  // Load jobs data
  const jobsPath = path.join(__dirname, '..', 'data', 'jobs.json');
  const jobsData = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
  
  // Find job by ID
  const job = jobsData.jobs.find(j => j.id === jobId);
  
  if (!job) {
    console.error(`Job not found: ${jobId}`);
    process.exit(1);
  }
  
  generateResume(job);
}

module.exports = { generateResume, PROFILE };
