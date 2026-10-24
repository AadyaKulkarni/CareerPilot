"""HTTP endpoints for the five AI agents + readiness score + roadmap."""
import copy
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agents import coding_agent, interview_agent, job_agent, resume_agent, roadmap as roadmap_agent
from app.agents.catalog import ROLES, resolve_role
from app.agents.readiness import compute_readiness
from app.agents.skill_gap_agent import candidate_skills, skill_gap_report
from app.core.deps import current_user
from app.db.session import get_db
from app.models import (CodingStat, InterviewSession, LearningTask, LLMSetting, Profile, ReadinessSnapshot, ResumeAnalysis)
from app.schemas.schemas import (CodingManualIn, CodingSyncIn, InterviewAnswerIn, InterviewStartIn, JobMatchIn, RoadmapIn, TextAnalyzeIn)
from app.services.llm import chat
from app.ml.recommender import readiness as profile_completion

router = APIRouter()


# ------------------------------------------------------------------ helpers
def _profile(u, db: Session) -> Profile:
    p = u.profile
    if not p:
        p = Profile(user_id=u.id); db.add(p); db.commit(); db.refresh(p)
    return p


def _pdict(p: Profile) -> dict:
    return {"career_goal": p.career_goal, "degree": p.degree, "branch": p.branch, "college": p.college, "cgpa": p.cgpa,
            "graduation_year": p.graduation_year, "skills": p.skills or [], "experiences": p.experiences or [], "projects": p.projects or [],
            "certifications": p.certifications or [], "achievements": p.achievements or [], "interests": p.interests or []}


def _latest_resume(u, db) -> ResumeAnalysis | None:
    return db.scalar(select(ResumeAnalysis).where(ResumeAnalysis.user_id == u.id).order_by(ResumeAnalysis.id.desc()))


def _coding(u, db) -> dict:
    rows = db.scalars(select(CodingStat).where(CodingStat.user_id == u.id)).all()
    return coding_agent.analyze_coding([r.data for r in rows])


def _interview_avg(u, db) -> tuple[float | None, dict | None]:
    rows = db.scalars(select(InterviewSession).where(InterviewSession.user_id == u.id, InterviewSession.status == "finished").order_by(InterviewSession.id.desc()).limit(3)).all()
    if not rows: return None, None
    return round(sum(r.overall_score for r in rows) / len(rows)), rows[0].summary


def _gather(u, db, target_role: str | None = None) -> dict:
    p = _profile(u, db); pd = _pdict(p); rs = _latest_resume(u, db); cod = _coding(u, db)
    have = candidate_skills(pd, rs.parsed if rs else None, cod if cod.get("assessed") else None)
    gap = skill_gap_report(pd, rs.parsed if rs else None, cod if cod.get("assessed") else None, target_role)
    avg, isum = _interview_avg(u, db)
    return {"p": p, "pd": pd, "resume": rs, "coding": cod, "have": have, "gap": gap, "interview_avg": avg, "interview_summary": isum}


def _llm(u, db) -> LLMSetting | None:
    s = db.scalar(select(LLMSetting).where(LLMSetting.user_id == u.id))
    return s if s and s.provider != "none" and s.encrypted_api_key else None


def _resume_out(r: ResumeAnalysis) -> dict:
    return {"id": r.id, "filename": r.filename, "target_role": r.target_role, "ats_score": r.ats_score, "breakdown": r.breakdown,
            "suggestions": r.suggestions, "parsed": r.parsed, "created_at": r.created_at.isoformat()}


# ------------------------------------------------------------- Resume Agent
def _store_resume(u, db, filename, text, parsed, scored, apply_to_profile: bool) -> dict:
    r = ResumeAnalysis(user_id=u.id, filename=filename, target_role=scored["target_role"], text=text[:20000], parsed=parsed,
                       ats_score=scored["ats_score"], breakdown=scored["breakdown"], suggestions=scored["suggestions"])
    db.add(r); added = []
    if apply_to_profile:
        p = _profile(u, db); upd = resume_agent.merge_into_profile(_pdict(p), parsed)
        for k, v in upd.items(): setattr(p, k, v)
        added = list(upd)
    db.commit(); db.refresh(r)
    return {**_resume_out(r), "profile_fields_added": added}


