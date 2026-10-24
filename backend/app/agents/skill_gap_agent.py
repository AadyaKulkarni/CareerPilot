"""Skill Gap Agent: compares what the candidate has evidence for with what a role needs."""
from .catalog import (DEFAULT_LEVEL_WEIGHT, MENTIONED_WEIGHT, ROLES, extract_skills, label, learn_hint,
                      normalize_skill, resolve_role)

LEVEL_NAME = [(0.95, "Advanced"), (0.75, "Intermediate"), (0.0, "Beginner")]


def candidate_skills(profile: dict, resume_parsed: dict | None = None, coding: dict | None = None) -> dict[str, dict]:
    """canonical skill -> {"proficiency": 0..1, "sources": [...]}; takes the best evidence per skill."""
    out: dict[str, dict] = {}

    def put(skill, prof, src):
        if not skill: return
        cur = out.setdefault(skill, {"proficiency": 0.0, "sources": []})
        cur["proficiency"] = max(cur["proficiency"], prof)
        if src not in cur["sources"]: cur["sources"].append(src)

    for s in profile.get("skills") or []:
        name = s.get("name", "") if isinstance(s, dict) else str(s)
        lvl = (s.get("level", "Intermediate") if isinstance(s, dict) else "Intermediate").lower()
        put(normalize_skill(name), DEFAULT_LEVEL_WEIGHT.get(lvl, 0.8), "profile")
    if resume_parsed:
        for sk in resume_parsed.get("skills", []): put(sk, MENTIONED_WEIGHT, "resume")
    blob = " ".join(f"{p.get('title','')} {p.get('description','')}" if isinstance(p, dict) else str(p)
                    for p in (profile.get("projects") or []) + (profile.get("experiences") or []))
    for sk in extract_skills(blob): put(sk, 0.7, "projects/experience")  # applied in a project => a bit stronger than "mentioned"
    for c in profile.get("certifications") or []:
        txt = c.get("name", "") if isinstance(c, dict) else str(c)
        for sk in extract_skills(txt): put(sk, 0.7, "certification")
    if coding and coding.get("total_solved"):
        t = coding["total_solved"]
        put("dsa", 1.0 if t >= 300 else 0.8 if t >= 100 else 0.6 if t >= 30 else 0.4, "coding platforms")
    return out


def _satisfaction(item: str, have: dict) -> tuple[float, str | None]:
    best, who = 0.0, None
    for alt in item.split("|"):
        p = have.get(alt, {}).get("proficiency", 0.0)
        if p > best: best, who = p, alt
    return best, who


def role_gap(have: dict, role: str) -> dict:
    spec = ROLES[role]
    rows, wsum, got = [], 0.0, 0.0
    for tier, weight in (("core", 2), ("nice", 1)):
        for item in spec[tier]:
            sat, who = _satisfaction(item, have)
            wsum += weight; got += weight * sat
            rows.append({"skill": item, "label": label(item), "tier": tier, "proficiency": round(sat, 2), "matched_with": who,
                         "level": next(n for t, n in LEVEL_NAME if sat >= t) if sat else None,
                         "sources": have.get(who, {}).get("sources", []) if who else []})
    return {"role": role, "coverage": round(100 * got / wsum) if wsum else 0, "rows": rows}


def skill_gap_report(profile: dict, resume_parsed: dict | None = None, coding: dict | None = None, target_role: str | None = None) -> dict:
    role = resolve_role(target_role or profile.get("career_goal") or "")
    have = candidate_skills(profile, resume_parsed, coding)
    main = role_gap(have, role)
    gaps = []
    for r in main["rows"]:
        hours, how = learn_hint(r["skill"])
        if r["proficiency"] == 0:
            gaps.append({"skill": r["skill"], "label": r["label"], "priority": "High" if r["tier"] == "core" else "Low",
                         "type": "missing", "estimated_hours": hours, "how": how})
        elif r["proficiency"] < 0.75 and r["tier"] == "core":
            gaps.append({"skill": r["skill"], "label": r["label"], "priority": "Medium", "type": "strengthen",
                         "estimated_hours": max(4, hours // 2), "how": f"Move from {r['level']} to Intermediate+: {how}"})
    order = {"High": 0, "Medium": 1, "Low": 2}
    gaps.sort(key=lambda g: (order[g["priority"]], -g["estimated_hours"]))
    strengths = [r for r in main["rows"] if r["proficiency"] >= 0.75]
    comparison = sorted(({"role": rn, "coverage": role_gap(have, rn)["coverage"]} for rn in ROLES), key=lambda x: -x["coverage"])
    core_missing = [g for g in gaps if g["priority"] == "High"]
    band = "Strong" if main["coverage"] >= 75 else "Moderate" if main["coverage"] >= 50 else "Needs work"
    summary = (f"You cover {main['coverage']}% of the skills expected for {role}. " +
               (f"{len(core_missing)} core skill(s) are missing: {', '.join(g['label'] for g in core_missing[:4])}." if core_missing
                else "All core skills have at least some evidence; focus on depth and projects.") )
    return {"target_role": role, "coverage": main["coverage"], "band": band, "summary": summary,
            "strengths": [{"label": s["label"], "level": s["level"], "sources": s["sources"]} for s in strengths],
            "gaps": gaps, "skills": main["rows"], "role_comparison": comparison[:8],
            "total_gap_hours": sum(g["estimated_hours"] for g in gaps if g["priority"] != "Low"),
            "candidate_skill_count": len(have)}
