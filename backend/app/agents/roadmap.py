"""Learning roadmap generator: turns gaps from every agent into a week-by-week plan."""


def generate_roadmap(gap: dict, coding: dict | None, resume_score: dict | None, interview: dict | None, projects_count: int, hours_per_week: int = 10, max_weeks: int = 12) -> list[dict]:
    items: list[dict] = []
    for g in gap["gaps"]:
        items.append({"task": f"{'Learn' if g['type']=='missing' else 'Strengthen'} {g['label']}: {g['how']}", "priority": g["priority"], "phase": "Skill gap", "hours": g["estimated_hours"]})
    if not (coding and coding.get("assessed")) or coding["score"] < 65:
        items.append({"task": "Solve 5 DSA problems per week (mix of easy/medium), review solutions and revisit mistakes", "priority": "High", "phase": "Coding", "hours": 24})
    if coding and coding.get("assessed"):
        for r in coding["recommendations"][:2]: items.append({"task": r, "priority": "Medium", "phase": "Coding", "hours": 8})
    if resume_score is None:
        items.append({"task": "Upload your resume to the Resume Agent and fix the top suggestions", "priority": "High", "phase": "Resume", "hours": 3})
    elif resume_score["ats_score"] < 75:
        for s in resume_score["suggestions"][:3]: items.append({"task": f"Resume: {s}", "priority": "Medium", "phase": "Resume", "hours": 2})
    if projects_count < 2:
        items.append({"task": f"Build and deploy a portfolio project for {gap['target_role']} (README, tests, live demo)", "priority": "High", "phase": "Projects", "hours": 30})
    if interview is None or interview.get("overall_score", 0) < 70:
        items.append({"task": "Complete a mock interview each week and work on the improvement points", "priority": "Medium", "phase": "Interview", "hours": 12})
    order = {"High": 0, "Medium": 1, "Low": 2}
    items.sort(key=lambda x: (order[x["priority"]], x["hours"]))
    tasks, cum = [], 0
    for it in items:
        hrs = max(1, it["hours"])
        week = int(cum // max(1, hours_per_week)) + 1  # week in which the task starts
        if week > max_weeks: break
        tasks.append({"task": it["task"][:250], "priority": it["priority"], "category": f"Week {week} · {it['phase']}", "estimated_hours": hrs})
        cum += hrs
    return tasks
