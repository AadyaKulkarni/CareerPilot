"""Interview Agent: plans a mock interview, evaluates answers (LLM when configured, heuristics otherwise)."""
import json
import random
import re
from .catalog import ROLES, label, resolve_role

# --- question bank: skill -> [(question, expected keywords)] ----------------
TECH: dict[str, list[tuple[str, list[str]]]] = {
    "python": [("What is the difference between a list and a tuple in Python, and when would you use each?", ["mutable", "immutable", "tuple", "list", "hashable", "performance"]),
               ("Explain how decorators and generators work in Python.", ["function", "wrapper", "yield", "iterator", "lazy", "memory"])],
    "java": [("Explain the difference between an abstract class and an interface in Java.", ["abstract", "interface", "multiple", "inheritance", "default", "implements"]),
             ("How does garbage collection work in Java?", ["heap", "garbage", "reachable", "generation", "jvm", "gc"])],
    "javascript": [("Explain closures and the event loop in JavaScript.", ["closure", "scope", "event loop", "callback", "promise", "async"]),
                   ("What is the difference between var, let and const?", ["scope", "hoisting", "block", "reassign", "const"])],
    "c++": [("What is the difference between a pointer and a reference in C++?", ["pointer", "reference", "null", "reassign", "address"])],
    "sql": [("What is the difference between INNER JOIN and LEFT JOIN? Give an example.", ["inner", "left", "null", "matching", "rows", "join"]),
            ("How would you find the second highest salary in an employee table?", ["subquery", "limit", "offset", "dense_rank", "max", "order by"])],
    "dsa": [("How would you detect a cycle in a linked list? Discuss time and space complexity.", ["fast", "slow", "pointer", "floyd", "o(1)", "o(n)"]),
            ("When would you use a hash map versus a balanced BST? Compare their complexities.", ["hash", "o(1)", "o(log n)", "ordered", "collision", "bst"])],
    "oop": [("Explain the four pillars of OOP with a real example.", ["encapsulation", "abstraction", "inheritance", "polymorphism", "example", "class"])],
    "dbms": [("What are ACID properties? Why do they matter?", ["atomicity", "consistency", "isolation", "durability", "transaction"]),
             ("Explain normalisation and when you might denormalise.", ["1nf", "2nf", "3nf", "redundancy", "join", "performance"])],
    "operating systems": [("What is the difference between a process and a thread? What is a deadlock?", ["process", "thread", "memory", "shared", "deadlock", "lock"])],
    "computer networks": [("What happens when you type a URL into the browser and press Enter?", ["dns", "tcp", "http", "tls", "server", "render"])],
    "git": [("Explain the difference between git merge and git rebase.", ["merge", "rebase", "history", "commit", "conflict", "linear"])],
    "rest api": [("What makes an API RESTful? Explain HTTP methods and status codes you would use for a CRUD resource.", ["get", "post", "put", "delete", "status", "stateless", "200", "404"])],
    "react": [("Explain state versus props and when useEffect runs in React.", ["state", "props", "render", "useeffect", "dependency", "component"])],
    "node.js": [("How does Node.js handle concurrency despite being single-threaded?", ["event loop", "non-blocking", "async", "callback", "thread", "libuv"])],
    "machine learning": [("Explain overfitting and three ways to reduce it.", ["overfitting", "regularization", "cross-validation", "more data", "dropout", "validation"]),
                         ("How do precision, recall and F1 differ, and when does accuracy mislead?", ["precision", "recall", "f1", "imbalanced", "false positive", "accuracy"])],
    "deep learning": [("Explain backpropagation and the vanishing gradient problem.", ["gradient", "chain rule", "weights", "activation", "relu", "vanishing"])],
    "statistics": [("Explain p-value and the difference between Type I and Type II errors.", ["null", "hypothesis", "type i", "type ii", "significance", "false"])],
    "docker": [("What is the difference between a Docker image and a container? Why use Docker?", ["image", "container", "layer", "isolation", "reproducible", "dockerfile"])],
    "kubernetes": [("What are pods, deployments and services in Kubernetes?", ["pod", "deployment", "service", "replica", "scaling", "cluster"])],
    "aws": [("When would you use EC2 versus Lambda? Mention cost and scaling.", ["ec2", "lambda", "serverless", "scaling", "cost", "idle"])],
    "linux": [("Explain file permissions in Linux and how chmod 755 works.", ["read", "write", "execute", "owner", "group", "755"])],
    "security": [("Explain SQL injection and XSS, and how to prevent them.", ["injection", "parameterized", "sanitize", "escape", "xss", "validation"])],
    "system design": [("How would you design a URL shortener? Cover storage, scaling and collisions.", ["hash", "database", "cache", "collision", "scale", "redirect"])],
    "excel": [("How do VLOOKUP and INDEX-MATCH differ, and when do you use a pivot table?", ["vlookup", "index", "match", "pivot", "lookup", "summar"])],
    "power bi|tableau": [("How would you design a dashboard for a sales manager? What KPIs and visuals would you include?", ["kpi", "trend", "filter", "audience", "chart", "metric"])],
}
HR = [
    ("Tell me about yourself.", ["education", "project", "skills", "internship", "goal", "interest"]),
    ("Why do you want to work in this role and what are your career goals?", ["learn", "growth", "interest", "goal", "contribute", "skills"]),
    ("What are your strengths and one weakness you are working on?", ["strength", "weakness", "improve", "example", "learning"]),
]
BEHAVIORAL = [
    ("Describe a time you faced a difficult technical problem. How did you solve it?", ["problem", "approach", "result", "learned", "debug", "team"]),
    ("Tell me about a time you worked in a team and handled a disagreement.", ["team", "disagree", "listen", "compromise", "outcome", "communication"]),
    ("Describe a time you missed a deadline or failed at something. What did you do?", ["failed", "deadline", "responsibility", "learned", "changed", "next time"]),
]
STAR = {"situation": r"\b(when|during|in my|at the time|situation|context)\b", "task": r"\b(task|responsible|goal|needed to|had to|my role)\b",
        "action": r"\b(i (built|decided|implemented|created|wrote|fixed|led|organi[sz]ed|analy[sz]ed|proposed|learned)|my approach|i took)\b",
        "result": r"\b(result|outcome|improved|reduced|increased|achieved|learned|finally|successfully|%)\b"}


