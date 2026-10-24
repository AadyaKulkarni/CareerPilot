from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.db.session import get_db
from app.models import User, Profile, CareerRecommendation, LearningTask, Resume, LLMSetting
from app.schemas.schemas import *
from app.core.security import hash_password, verify_password, create_token
from app.core.deps import current_user
from app.ml.recommender import analyze, readiness
from app.services.crypto import encrypt
from app.services.llm import enhance

router=APIRouter()

def user_dict(u): return {"id":u.id,"name":u.name,"email":u.email}
@router.post('/auth/register', response_model=TokenOut)
def register(x:RegisterIn, db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==x.email)): raise HTTPException(400,"Email already registered")
    u=User(name=x.name,email=x.email,password_hash=hash_password(x.password)); db.add(u); db.flush(); db.add(Profile(user_id=u.id)); db.commit()
    return {"access_token":create_token(u.id),"user":user_dict(u)}
@router.post('/auth/login', response_model=TokenOut)
def login(x:LoginIn, db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==x.email))
    if not u or not verify_password(x.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return {"access_token":create_token(u.id),"user":user_dict(u)}
@router.get('/me')
def me(u=Depends(current_user)): return user_dict(u)
@router.get('/profile')
def get_profile(u=Depends(current_user),db:Session=Depends(get_db)):
    p=u.profile or Profile(user_id=u.id); db.add(p); db.commit(); db.refresh(p)
    score,completion=readiness(p)
    return {"id":p.id,"career_goal":p.career_goal,"degree":p.degree,"branch":p.branch,"college":p.college,"cgpa":p.cgpa,"graduation_year":p.graduation_year,"skills":p.skills or [],"experiences":p.experiences or [],"projects":p.projects or [],"certifications":p.certifications or [],"achievements":p.achievements or [],"interests":p.interests or [],"readiness":score,"completion":completion}
@router.put('/profile')
def update_profile(x:ProfileIn,u=Depends(current_user),db:Session=Depends(get_db)):
    p=u.profile or Profile(user_id=u.id); db.add(p)
    for k,v in x.model_dump().items(): setattr(p,k,v)
    db.commit(); db.refresh(p); return get_profile(u,db)
@router.post('/career/analyze')
def career_analyze(u=Depends(current_user),db:Session=Depends(get_db)):
    p=u.profile
    if not p: p=Profile(user_id=u.id); db.add(p); db.flush()
    results=analyze(p); db.execute(delete(CareerRecommendation).where(CareerRecommendation.user_id==u.id))
    db.execute(delete(LearningTask).where(LearningTask.user_id==u.id))
    for r in results:
        db.add(CareerRecommendation(user_id=u.id,career=r['career'],match_score=r['match_score'],reasoning=r['reasoning']))
    top=results[0]; tasks=[]
    for skill in top['missing']:
        t=LearningTask(user_id=u.id,task=f"Learn {skill}",priority="High" if skill in top['missing'][:3] else "Medium",category="Skill Gap",estimated_hours=8)
        db.add(t); tasks.append(t)
    for t in ["Build one portfolio project for your target role","Practice DSA and technical interview questions","Optimize your resume for ATS"]:
        db.add(LearningTask(user_id=u.id,task=t,priority="High",category="Placement",estimated_hours=6))
    db.commit(); return {"recommendations":results,"top_role":top}
@router.get('/career/recommendations')
def recs(u=Depends(current_user),db:Session=Depends(get_db)):
    return [{"career":r.career,"match_score":r.match_score,"reasoning":r.reasoning} for r in db.scalars(select(CareerRecommendation).where(CareerRecommendation.user_id==u.id).order_by(CareerRecommendation.match_score.desc())).all()]
@router.get('/learning')
def learning(u=Depends(current_user),db:Session=Depends(get_db)):
    return [{"id":t.id,"task":t.task,"priority":t.priority,"category":t.category,"estimated_hours":t.estimated_hours,"completed":t.completed} for t in db.scalars(select(LearningTask).where(LearningTask.user_id==u.id)).all()]
@router.put('/learning/{task_id}')
def update_task(task_id:int,x:TaskUpdate,u=Depends(current_user),db:Session=Depends(get_db)):
    t=db.scalar(select(LearningTask).where(LearningTask.id==task_id,LearningTask.user_id==u.id));
    if not t: raise HTTPException(404,"Task not found")
    t.completed=x.completed; db.commit(); return {"ok":True}
@router.get('/resumes')
def resumes(u=Depends(current_user),db:Session=Depends(get_db)):
    return [{"id":r.id,"name":r.name,"template":r.template,"content":r.content,"version":r.version,"ats_score":r.ats_score} for r in db.scalars(select(Resume).where(Resume.user_id==u.id).order_by(Resume.id.desc())).all()]
@router.post('/resumes')
def create_resume(x:ResumeIn,u=Depends(current_user),db:Session=Depends(get_db)):
    r=Resume(user_id=u.id,name=x.name,template=x.template,content=x.content,ats_score=ats_score(x.content)); db.add(r); db.commit(); db.refresh(r); return {"id":r.id,"ats_score":r.ats_score}
@router.put('/resumes/{rid}')
def update_resume(rid:int,x:ResumeIn,u=Depends(current_user),db:Session=Depends(get_db)):
    r=db.scalar(select(Resume).where(Resume.id==rid,Resume.user_id==u.id));
    if not r: raise HTTPException(404,"Resume not found")
    r.name=x.name;r.template=x.template;r.content=x.content;r.version+=1;r.ats_score=ats_score(x.content);db.commit();return {"id":r.id,"ats_score":r.ats_score}
def ats_score(c):
    required=["summary","education","skills","projects"]
    present=sum(bool(c.get(k)) for k in required); bullets=str(c.get("projects","")).count("-")+str(c.get("experience","")).count("-")
    return min(100, round(present/len(required)*65 + min(35,bullets*5)))
@router.post('/resume/enhance')
async def enhance_resume(x:EnhanceIn,u=Depends(current_user),db:Session=Depends(get_db)):
    s=db.scalar(select(LLMSetting).where(LLMSetting.user_id==u.id))
    if not s or s.provider=="none" or not s.encrypted_api_key: raise HTTPException(400,"Configure an LLM provider and API key in Settings first")
    try: return {"text":await enhance(s.provider,s.model,s.encrypted_api_key,x.section,x.text)}
    except Exception as e: raise HTTPException(502,f"LLM request failed: {str(e)[:180]}")
@router.put('/llm/settings')
def save_llm(x:LLMIn,u=Depends(current_user),db:Session=Depends(get_db)):
    s=db.scalar(select(LLMSetting).where(LLMSetting.user_id==u.id))
    if not s: s=LLMSetting(user_id=u.id); db.add(s)
    s.provider=x.provider;s.model=x.model
    if x.api_key: s.encrypted_api_key=encrypt(x.api_key)
    db.commit(); return {"provider":s.provider,"model":s.model,"configured":bool(s.encrypted_api_key)}
@router.get('/llm/settings')
def get_llm(u=Depends(current_user),db:Session=Depends(get_db)):
    s=db.scalar(select(LLMSetting).where(LLMSetting.user_id==u.id)); return {"provider":s.provider if s else "none","model":s.model if s else "","configured":bool(s and s.encrypted_api_key)}
@router.delete('/llm/settings')
def delete_llm(u=Depends(current_user),db:Session=Depends(get_db)):
    db.execute(delete(LLMSetting).where(LLMSetting.user_id==u.id));db.commit();return {"ok":True}
