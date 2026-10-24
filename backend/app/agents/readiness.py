"""Placement readiness score: a transparent weighted blend of every agent's output."""

WEIGHTS = {"profile": 8, "academics": 10, "skills": 24, "portfolio": 10, "resume": 13, "coding": 20, "interview": 15}


def _band(score: int) -> str:
    return "Placement ready" if score >= 80 else "Almost there" if score >= 65 else "Building momentum" if score >= 45 else "Getting started"


def compute_readiness(profile: dict, completion: int, gap: dict | None, resume_ats: float | None, coding: dict | None, interview_avg: float | None) -> dict:
    comps = []

    def add(key, label, score, assessed, detail, action):
        comps.append({"key": key, "label": label, "weight": WEIGHTS[key], "score": round(score) if assessed else 0, "assessed": assessed,
                      "contribution": round(WEIGHTS[key] * score / 100, 1) if assessed else 0.0, "detail": detail, "action": action})

    add("profile", "Profile completeness", completion, True, f"{completion}% of profile fields filled", "Complete missing profile sections." if completion < 100 else "")
    cg = profile.get("cgpa")
    add("academics", "Academics (CGPA)", max(0, min(100, (cg - 5) / 4 * 100)) if cg else 0, bool(cg),
        f"CGPA {cg}" if cg else "CGPA not provided", "" if cg else "Add your CGPA to your profile.")
    add("skills", f"Skill match ({gap['target_role']})" if gap else "Skill match", gap["coverage"] if gap else 0, bool(gap and gap["candidate_skill_count"]),
        f"{gap['coverage']}% of role skills covered" if gap and gap["candidate_skill_count"] else "No skills recorded",
        (gap["gaps"][0]["how"] if gap and gap["gaps"] else "Add your skills to your profile."))
    pr, ex, ce = len(profile.get("projects") or []), len(profile.get("experiences") or []), len(profile.get("certifications") or [])
    port = min(100, pr * 30 + ex * 30 + ce * 10)
    add("portfolio", "Projects & experience", port, bool(pr or ex or ce), f"{pr} projects, {ex} internships/experiences, {ce} certifications",
        "Build one solid project and add it to your profile." if pr < 2 else "")
    add("resume", "Resume quality (ATS)", resume_ats or 0, resume_ats is not None, f"ATS score {round(resume_ats)}/100" if resume_ats is not None else "No resume analysed yet",
        "Upload your resume to the Resume Agent." if resume_ats is None else ("Apply the Resume Agent's suggestions." if resume_ats < 75 else ""))
    cs = coding["score"] if coding and coding.get("assessed") else 0
    add("coding", "Coding practice", cs, bool(coding and coding.get("assessed")), f"{coding['total_solved']} problems solved, level {coding['level']}" if coding and coding.get("assessed") else "No coding profile linked",
        (coding["recommendations"][0] if coding and coding.get("recommendations") else "Link your coding profiles."))
    add("interview", "Mock interview", interview_avg or 0, interview_avg is not None, f"Average mock interview score {round(interview_avg)}/100" if interview_avg is not None else "No mock interview completed",
        "Take a mock interview with the Interview Agent." if interview_avg is None else ("Practise weak categories and retake." if interview_avg < 70 else ""))
    score = round(sum(c["contribution"] for c in comps))
    conf = sum(c["weight"] for c in comps if c["assessed"])
    todo = sorted((c for c in comps if c["action"]), key=lambda c: -(c["weight"] * (100 - c["score"])))
    return {"score": score, "band": _band(score), "confidence": conf, "components": comps,
            "next_actions": [{"area": c["label"], "action": c["action"]} for c in todo[:4]],
            "note": "Unassessed areas count as zero. Use the agents to assess them." if conf < 100 else None}
