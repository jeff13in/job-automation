---
name: internship-applications
description: Tailor Jeffin's resume and draft application answers for a specific internship posting. Use whenever preparing, reviewing or answering questions for an internship or co-op application.
---

# Internship applications

You are preparing one application for one posting. Inputs: the master resume
(`resumes/master.yaml`), the variant chosen for this role type
(`resumes/variants.yaml`), and the job description.

## The one rule

**Never add anything that is not in the master resume.** No new employers, projects,
tools, numbers, dates, titles or outcomes. You may select, reorder, trim and
reword bullets. If a posting asks for something the master doesn't show, leave the
gap; don't paper over it. `stack/resumes/tailor.py` rejects output that cites a
bullet id that doesn't exist, adds numbers that weren't in the source bullet, or
lists skills not in the master.

## Tailoring a resume

1. Start from the variant: its `tags` decide which bullets lead, and
   `section_order` decides section order.
2. Read the posting and pull out its 5–8 concrete requirements (languages,
   frameworks, domain, responsibilities). Ignore boilerplate.
3. For each experience and project, keep the 1–3 bullets that best match those
   requirements. Drop entries with nothing relevant, unless dropping them leaves a
   visible date gap in experience.
4. Reword only to mirror the posting's vocabulary where it's truthful
   ("built REST endpoints" → "built REST APIs" is fine; "built REST APIs" →
   "designed distributed systems" is not).
5. Order skills so the posting's must-haves come first. Only list skills from the
   master's `skills` block.
6. One page. If it doesn't fit, cut the weakest bullet, not the font size.

## Drafting free-text answers

- 80–150 words unless the form says otherwise. Plain, specific, first person.
- Ground every claim in a master bullet; name the project or employer.
- "Why us": one concrete thing about the company from the posting or its own
  site, linked to one concrete thing Jeffin has done. No flattery.
- No clichés ("passionate", "fast-paced environment", "hit the ground running").

## Questions you must not answer

Return `BLOCKED` with the reason instead of an answer for:
work authorization or visa sponsorship, citizenship, criminal record or
background checks, salary expectations, demographic / EEO / disability /
veteran questions, graduation date or enrollment status, GPA, start-date
commitments, relocation commitments, and anything that asks for a legal
attestation. These go to Jeffin; a wrong answer can sink the application or
be a misrepresentation.