@router.post("/resume/parse")
async def resume_parse(file: UploadFile = File(...), target_role: str = Form(""), apply_to_profile: bool = Form(False),
                       u=Depends(current_user), db: Session = Depends(get_db)):
    data = await file.read(resume_agent.MAX_BYTES + 1)
    try:
        text = resume_agent.extract_text(file.filename or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    parsed = resume_agent.parse_resume(text)
    scored = resume_agent.score_resume(parsed, text, target_role or _profile(u, db).career_goal)
    return _store_resume(u, db, file.filename or "", text, parsed, scored, apply_to_profile)


@router.post("/resume/analyze-text")
def resume_analyze_text(x: TextAnalyzeIn, u=Depends(current_user), db: Session = Depends(get_db)):
    parsed = resume_agent.parse_resume(x.text)
    scored = resume_agent.score_resume(parsed, x.text, x.target_role or _profile(u, db).career_goal)
    return _store_resume(u, db, "pasted text", x.text, parsed, scored, False)


@router.get("/resume/latest")
def resume_latest(u=Depends(current_user), db: Session = Depends(get_db)):
    r = _latest_resume(u, db)
    return _resume_out(r) if r else None


# --------------------------------------------------------- Skill Gap Agent
@router.get("/skills/gap")
def skills_gap(target_role: str = "", u=Depends(current_user), db: Session = Depends(get_db)):
    return _gather(u, db, target_role or None)["gap"]


@router.get("/roles")
def roles(): return list(ROLES)


# ------------------------------------------------------ Coding Analytics Agent
def _upsert_stat(db, uid, platform, handle, data):
    row = db.scalar(select(CodingStat).where(CodingStat.user_id == uid, CodingStat.platform == platform))
    if not row: row = CodingStat(user_id=uid, platform=platform); db.add(row)
    row.handle = handle; row.data = data; row.fetched_at = datetime.utcnow()


@router.post("/coding/sync")
async def coding_sync(x: CodingSyncIn, u=Depends(current_user), db: Session = Depends(get_db)):
    errors, synced = {}, []
    for platform, raw in (("leetcode", x.leetcode), ("codeforces", x.codeforces), ("github", x.github)):
        if not raw.strip(): continue
        try:
            handle = coding_agent.clean_handle(platform, raw)
            data = await coding_agent.FETCHERS[platform](handle)
            _upsert_stat(db, u.id, platform, handle, data); synced.append(platform)
        except coding_agent.CodingFetchError as e:
            errors[platform] = str(e)
    db.commit()
    return {"synced": synced, "errors": errors, "analytics": _coding(u, db)}


@router.post("/coding/manual")
def coding_manual(x: CodingManualIn, u=Depends(current_user), db: Session = Depends(get_db)):
    data = coding_agent.normalize("manual", "manual", x.easy, x.medium, x.hard, x.rating, x.contests)
    _upsert_stat(db, u.id, "manual", "manual", data); db.commit()
    return _coding(u, db)


@router.get("/coding/analytics")
def coding_analytics(u=Depends(current_user), db: Session = Depends(get_db)):
    return _coding(u, db)


@router.delete("/coding/{platform}")
def coding_delete(platform: str, u=Depends(current_user), db: Session = Depends(get_db)):
    if platform not in coding_agent.PLATFORMS: raise HTTPException(404, "Unknown platform")
    db.execute(delete(CodingStat).where(CodingStat.user_id == u.id, CodingStat.platform == platform)); db.commit()
    return _coding(u, db)


# -------------------------------------------------------- Job Matching Agent
@router.get("/companies/matches")
def company_matches(top: int = 12, u=Depends(current_user), db: Session = Depends(get_db)):
    g = _gather(u, db); rs = g["resume"]
    cs = g["coding"]["score"] if g["coding"].get("assessed") else None
    return {"matches": job_agent.match_companies(g["pd"], g["have"], cs, rs.text if rs else "", max(1, min(top, 30))),
            "note": "Company data is an illustrative seed (backend/app/data/companies.json). Verify criteria with your placement cell."}


@router.post("/job/match")
def job_match(x: JobMatchIn, u=Depends(current_user), db: Session = Depends(get_db)):
    g = _gather(u, db); rs = g["resume"]
    return job_agent.match_job_description(x.job_description, g["have"], rs.text if rs else "")


# ----------------------------------------------------------- Interview Agent
def _public_q(q: dict) -> dict:
    out = {k: q.get(k) for k in ("id", "category", "topic", "question", "answer", "evaluation")}
    if not q.get("evaluation"): out["evaluation"] = None
    return out


def _session_out(s: InterviewSession) -> dict:
    return {"id": s.id, "role": s.role, "difficulty": s.difficulty, "mode": s.mode, "status": s.status, "overall_score": s.overall_score,
            "summary": s.summary, "questions": [_public_q(q) for q in s.questions], "created_at": s.created_at.isoformat()}


def _own_session(sid: int, u, db) -> InterviewSession:
    s = db.scalar(select(InterviewSession).where(InterviewSession.id == sid, InterviewSession.user_id == u.id))
    if not s: raise HTTPException(404, "Interview session not found")
    return s


@router.post("/interview/start")
async def interview_start(x: InterviewStartIn, u=Depends(current_user), db: Session = Depends(get_db)):
    g = _gather(u, db); role = resolve_role(x.role or g["pd"]["career_goal"]); mode, notice, questions = "heuristic", None, None
    llm = _llm(u, db) if x.use_llm else None
    if llm:
        try:
            raw = await chat(llm.provider, llm.model, llm.encrypted_api_key, interview_agent.SYSTEM,
                             interview_agent.generation_prompt(g["pd"], role, x.num_questions, x.difficulty), 0.6, True)
            questions = interview_agent.llm_questions(raw)[:x.num_questions]; mode = "llm"
        except Exception as e:
            notice = f"LLM unavailable ({str(e)[:80]}); using the built-in question bank."
    if not questions:
        questions = interview_agent.build_plan(g["pd"], g["have"], role, x.num_questions)
    s = InterviewSession(user_id=u.id, role=role, difficulty=x.difficulty, mode=mode, questions=questions)
    db.add(s); db.commit(); db.refresh(s)
    return {**_session_out(s), "notice": notice}


@router.post("/interview/{sid}/answer")
async def interview_answer(sid: int, x: InterviewAnswerIn, u=Depends(current_user), db: Session = Depends(get_db)):
    s = _own_session(sid, u, db)
    if s.status != "in_progress": raise HTTPException(400, "This interview is already finished")
    if x.question_index >= len(s.questions): raise HTTPException(400, "Invalid question")
    qs = copy.deepcopy(s.questions); q = qs[x.question_index]
    if q.get("evaluation"): raise HTTPException(400, "This question is already answered")
    ev, notice = None, None
    if s.mode == "llm":
        llm = _llm(u, db)
        if llm:
            try:
                ev = interview_agent.llm_evaluation(await chat(llm.provider, llm.model, llm.encrypted_api_key, interview_agent.SYSTEM,
                                                               interview_agent.evaluation_prompt(q, x.answer, s.role), 0.2, True))
            except Exception as e:
                notice = f"LLM evaluation failed ({str(e)[:80]}); used keyword-based scoring."
    if ev is None:
        ev = interview_agent.evaluate_heuristic(q, x.answer)
    q["answer"] = x.answer; q["evaluation"] = ev
    s.questions = qs; flag_modified(s, "questions"); db.commit()
    return {"question_index": x.question_index, "evaluation": ev, "notice": notice}


@router.post("/interview/{sid}/finish")
def interview_finish(sid: int, u=Depends(current_user), db: Session = Depends(get_db)):
    s = _own_session(sid, u, db)
    if not any(q.get("evaluation") for q in s.questions): raise HTTPException(400, "Answer at least one question first")
    s.summary = interview_agent.summarize(s.questions); s.overall_score = s.summary["overall_score"]; s.status = "finished"
    db.commit(); return _session_out(s)


@router.get("/interview/sessions")
def interview_sessions(u=Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InterviewSession).where(InterviewSession.user_id == u.id).order_by(InterviewSession.id.desc()).limit(20)).all()
    return [{"id": r.id, "role": r.role, "status": r.status, "mode": r.mode, "overall_score": r.overall_score, "created_at": r.created_at.isoformat(),
             "answered": sum(1 for q in r.questions if q.get("evaluation")), "total": len(r.questions)} for r in rows]


