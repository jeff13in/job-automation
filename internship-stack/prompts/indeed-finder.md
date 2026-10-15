Use this as the prompt for a daily Claude scheduled task (in a session that has the
Indeed connector and this repo available).

---

Search Indeed for internship and co-op postings from the last 3 days in Canada
(Toronto, Waterloo, Ottawa, remote in Canada) for: software engineering, backend,
full-stack, AI/ML, data engineering, security, DevOps.

For each real posting, record company, role title, location and the Indeed job URL
exactly as returned by the connector. Do not invent or rewrite URLs. Skip roles that
need a master's or PhD, and roles that aren't internships or co-ops.

Write the list to `data/indeed.json` as
[{"company": "...", "role": "...", "location": "...", "url": "...", "source": "indeed"}]
then run `python -m stack.finder add --json data/indeed.json` and report how many were added.
