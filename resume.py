"""AI Resume Analyser CLI.

Usage:
  python resume.py <resume> [--job <job_description_file>] [--parse]
"""
import argparse
import json
import sys

from analyser import analyse_resume, keyword_overlap
from extractor import extract_text


def print_report(result: dict, job_description: str, resume_text: str) -> None:
    try:
        overall = int(result.get("overall_score", 0))
        ats = int(result.get("ats_score", 0))
    except (TypeError, ValueError):
        overall = ats = 0

    line = "=" * 52
    print(line)
    print("  AI RESUME ANALYSIS REPORT")
    print(line)
    print(f"  Overall score : {overall:>3}/100")
    print(f"  ATS score     : {ats:>3}/100")
    print(line)

    print("\n[ Sections found]")
    sections = result.get("sections_found") or []
    print("  " + (", ".join(sections) if sections else "None detected"))

    missing = result.get("missing_sections") or []
    if missing:
        print("\n[ Missing sections]")
        for item in missing:
            print(f"  - {item}")

    if job_description:
        coverage = result.get("keyword_coverage") or keyword_overlap(resume_text, job_description)
        match_rate = result.get("keyword_match_rate")
        if match_rate is None:
            matched = sum(coverage.values()) or 0
            match_rate = round(100 * matched / len(coverage)) if coverage else 0
        print("\n[ Keyword match vs job description]")
        print(f"  Match rate: {match_rate}%")
        if coverage:
            miss_kw = [k for k, v in coverage.items() if not v]
            if miss_kw:
                print(f"  Missing keywords: {', '.join(miss_kw[:25])}")

    strengths = result.get("strengths") or []
    if strengths:
        print("\n[ Strengths]")
        for s in strengths:
            print(f"  + {s}")

    weaknesses = result.get("weaknesses") or []
    if weaknesses:
        print("\n[ Weaknesses]")
        for w in weaknesses:
            print(f"  - {w}")

    suggestions = result.get("suggestions") or []
    if suggestions:
        print("\n[ Suggested improvements]")
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")

    improved = result.get("improved_summary")
    if improved:
        print("\n[ Improved professional summary]")
        print(f"  {improved}")

    print("\n" + line)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Resume Analyser")
    parser.add_argument("resume", help="Path to resume file (.pdf, .docx, .txt)")
    parser.add_argument("--job", "-j", help="Path to job description file (text)")
    parser.add_argument(
        "--parse", action="store_true", help="Only extract and print the resume text"
    )
    args = parser.parse_args()

    resume_text = extract_text(args.resume)

    if args.parse:
        print(resume_text)
        return 0

    job_description = ""
    if args.job:
        job_description = extract_text(args.job)

    if not resume_text.strip():
        print("Error: no readable text found in the resume.", file=sys.stderr)
        return 1

    try:
        result = analyse_resume(resume_text, job_description)
    except Exception as exc:
        print(f"Error: analysis failed - {exc}", file=sys.stderr)
        return 1
    if not result:
        print("Error: analysis returned empty results.", file=sys.stderr)
        return 1

    if args.job and not result.get("keyword_coverage"):
        result["keyword_coverage"] = keyword_overlap(resume_text, job_description)

    print_report(result, args.job and job_description, resume_text)
    with open("report.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(f"\nFull JSON report saved to report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