def _pick(rng, lst, k=1): return rng.sample(lst, min(k, len(lst)))


def build_plan(profile: dict, have: dict, role: str, n: int = 6, seed: int | None = None) -> list[dict]:
    role = resolve_role(role); rng = random.Random(seed)
    qs = [dict(zip(("question", "keywords"), HR[0]), category="HR")]
    spec = ROLES[role]["core"] + ROLES[role]["nice"]
    pool = []
    for item in spec:
        alts = [a for a in item.split("|") if a in have] or ([item] if item in TECH else [])
        key = item if item in TECH else next((a for a in alts if a in TECH), None)
        if key and (any(a in have for a in item.split("|"))): pool.append(key)
    pool += [i for i in spec if i in TECH and i not in pool]  # then skills they haven't claimed (probe gaps)
    seen = set()
    tech_n = max(1, n - 3)
    for key in pool:
        if key in seen or len([q for q in qs if q["category"] == "Technical"]) >= tech_n: continue
        seen.add(key); q, kw = rng.choice(TECH[key]); qs.append({"question": q, "keywords": kw, "category": "Technical", "topic": label(key)})
    projects = [p for p in (profile.get("projects") or []) if (p.get("title") if isinstance(p, dict) else p)]
    if projects:
        t = projects[0].get("title") if isinstance(projects[0], dict) else str(projects[0])
        qs.append({"question": f"Walk me through your project '{t[:80]}'. What was your role, which technical decisions did you make, and what would you improve?",
                   "keywords": ["role", "design", "technology", "challenge", "database", "improve", "result"], "category": "Project", "topic": t[:60]})
    q, kw = rng.choice(BEHAVIORAL); qs.append({"question": q, "keywords": kw, "category": "Behavioral"})
    if len(qs) < n:
        q, kw = HR[1]; qs.append({"question": q, "keywords": kw, "category": "HR"})
    qs = qs[:n]
    for i, q in enumerate(qs): q.update(id=i, answer=None, evaluation=None)
    return qs


def evaluate_heuristic(q: dict, answer: str) -> dict:
    a = (answer or "").strip(); low = a.lower(); words = len(a.split())
    kws = q.get("keywords", [])
    hit = [k for k in kws if k.lower() in low]
    miss = [k for k in kws if k.lower() not in low]
    cov = len(hit) / len(kws) if kws else 0.5
    length = 1.0 if 40 <= words <= 220 else 0.6 if 20 <= words < 40 else 0.3 if 8 <= words < 20 else 0.05 if words else 0
    if words > 220: length = 0.8
    extra = 0.0; improve = []; strong = []
    if q["category"] in ("Behavioral", "Project", "HR"):
        star = [k for k, rx in STAR.items() if re.search(rx, low)]
        extra = len(star) / 4
        if len(star) < 3: improve.append("Structure your answer with STAR: Situation, Task, Action, Result.")
        else: strong.append("Clear structure (situation, action and result).")
    else:
        if re.search(r"\b(for example|e\.g\.|for instance|such as)\b", low): extra += 0.5; strong.append("Used an example.")
        else: improve.append("Add a concrete example or code-level detail.")
        if re.search(r"o\(|complexity|trade-?off|because|however|whereas", low): extra += 0.5; strong.append("Explained trade-offs / reasoning.")
        else: improve.append("Explain why, not just what: mention trade-offs or complexity.")
    score10 = round(10 * (0.55 * cov + 0.25 * length + 0.20 * min(1, extra)), 1)
    if words < 20: improve.insert(0, "Your answer is very short; aim for 4-8 sentences.")
    if hit: strong.append("Covered: " + ", ".join(hit[:5]))
    if miss and q["category"] in ("Technical", "Project"): improve.append("Consider mentioning: " + ", ".join(miss[:4]))
    return {"score": min(10, score10), "feedback": " ".join(strong[:2]) or "Needs more substance.", "strengths": strong[:3], "improvements": improve[:3],
            "matched_keywords": hit, "missing_keywords": miss[:5], "method": "heuristic"}


