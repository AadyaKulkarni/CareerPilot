"""Skill taxonomy, role requirements and learning hints shared by all agents."""
import re
from difflib import SequenceMatcher

# canonical skill -> aliases (all lowercase)
SKILL_ALIASES: dict[str, list[str]] = {
    "python": ["python3", "python 3", "py"],
    "java": ["core java", "java se", "java 8", "java 11", "java 17"],
    "javascript": ["js", "es6", "ecmascript", "vanilla js"],
    "typescript": ["ts"],
    "c++": ["cpp", "c plus plus"],
    "c": ["c programming", "c language"],
    "c#": ["csharp", "c sharp", ".net", "dotnet", "asp.net"],
    "go": ["golang"],
    "sql": ["mysql", "postgresql", "postgres", "sqlite", "mssql", "sql server", "oracle sql", "pl/sql", "t-sql", "rdbms"],
    "mongodb": ["mongo", "nosql"],
    "dsa": ["data structures", "algorithms", "data structures and algorithms", "data structure", "competitive programming"],
    "oop": ["oops", "object oriented", "object-oriented", "object oriented programming"],
    "dbms": ["database management", "database management systems", "database design"],
    "operating systems": ["os concepts", "operating system"],
    "computer networks": ["networking", "tcp/ip", "computer networking", "network protocols"],
    "git": ["github", "gitlab", "version control", "bitbucket"],
    "rest api": ["rest", "restful", "rest apis", "restful api", "restful apis", "api development", "web services"],
    "html": ["html5"],
    "css": ["css3", "tailwind", "tailwind css", "bootstrap", "sass", "scss"],
    "react": ["reactjs", "react.js", "react js", "redux", "next.js", "nextjs"],
    "node.js": ["node", "nodejs", "node js", "express", "express.js", "expressjs"],
    "angular": ["angularjs", "angular.js"],
    "django": [],
    "flask": [],
    "fastapi": [],
    "spring boot": ["springboot", "spring", "spring framework", "hibernate"],
    "machine learning": ["ml", "scikit-learn", "sklearn", "supervised learning", "xgboost"],
    "deep learning": ["dl", "neural networks", "neural network", "cnn", "rnn", "lstm", "transformers"],
    "nlp": ["natural language processing", "text mining", "llm", "llms", "langchain"],
    "computer vision": ["opencv", "image processing", "yolo"],
    "pytorch": ["torch"],
    "tensorflow": ["keras", "tf"],
    "pandas": [],
    "numpy": [],
    "statistics": ["probability", "statistical analysis", "hypothesis testing", "probability and statistics"],
    "visualization": ["data visualization", "matplotlib", "seaborn", "plotly"],
    "excel": ["ms excel", "microsoft excel", "advanced excel", "vlookup", "pivot tables"],
    "power bi": ["powerbi", "power-bi"],
    "tableau": [],
    "linux": ["unix", "bash", "shell scripting", "shell"],
    "docker": ["containers", "containerization", "docker compose"],
    "kubernetes": ["k8s"],
    "aws": ["amazon web services", "ec2", "s3", "lambda"],
    "azure": ["microsoft azure"],
    "gcp": ["google cloud", "google cloud platform"],
    "ci/cd": ["cicd", "ci cd", "jenkins", "github actions", "gitlab ci", "continuous integration"],
    "terraform": ["infrastructure as code", "iac", "ansible"],
    "security": ["cybersecurity", "cyber security", "infosec", "owasp", "penetration testing", "ethical hacking", "network security"],
    "cryptography": ["encryption", "pki"],
    "siem": ["splunk", "qradar", "soc"],
    "cloud": ["cloud computing"],
    "system design": ["low level design", "high level design", "hld", "lld", "scalability", "microservices"],
    "testing": ["unit testing", "pytest", "junit", "selenium", "test automation", "jest"],
    "agile": ["scrum", "kanban"],
    "communication": ["communication skills", "presentation skills", "public speaking", "soft skills"],
    "problem solving": ["problem-solving", "analytical thinking", "analytical skills"],
}

