"""Coding Analytics Agent: pulls public stats from coding platforms and turns them into insights.

Public endpoints used (no API keys needed): LeetCode GraphQL, Codeforces API, GitHub REST API.
If a platform is unreachable the user can enter stats manually.
"""
import re
from datetime import datetime, timedelta, timezone

PLATFORMS = ("leetcode", "codeforces", "github", "manual")


class CodingFetchError(Exception):
    pass


def clean_handle(platform: str, value: str) -> str:
    v = (value or "").strip().rstrip("/")
    m = re.search(r"(?:leetcode\.com/(?:u/)?|codeforces\.com/profile/|github\.com/)([A-Za-z0-9_.\-]+)", v, re.I)
    v = m.group(1) if m else v.lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_.\-]{1,40}", v): raise CodingFetchError("Invalid username")
    return v


async def _get_json(client, url, **kw):
    try:
        r = await client.get(url, **kw)
    except Exception as e:
        raise CodingFetchError(f"Could not reach {url.split('/')[2]}: {type(e).__name__}")
    if r.status_code == 404: raise CodingFetchError("User not found")
    if r.status_code in (403, 429): raise CodingFetchError("Rate limited by the platform; try again later")
    if r.status_code >= 400: raise CodingFetchError(f"Platform returned HTTP {r.status_code}")
    return r.json()


