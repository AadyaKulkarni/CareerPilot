"""Career-fit engine: skill coverage (catalog roles) blended with TF-IDF profile similarity."""
from app.agents.catalog import ROLES, label
from app.agents.similarity import scaled, similarities
from app.agents.skill_gap_agent import candidate_skills, role_gap


def _profile_dict(p) -> dict:
    return {k: getattr(p, k, None) or ([] if k not in ("career_goal", "cgpa") else getattr(p, k, None))
            for k in ("skills", "projects", "experiences", "certifications", "interests", "career_goal", "cgpa")}


def analyze(p):
    pd = _profile_dict(p); have = candidate_skills(pd)
    docs = [" ".join(s.replace("|", " ") for s in v["core"] + v["nice"]) + " " + r for r, v in ROLES.items()]
    query = " ".join(list(have) + [str(i) for i in pd["interests"]] + [pd["career_goal"] or ""])
    sims = similarities(query, docs)
    results = []
    for (role, _), sim in zip(ROLES.items(), sims):
        g = role_gap(have, role)
        core = [r for r in g["rows"] if r["tier"] == "core"]
        matched = [r["label"] for r in g["rows"] if r["proficiency"] >= 0.5]
        missing = [r["label"] for r in core if r["proficiency"] < 0.5]
        score = min(99, round(0.7 * g["coverage"] + 0.3 * scaled(sim) * 100))
        results.append({"career": role, "match_score": score, "matched": matched, "missing": missing,
                        "reasoning": f"You cover {g['coverage']}% of the skills for this role; {len(missing)} core skill(s) still missing."})
    return sorted(results, key=lambda r: -r["match_score"])


def readiness(p):
    fields = [bool(p.degree), bool(p.branch), bool(p.career_goal), bool(p.skills), bool(p.projects), bool(p.experiences), bool(p.certifications), bool(p.achievements)]
    profile = round(sum(fields) / len(fields) * 100)
    skills = min(25, len(p.skills) * 4); projects = min(20, len(p.projects) * 10); exp = min(15, len(p.experiences) * 8)
    academics = 15 if p.cgpa else 7; cert = min(10, len(p.certifications) * 5); achievements = min(5, len(p.achievements) * 2)
    return min(100, skills + projects + exp + academics + cert + achievements), profile