DEFAULT_LEVEL_WEIGHT = {"beginner": 0.5, "intermediate": 0.8, "advanced": 1.0, "expert": 1.0}
MENTIONED_WEIGHT = 0.6  # skill seen on resume / projects but not self-rated

_ALIAS_TO_CANON: dict[str, str] = {}
for _c, _al in SKILL_ALIASES.items():
    _ALIAS_TO_CANON[_c] = _c
    for _a in _al:
        _ALIAS_TO_CANON[_a] = _c

# aliases too short / ambiguous to find inside free text
_TEXT_SKIP = {"py", "tf", "os concepts", "dl", "ml", "ts", "soc", "iac", "go", "c"}
_TEXT_ALLOW_EXACT = {"go": r"golang", "c": r"c programming|c language"}


def _build_patterns():
    pats = {}
    for canon, aliases in SKILL_ALIASES.items():
        terms = {canon, *aliases}
        # ambiguous short tokens only match as listed
        terms = {t for t in terms if t not in _TEXT_SKIP or t in ("ml", "dl")}
        if canon == "go": terms = {"golang"}
        if canon == "c": terms = {"c programming", "c language"}
        if canon in ("ml",): pass
        alt = "|".join(sorted((re.escape(t) for t in terms), key=len, reverse=True))
        pats[canon] = re.compile(rf"(?<![A-Za-z0-9+#]){'(?:' + alt + ')'}(?![A-Za-z0-9+#])", re.I)
    return pats

_PATTERNS = _build_patterns()


def extract_skills(text: str) -> list[str]:
    """Return canonical skills mentioned in free text."""
    if not text: return []
    return [c for c, p in _PATTERNS.items() if p.search(text)]


def normalize_skill(name: str) -> str:
    """Map a user-typed skill to a canonical skill (best effort)."""
    n = (name or "").strip().lower()
    if not n: return ""
    if n in _ALIAS_TO_CANON: return _ALIAS_TO_CANON[n]
    found = extract_skills(n)
    if len(found) == 1 and len(n.split()) <= 3: return found[0]
    best, score = "", 0.0
    for a, c in _ALIAS_TO_CANON.items():
        if len(a) < 4: continue
        r = SequenceMatcher(None, n, a).ratio()
        if r > score: best, score = c, r
    return best if score >= 0.82 else n


# ---- roles -------------------------------------------------------------
# core items weigh 2, nice items weigh 1. "a|b|c" means any one of these satisfies the item.
ROLES: dict[str, dict[str, list[str]]] = {
    "Software Developer": {
        "core": ["python|java|c++|javascript", "dsa", "oop", "sql", "git", "dbms"],
        "nice": ["rest api", "operating systems", "system design", "testing"]},
    "Backend Developer": {
        "core": ["python|java|node.js|c#", "sql", "rest api", "git", "dbms", "dsa"],
        "nice": ["docker", "system design", "testing", "mongodb"]},
    "Full Stack Developer": {
        "core": ["javascript", "html", "css", "react", "node.js", "sql", "git", "rest api"],
        "nice": ["typescript", "mongodb", "docker", "testing"]},
    "AI/ML Engineer": {
        "core": ["python", "machine learning", "deep learning", "pytorch|tensorflow", "numpy", "pandas", "statistics", "git"],
        "nice": ["nlp", "sql", "docker", "visualization", "computer vision"]},
    "Data Scientist": {
        "core": ["python", "machine learning", "statistics", "sql", "pandas", "numpy", "visualization"],
        "nice": ["deep learning", "power bi|tableau", "git", "communication"]},
    "Data Analyst": {
        "core": ["sql", "excel", "python", "power bi|tableau", "statistics", "visualization"],
        "nice": ["pandas", "communication", "problem solving"]},
    "Cloud/DevOps Engineer": {
        "core": ["linux", "docker", "kubernetes", "aws|azure|gcp", "git", "ci/cd"],
        "nice": ["terraform", "computer networks", "python"]},
    "Cybersecurity Engineer": {
        "core": ["computer networks", "linux", "security", "cryptography", "python"],
        "nice": ["siem", "cloud", "operating systems"]},
}


