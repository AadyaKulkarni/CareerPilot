"""AI agents for the Placement Readiness & Career Intelligence Portal.

Each agent is a plain-Python module (no web framework imports) so it can be
unit-tested in isolation:

    resume_agent     - parse PDF/DOCX/TXT resumes, extract skills, ATS score
    skill_gap_agent  - compare candidate skills against role requirements
    coding_agent     - LeetCode / Codeforces / GitHub analytics
    job_agent        - company / role matching + job-description matching
    interview_agent  - mock interview question planning and evaluation
    readiness        - composite placement readiness score
    roadmap          - learning roadmap generator
"""