@router.get("/interview/{sid}")
def interview_get(sid: int, u=Depends(current_user), db: Session = Depends(get_db)):
    return _session_out(_own_session(sid, u, db))


# ------------------------------------------------ Readiness score + roadmap
@router.get("/readiness")
def readiness(u=Depends(current_user), db: Session = Depends(get_db)):
    g = _gather(u, db); rs = g["resume"]; _, completion = profile_completion(g["p"])
    out = compute_readiness(g["pd"], completion, g["gap"], rs.ats_score if rs else None, g["coding"], g["interview_avg"])
    last = db.scalar(select(ReadinessSnapshot).where(ReadinessSnapshot.user_id == u.id).order_by(ReadinessSnapshot.id.desc()))
    if not last or last.score != out["score"] or last.created_at < datetime.utcnow() - timedelta(hours=12):
        db.add(ReadinessSnapshot(user_id=u.id, score=out["score"], components=out["components"])); db.commit()
    hist = db.scalars(select(ReadinessSnapshot).where(ReadinessSnapshot.user_id == u.id).order_by(ReadinessSnapshot.id.desc()).limit(12)).all()
    out["history"] = [{"score": h.score, "at": h.created_at.isoformat()} for h in reversed(hist)]
    out["target_role"] = g["gap"]["target_role"]
    return out


@router.post("/roadmap/generate")
def roadmap_generate(x: RoadmapIn, u=Depends(current_user), db: Session = Depends(get_db)):
    g = _gather(u, db, x.target_role or None); rs = g["resume"]
    resume_score = {"ats_score": rs.ats_score, "suggestions": rs.suggestions} if rs else None
    tasks = roadmap_agent.generate_roadmap(g["gap"], g["coding"], resume_score, g["interview_summary"], len(g["pd"]["projects"]), x.hours_per_week)
    done = {t.task for t in db.scalars(select(LearningTask).where(LearningTask.user_id == u.id, LearningTask.completed == True)).all()}  # noqa: E712
    db.execute(delete(LearningTask).where(LearningTask.user_id == u.id))
    for t in tasks: db.add(LearningTask(user_id=u.id, completed=t["task"] in done, **t))
    db.commit()
    return {"target_role": g["gap"]["target_role"], "count": len(tasks), "total_hours": sum(t["estimated_hours"] for t in tasks)}