async def fetch_leetcode(handle: str) -> dict:
    import httpx
    q = """query($u:String!){matchedUser(username:$u){username profile{ranking}
      submitStatsGlobal{acSubmissionNum{difficulty count}}}
      userContestRanking(username:$u){rating attendedContestsCount}}"""
    async with httpx.AsyncClient(timeout=15, headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"}) as c:
        try:
            r = await c.post("https://leetcode.com/graphql", json={"query": q, "variables": {"u": handle}})
            r.raise_for_status(); d = r.json()["data"]
        except Exception as e:
            raise CodingFetchError(f"LeetCode request failed: {type(e).__name__}")
    if not d.get("matchedUser"): raise CodingFetchError("LeetCode user not found")
    counts = {x["difficulty"].lower(): x["count"] for x in d["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]}
    cr = d.get("userContestRanking") or {}
    return normalize("leetcode", handle, easy=counts.get("easy", 0), medium=counts.get("medium", 0), hard=counts.get("hard", 0),
                     rating=round(cr["rating"]) if cr.get("rating") else None, contests=cr.get("attendedContestsCount", 0),
                     extra={"global_rank": d["matchedUser"]["profile"].get("ranking")})


async def fetch_codeforces(handle: str) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        info = await _get_json(c, "https://codeforces.com/api/user.info", params={"handles": handle})
        if info.get("status") != "OK": raise CodingFetchError("Codeforces user not found")
        u = info["result"][0]
        subs = await _get_json(c, "https://codeforces.com/api/user.status", params={"handle": handle, "from": 1, "count": 2000})
        try: rated = await _get_json(c, "https://codeforces.com/api/user.rating", params={"handle": handle}); contests = len(rated.get("result", []))
        except CodingFetchError: contests = 0
    solved: dict[str, int | None] = {}
    tags: dict[str, int] = {}
    for s in subs.get("result", []):
        if s.get("verdict") != "OK": continue
        p = s["problem"]; key = f"{p.get('contestId')}{p.get('index')}"
        if key in solved: continue
        solved[key] = p.get("rating")
        for t in p.get("tags", []): tags[t] = tags.get(t, 0) + 1
    easy = sum(1 for r in solved.values() if r is not None and r <= 1200)
    hard = sum(1 for r in solved.values() if r is not None and r > 1700)
    medium = sum(1 for r in solved.values() if r is not None and 1200 < r <= 1700) + sum(1 for r in solved.values() if r is None)
    return normalize("codeforces", handle, easy=easy, medium=medium, hard=hard, rating=u.get("rating"), contests=contests,
                     extra={"max_rating": u.get("maxRating"), "rank": u.get("rank"), "top_tags": sorted(tags, key=tags.get, reverse=True)[:6]})


async def fetch_github(handle: str) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=20, headers={"Accept": "application/vnd.github+json", "User-Agent": "placement-portal"}) as c:
        u = await _get_json(c, f"https://api.github.com/users/{handle}")
        repos = await _get_json(c, f"https://api.github.com/users/{handle}/repos", params={"per_page": 100, "sort": "pushed"})
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    own = [r for r in repos if not r.get("fork")]
    langs: dict[str, int] = {}
    for r in own:
        if r.get("language"): langs[r["language"]] = langs.get(r["language"], 0) + 1
    active = sum(1 for r in own if r.get("pushed_at") and datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")) >= cutoff)
    return {"platform": "github", "handle": handle, "solved": {"easy": 0, "medium": 0, "hard": 0, "total": 0}, "rating": None, "contests": 0,
            "extra": {"public_repos": u.get("public_repos", len(own)), "original_repos": len(own), "followers": u.get("followers", 0),
                      "stars": sum(r.get("stargazers_count", 0) for r in own), "active_repos_90d": active,
                      "languages": dict(sorted(langs.items(), key=lambda x: -x[1])[:6])}}


FETCHERS = {"leetcode": fetch_leetcode, "codeforces": fetch_codeforces, "github": fetch_github}


def normalize(platform, handle, easy=0, medium=0, hard=0, rating=None, contests=0, extra=None) -> dict:
    easy, medium, hard = max(0, int(easy or 0)), max(0, int(medium or 0)), max(0, int(hard or 0))
    return {"platform": platform, "handle": handle, "solved": {"easy": easy, "medium": medium, "hard": hard, "total": easy + medium + hard},
            "rating": int(rating) if rating else None, "contests": int(contests or 0), "extra": extra or {}}


def analyze_coding(stats: list[dict]) -> dict:
    """stats: list of normalized platform dicts. Returns score (0-100) + insights."""
    if not stats:
        return {"assessed": False, "score": 0, "total_solved": 0, "level": "No data", "difficulty_mix": {"easy": 0, "medium": 0, "hard": 0},
                "platforms": [], "strengths": [], "weaknesses": ["No coding profile linked yet."],
                "recommendations": ["Link your LeetCode / Codeforces / GitHub handles to get coding analytics."]}
    e = sum(s["solved"]["easy"] for s in stats); m = sum(s["solved"]["medium"] for s in stats); h = sum(s["solved"]["hard"] for s in stats)
    total = e + m + h
    weighted = e + 2 * m + 3 * h
    volume = min(60, weighted / 300 * 60)
    lc = next((s for s in stats if s["platform"] == "leetcode"), None); cf = next((s for s in stats if s["platform"] == "codeforces"), None)
    gh = next((s for s in stats if s["platform"] == "github"), None)
    lc_r = (lc or {}).get("rating") or 0; cf_r = (cf or {}).get("rating") or 0
    rating_pts = max(15 if lc_r >= 1600 else 10 if lc_r >= 1400 else 5 if lc_r >= 1200 else 0,
                     15 if cf_r >= 1400 else 10 if cf_r >= 1200 else 5 if cf_r >= 1000 else 0)
    balance = 10 if total and (m + h) / total >= 0.4 else 5 if total and (m + h) / total >= 0.25 else 0
    contests = sum(s["contests"] for s in stats)
    contest_pts = 5 if contests >= 3 else 2 if contests >= 1 else 0
    gx = (gh or {}).get("extra", {})
    gh_pts = min(10, gx.get("original_repos", 0) + 2 * gx.get("active_repos_90d", 0)) if gh else 0
    score = round(min(100, volume + rating_pts + balance + contest_pts + gh_pts))

    strengths, weak, recs = [], [], []
    if total >= 150: strengths.append(f"Solid problem volume ({total} solved).")
    if total and (m + h) / total >= 0.4: strengths.append("Good difficulty mix: 40%+ medium/hard problems.")
    if lc_r >= 1500 or cf_r >= 1200: strengths.append("Competitive contest rating shows speed under pressure.")
    if gx.get("active_repos_90d", 0) >= 2: strengths.append("Active GitHub: recent commits in multiple repositories.")
    if cf and cf["extra"].get("top_tags"): strengths.append("Most-solved Codeforces topics: " + ", ".join(cf["extra"]["top_tags"][:3]) + ".")
    if gh and gx.get("languages"): strengths.append("GitHub languages: " + ", ".join(list(gx["languages"])[:3]) + ".")
    if (lc or cf) and total < 100: weak.append(f"Only {total} problems solved so far."); recs.append("Aim for 5 problems a week; cover arrays, strings, hashing, two pointers, trees and graphs first.")
    if total and h == 0 and total >= 30: weak.append("No hard problems solved."); recs.append("Add 1-2 hard problems a week once you are comfortable with mediums (DP, graphs).")
    if total and (m + h) / total < 0.25 and total >= 30: weak.append("Mostly easy problems."); recs.append("Shift to medium problems: that is the level most online assessments use.")
    if (lc or cf) and contests == 0: weak.append("No contest participation."); recs.append("Join weekly contests to build speed; product-company OAs are timed.")
    if gh and gx.get("active_repos_90d", 0) == 0: weak.append("No GitHub activity in the last 90 days."); recs.append("Push a project regularly; recruiters check recent activity.")
    if not gh: recs.append("Link your GitHub so projects and activity count in your profile.")
    if not (lc or cf) and not any(s["platform"] == "manual" for s in stats): recs.append("Link LeetCode or Codeforces to measure DSA practice.")
    level = "Advanced" if score >= 75 else "Intermediate" if score >= 45 else "Beginner"
    return {"assessed": True, "score": score, "level": level, "total_solved": total, "difficulty_mix": {"easy": e, "medium": m, "hard": h},
            "contests": contests, "platforms": stats, "strengths": strengths, "weaknesses": weak, "recommendations": recs[:6],
            "score_breakdown": {"volume": round(volume), "ratings": rating_pts, "difficulty_balance": balance, "contests": contest_pts, "github": gh_pts}}
