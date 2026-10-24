"""Unit tests for the agent modules (no web framework or database needed).

Run from the backend folder:  python -m unittest discover -s tests -v
"""
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.agents import (coding_agent, interview_agent, job_agent, readiness, resume_agent, roadmap, skill_gap_agent)  # noqa: E402
from app.agents.catalog import extract_skills, normalize_skill, resolve_role  # noqa: E402

SAMPLE = (Path(__file__).parent / "sample_resume.txt").read_bytes()
PROFILE = {"career_goal": "Backend Developer", "cgpa": 7.8, "skills": [{"name": "Python", "level": "Advanced"}, {"name": "MySQL"}, {"name": "Git", "level": "Beginner"}],
           "projects": [{"title": "Portal", "description": "FastAPI REST API with Docker"}], "experiences": [], "certifications": [], "interests": []}


class Catalog(unittest.TestCase):
    def test_java_is_not_javascript(self):
        self.assertEqual(extract_skills("I know JavaScript"), ["javascript"])
        self.assertIn("java", extract_skills("Java and JavaScript"))

    def test_aliases(self):
        self.assertEqual(normalize_skill("ReactJS"), "react")
        self.assertEqual(normalize_skill("PostgreSQL"), "sql")
        self.assertEqual(resolve_role("full stack dev"), "Full Stack Developer")


class ResumeAgent(unittest.TestCase):
    def test_parse_text(self):
        r = resume_agent.analyze("cv.txt", SAMPLE, "backend")
        p = r["parsed"]
        self.assertEqual(p["contact"]["email"], "rahul.patil@example.com")
        self.assertEqual(p["education"]["cgpa"], 8.4)
        self.assertEqual(p["education"]["graduation_year"], 2026)
        self.assertEqual(p["links"]["github"], "rahulp")
        self.assertIn("python", p["skills"]); self.assertEqual(len(p["projects"]), 2)
        self.assertTrue(0 < r["ats_score"] <= 100); self.assertTrue(r["suggestions"])

    def test_pdf_and_docx(self):
        import docx
        from reportlab.pdfgen import canvas
        buf = io.BytesIO(); c = canvas.Canvas(buf); y = 800
        for ln in SAMPLE.decode().split("\n"): c.drawString(40, y, ln); y -= 14
        c.save()
        self.assertEqual(resume_agent.parse_resume(resume_agent.extract_text("a.pdf", buf.getvalue()))["education"]["cgpa"], 8.4)
        d = docx.Document()
        for ln in SAMPLE.decode().split("\n"): d.add_paragraph(ln)
        b = io.BytesIO(); d.save(b)
        self.assertIn("python", resume_agent.parse_resume(resume_agent.extract_text("a.docx", b.getvalue()))["skills"])

    def test_bad_files(self):
        for name, data in [("a.exe", b"x"), ("a.txt", b""), ("a.pdf", b"not a pdf")]:
            with self.assertRaises(ValueError): resume_agent.extract_text(name, data)

    def test_merge_does_not_overwrite(self):
        parsed = resume_agent.parse_resume(SAMPLE.decode())
        upd = resume_agent.merge_into_profile({"skills": [{"name": "Python"}], "cgpa": 9.0, "projects": [{"title": "mine"}]}, parsed)
        self.assertNotIn("cgpa", upd); self.assertNotIn("projects", upd)
        self.assertNotIn("python", [s["name"] for s in upd["skills"][1:]])


class SkillGap(unittest.TestCase):
    def test_report(self):
        r = skill_gap_agent.skill_gap_report(PROFILE)
        self.assertEqual(r["target_role"], "Backend Developer")
        self.assertTrue(any(g["skill"] == "dbms" and g["priority"] == "High" for g in r["gaps"]))
        self.assertTrue(0 <= r["coverage"] <= 100)

    def test_any_of_group(self):
        have = skill_gap_agent.candidate_skills({"skills": [{"name": "java", "level": "Advanced"}]})
        row = next(x for x in skill_gap_agent.role_gap(have, "Software Developer")["rows"] if x["skill"].startswith("python|"))
        self.assertEqual(row["matched_with"], "java")


class Coding(unittest.TestCase):
    def test_scoring_monotonic(self):
        lo = coding_agent.analyze_coding([coding_agent.normalize("leetcode", "a", 20, 5, 0)])
        hi = coding_agent.analyze_coding([coding_agent.normalize("leetcode", "a", 120, 150, 30, 1700, 10)])
        self.assertLess(lo["score"], hi["score"]); self.assertLessEqual(hi["score"], 100)

    def test_empty_and_handle_validation(self):
        self.assertFalse(coding_agent.analyze_coding([])["assessed"])
        self.assertEqual(coding_agent.clean_handle("github", "https://github.com/octocat/"), "octocat")
        with self.assertRaises(coding_agent.CodingFetchError): coding_agent.clean_handle("github", "../etc/passwd")


class JobMatching(unittest.TestCase):
    def test_companies_sorted_and_bounded(self):
        have = skill_gap_agent.candidate_skills(PROFILE)
        m = job_agent.match_companies(PROFILE, have, 50, top=20)
        self.assertTrue(all(0 <= x["match_score"] <= 100 for x in m))
        self.assertEqual([x["match_score"] for x in m], sorted((x["match_score"] for x in m), reverse=True))

    def test_job_description(self):
        have = skill_gap_agent.candidate_skills(PROFILE)
        r = job_agent.match_job_description("Need Python, SQL and Kubernetes", have)
        self.assertIn("kubernetes", r["missing"]); self.assertIn("python", r["matched"])


class Interview(unittest.TestCase):
    def test_plan_and_eval(self):
        have = skill_gap_agent.candidate_skills(PROFILE)
        plan = interview_agent.build_plan(PROFILE, have, "Backend Developer", 6, seed=3)
        self.assertEqual(len(plan), 6); self.assertEqual(plan[0]["category"], "HR")
        weak = interview_agent.evaluate_heuristic(plan[1], "idk")
        strong = interview_agent.evaluate_heuristic(plan[1], " ".join(plan[1]["keywords"]) + " for example because of the trade-off " * 6)
        self.assertLess(weak["score"], strong["score"])

    def test_llm_json_parsing(self):
        self.assertEqual(interview_agent.llm_evaluation('```json\n{"score": 99}\n```')["score"], 10.0)
        with self.assertRaises(ValueError): interview_agent.llm_questions('{"questions": []}')


class ReadinessAndRoadmap(unittest.TestCase):
    def test_unassessed_counts_zero(self):
        gap = skill_gap_agent.skill_gap_report(PROFILE)
        r = readiness.compute_readiness(PROFILE, 60, gap, None, coding_agent.analyze_coding([]), None)
        self.assertLess(r["confidence"], 100); self.assertEqual(sum(c["weight"] for c in r["components"]), 100)
        full = readiness.compute_readiness(PROFILE, 100, gap, 90, coding_agent.analyze_coding([coding_agent.normalize("leetcode", "a", 100, 100, 20, 1600, 6)]), 85)
        self.assertGreater(full["score"], r["score"])

    def test_roadmap(self):
        gap = skill_gap_agent.skill_gap_report(PROFILE)
        t = roadmap.generate_roadmap(gap, coding_agent.analyze_coding([]), None, None, 1, 10)
        self.assertTrue(t); self.assertTrue(all(x["category"].startswith("Week ") for x in t))


if __name__ == "__main__":
    unittest.main()