def summarize(questions: list[dict]) -> dict:
    done = [q for q in questions if q.get("evaluation")]
    if not done: return {"overall_score": 0, "answered": 0, "by_category": {}, "strengths": [], "improvements": []}
    overall = round(sum(q["evaluation"]["score"] for q in done) / len(done) * 10)
    cats: dict[str, list[float]] = {}
    for q in done: cats.setdefault(q["category"], []).append(q["evaluation"]["score"])
    by = {k: round(sum(v) / len(v) * 10) for k, v in cats.items()}
    st, im = [], []
    for q in done:
        st += q["evaluation"].get("strengths", []); im += q["evaluation"].get("improvements", [])
    freq = lambda xs: [x for x, _ in sorted({x: xs.count(x) for x in xs}.items(), key=lambda t: -t[1])][:4]
    return {"overall_score": overall, "answered": len(done), "total": len(questions), "by_category": by, "strengths": freq(st), "improvements": freq(im),
            "verdict": "Interview-ready" if overall >= 75 else "Getting there" if overall >= 55 else "Needs more practice"}


# --- LLM prompts ---------------------------------------------------------
SYSTEM = "You are a strict but supportive technical interviewer for campus placements in India. Respond with JSON only."


def generation_prompt(profile: dict, role: str, n: int, difficulty: str) -> str:
    skills = ", ".join(s.get("name", "") for s in profile.get("skills", []) if isinstance(s, dict))[:300]
    projects = "; ".join((p.get("title", "") if isinstance(p, dict) else str(p)) for p in profile.get("projects", []))[:300]
    return (f"Create {n} mock interview questions for a fresher applying as {role}. Difficulty: {difficulty}. "
            f"Candidate skills: {skills or 'n/a'}. Projects: {projects or 'n/a'}. Include 1 HR, 1 behavioural, 1 project question (if projects exist), rest technical. "
            'Return JSON: {"questions":[{"question":str,"category":"HR|Technical|Behavioral|Project","topic":str,"keywords":[str,...]}]} with 4-7 expected keywords each.')


def evaluation_prompt(q: dict, answer: str, role: str) -> str:
    return (f"Role: {role}. Question ({q['category']}): {q['question']}\nCandidate answer: {answer[:2500]}\n"
            "Evaluate honestly; do not reward fluent but wrong answers. Return JSON: "
            '{"score":0-10 number,"feedback":str (2 sentences),"strengths":[str],"improvements":[str],"ideal_answer_points":[str]}')


def parse_json_loose(text: str):
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try: return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        if not m: raise ValueError("LLM did not return JSON")
        return json.loads(m.group(0))


def llm_questions(raw: str) -> list[dict]:
    data = parse_json_loose(raw).get("questions", [])
    out = []
    for i, q in enumerate(data):
        if not q.get("question"): continue
        out.append({"id": i, "question": str(q["question"])[:500], "category": q.get("category", "Technical") if q.get("category") in ("HR", "Technical", "Behavioral", "Project") else "Technical",
                    "topic": str(q.get("topic", ""))[:60], "keywords": [str(k) for k in q.get("keywords", [])][:8], "answer": None, "evaluation": None})
    if not out: raise ValueError("No questions returned")
    return out


def llm_evaluation(raw: str) -> dict:
    d = parse_json_loose(raw)
    return {"score": max(0.0, min(10.0, float(d.get("score", 0)))), "feedback": str(d.get("feedback", ""))[:600],
            "strengths": [str(x) for x in d.get("strengths", [])][:4], "improvements": [str(x) for x in d.get("improvements", [])][:4],
            "ideal_answer_points": [str(x) for x in d.get("ideal_answer_points", [])][:5], "matched_keywords": [], "missing_keywords": [], "method": "llm"}