def label(item: str) -> str:
    parts = item.split("|")
    return item if len(parts) == 1 else " / ".join(parts) + " (any one)"


def resolve_role(name: str) -> str:
    """Map free text such as 'full stack dev' to a known role."""
    from difflib import get_close_matches
    if not name: return "Software Developer"
    for r in ROLES:
        if r.lower() == name.strip().lower(): return r
    low = name.lower()
    keys = {"full": "Full Stack Developer", "backend": "Backend Developer", "back end": "Backend Developer",
            "ml": "AI/ML Engineer", "ai": "AI/ML Engineer", "machine": "AI/ML Engineer", "data sci": "Data Scientist",
            "analyst": "Data Analyst", "devops": "Cloud/DevOps Engineer", "cloud": "Cloud/DevOps Engineer",
            "security": "Cybersecurity Engineer", "cyber": "Cybersecurity Engineer"}
    for k, r in keys.items():
        if k in low: return r
    m = get_close_matches(name, list(ROLES), n=1, cutoff=0.5)
    return m[0] if m else "Software Developer"


# ---- learning hints (hours, how) ----------------------------------------
LEARN: dict[str, tuple[int, str]] = {
    "dsa": (40, "Solve ~100 problems across arrays, strings, hashing, trees, graphs and DP; review patterns after each set."),
    "sql": (12, "Practise joins, group-by, window functions and subqueries on 40+ queries."),
    "dbms": (10, "Cover normalisation, transactions/ACID, indexing and ER modelling."),
    "oop": (8, "Revise the four pillars with small design exercises in your main language."),
    "operating systems": (12, "Study processes/threads, scheduling, deadlocks, memory management."),
    "computer networks": (10, "Study OSI/TCP-IP, HTTP/DNS, and trace a request end to end."),
    "git": (4, "Practise branching, merging, rebasing and pull requests on a real repo."),
    "rest api": (8, "Build a small CRUD API with auth, validation and status codes."),
    "system design": (20, "Learn the basics of load balancing, caching, DB sharding; design 5 common systems."),
    "react": (20, "Build a multi-page app covering state, effects, routing and API calls."),
    "node.js": (14, "Build a REST API with Express, a database and JWT auth."),
    "docker": (8, "Containerise one of your projects and run it with docker compose."),
    "kubernetes": (16, "Deploy a containerised app on a local cluster (kind/minikube)."),
    "aws": (16, "Deploy a small app using compute, storage and a managed database."),
    "ci/cd": (8, "Add a CI pipeline that tests, builds and deploys one of your projects."),
    "machine learning": (30, "Work through supervised/unsupervised basics and finish 2 end-to-end projects."),
    "deep learning": (30, "Train a CNN and a sequence model; understand backprop and regularisation."),
    "statistics": (14, "Cover distributions, hypothesis testing, confidence intervals, regression."),
    "pandas": (8, "Clean and analyse a real dataset end to end."),
    "numpy": (5, "Practise vectorised operations, broadcasting and linear algebra helpers."),
    "visualization": (6, "Produce a dashboard-style set of charts that tells a data story."),
    "excel": (8, "Pivot tables, lookups, conditional formatting and basic charts."),
    "power bi|tableau": (10, "Build one interactive dashboard from a public dataset."),
    "linux": (10, "Use the shell daily: files, permissions, processes, pipes, scripting."),
    "security": (20, "Learn the OWASP Top 10 and practise on intentionally vulnerable labs."),
    "cryptography": (12, "Symmetric vs asymmetric crypto, hashing, TLS, digital signatures."),
    "testing": (8, "Add unit and integration tests to an existing project."),
    "communication": (6, "Record yourself explaining a project in 2 minutes; iterate on clarity."),
}
DEFAULT_LEARN = (10, "Take a structured course, then apply it in a small hands-on project.")


def learn_hint(item: str) -> tuple[int, str]:
    return LEARN.get(item) or LEARN.get(item.split("|")[0]) or DEFAULT_LEARN
