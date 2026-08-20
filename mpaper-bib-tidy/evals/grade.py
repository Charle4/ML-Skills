#!/usr/bin/env python3
"""Grade mpaper-bib-tidy benchmark outputs against the current tier boundaries.

Usage: grade.py <iteration-dir>   e.g. grade.py iteration-2
"""

import json
import re
import sys
from pathlib import Path


def has_field(bib: str, field: str) -> bool:
    return bool(re.search(rf"^\s*{re.escape(field)}\s*=", bib, re.MULTILINE | re.IGNORECASE))


def all_pages_double_dash(bib: str) -> bool:
    for value in re.findall(r"^\s*pages\s*=\s*\{?([^},]+)", bib, re.MULTILINE | re.IGNORECASE):
        if "-" in value and "--" not in value:
            return False
    return True


def all_authors_last_first(bib: str) -> bool:
    for value in re.findall(r"^\s*author\s*=\s*\{(.*)\}\s*,?$", bib, re.MULTILINE | re.IGNORECASE):
        if value.strip().lower().endswith(" and others"):
            continue
        for name in value.split(" and "):
            name = name.strip()
            if name.lower() in {"others", "anonymous"}:
                continue
            if "," not in name:
                return False
    return True


def has_key(bib: str, key: str) -> bool:
    return bool(re.search(r"@\w+\{" + re.escape(key) + r"\s*,", bib, re.IGNORECASE))


def entry_type(bib: str, key: str) -> str:
    match = re.search(r"@(\w+)\{" + re.escape(key) + r"\s*,", bib, re.IGNORECASE)
    return match.group(1).lower() if match else ""


def entry(bib: str, key: str) -> str:
    match = re.search(r"@\w+\{" + re.escape(key) + r"\s*,(.*?)(?=\n@|\Z)", bib, re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else ""


def field_value(bib: str, key: str, field: str) -> str:
    match = re.search(
        rf"^\s*{re.escape(field)}\s*=\s*(.+?)(?:,\s*$|$)",
        entry(bib, key),
        re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def title_has(bib: str, key: str, term: str) -> bool:
    return "{" + term + "}" in field_value(bib, key, "title")


def summary_mentions(summary: str, text: str) -> bool:
    return text.lower() in summary.lower()


def shared_checks(bib: str, keys: list[str]) -> list[dict]:
    return [
        check("No doi fields remain", not has_field(bib, "doi")),
        check("No url fields remain", not has_field(bib, "url")),
        check("No month fields remain", not has_field(bib, "month")),
        check("No address fields remain", not has_field(bib, "address")),
        check("All pages use double dash", all_pages_double_dash(bib)),
        check("All author fields use Last, First", all_authors_last_first(bib)),
        check("All original citation keys remain", all(has_key(bib, key) for key in keys)),
    ]


def check(text: str, passed: bool, evidence: str = "") -> dict:
    return {"text": text, "passed": passed, "evidence": evidence or ("passed" if passed else "failed")}


def grade_fullname(bib: str, summary: str) -> list[dict]:
    keys = [
        "zhang2021plug", "liang2021swinir", "romano2017little", "chen2022learning",
        "venkatakrishnan2013pnp", "hurault2022proximal", "wang2024sinsr", "scholkopf2002learning",
    ]
    checks = shared_checks(bib, keys)
    checks.extend([
        check("Full-name venue is recased without word substitution", "SIAM Journal on Imaging Sciences" in field_value(bib, "romano2017little", "journal")),
        check("Flattened model name SwinIR is brace-protected", title_has(bib, "liang2021swinir", "SwinIR")),
        check("Incomplete author list is preserved", "others" in field_value(bib, "wang2024sinsr", "author").lower()),
        check("Conference candidate was not dropped", has_key(bib, "venkatakrishnan2013pnp")),
    ])
    return checks


def grade_string(bib: str, summary: str) -> list[dict]:
    keys = [
        "zhang2017learning", "lim2017enhanced", "zhang2022practical", "wang2021real",
        "ho2020denoising", "elad2023image", "dosovitskiy2021image",
    ]
    checks = shared_checks(bib, keys)
    checks.extend([
        check("String definitions remain", "@String(" in bib),
        check("Exact @String match uses PAMI", field_value(bib, "zhang2022practical", "journal") == "PAMI"),
        check("Exact @String match uses NeurIPS", field_value(bib, "ho2020denoising", "booktitle") == "NeurIPS"),
        check("Exact @String match uses ICLR", field_value(bib, "dosovitskiy2021image", "booktitle") == "ICLR"),
        check("Unlisted full journal is recased", "SIAM Journal on Imaging Sciences" in field_value(bib, "elad2023image", "journal")),
        check("Flattened CNN is brace-protected", title_has(bib, "zhang2017learning", "CNN")),
        check("Flattened Real-ESRGAN is brace-protected", title_has(bib, "wang2021real", "Real-ESRGAN")),
        check("Conference candidate is retained", has_key(bib, "zhang2017learning")),
    ])
    return checks


def grade_ltwa(bib: str, summary: str) -> list[dict]:
    keys = [
        "candes2006robust", "rudin1992nonlinear", "chambolle2004algorithm",
        "beck2009fast", "boyd2011distributed", "chan1998total", "goldstein2009split",
    ]
    checks = shared_checks(bib, keys)
    checks.extend([
        check("Trademark symbol is removed", "textregistered" not in bib),
        check("Bregman method name is brace-protected", any(
            protected in field_value(bib, "goldstein2009split", "title")
            for protected in ("{Bregman}", "{Split Bregman}")
        )),
        check("L1 is brace-protected", title_has(bib, "goldstein2009split", "L1")),
        check("All original LTWA-mode venues remain present", all(has_key(bib, key) for key in keys)),
        check("Boyd entry remains present", has_key(bib, "boyd2011distributed")),
    ])
    return checks


def grade_real_string(bib: str, summary: str) -> list[dict]:
    keys = [
        "kupyn2018deblurgan", "pan2014deblurring", "oquab2024dinov", "wipf2014revisiting",
        "radford2021learning", "tschannen2025siglip2", "ravi2025sam", "Huo2023blind",
    ]
    checks = shared_checks(bib, keys)
    checks.extend([
        check("String definitions remain", "@String(" in bib),
        check("Exact CVPR value maps to CVPR", field_value(bib, "kupyn2018deblurgan", "booktitle") == "CVPR"),
        check("Exact TMLR value maps to TMLR", field_value(bib, "oquab2024dinov", "journal") == "TMLR"),
        check("Exact ICML value maps to ICML", field_value(bib, "radford2021learning", "booktitle") == "ICML"),
        check("Exact ICLR value maps to ICLR", field_value(bib, "ravi2025sam", "booktitle") == "ICLR"),
        check("Exact PAMI value maps to PAMI", field_value(bib, "Huo2023blind", "journal") == "PAMI"),
        check("Flattened DeblurGAN is brace-protected", title_has(bib, "kupyn2018deblurgan", "DeblurGAN")),
        check("Flattened L0 is brace-protected", title_has(bib, "pan2014deblurring", "L0")),
        check("Flattened DINOv2 restores conventional capitalization", any(
            protected in field_value(bib, "oquab2024dinov", "title")
            for protected in ("{DINO}v2", "{DINOv2}")
        )),
        check("Flattened SigLIP is brace-protected", title_has(bib, "tschannen2025siglip2", "SigLIP")),
        check("Flattened SAM is brace-protected", title_has(bib, "ravi2025sam", "SAM")),
        check("Flattened Bayesian is brace-protected", title_has(bib, "wipf2014revisiting", "Bayesian")),
        check("Incomplete author list remains", "others" in field_value(bib, "radford2021learning", "author").lower()),
    ])
    return checks


def grade_run(eval_name: str, bib: str, summary: str) -> list[dict]:
    if eval_name == "eval-1-fullname":
        return grade_fullname(bib, summary)
    if eval_name == "eval-2-string":
        return grade_string(bib, summary)
    if eval_name == "eval-3-ltwa":
        return grade_ltwa(bib, summary)
    if eval_name == "eval-4-real-string":
        return grade_real_string(bib, summary)
    raise ValueError(eval_name)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: grade.py <iteration-dir>")
    base = Path(sys.argv[1])
    for eval_dir in sorted(base.glob("eval-*")):
        for config_dir in sorted(path for path in eval_dir.iterdir() if path.is_dir()):
            output_dir = config_dir / "outputs"
            bib_path = output_dir / "result.bib"
            if not bib_path.exists():
                print(f"SKIP {eval_dir.name}/{config_dir.name}: no result.bib")
                continue
            summary_path = output_dir / "summary.md"
            summary = summary_path.read_text() if summary_path.exists() else ""
            checks = grade_run(eval_dir.name, bib_path.read_text(), summary)
            passed = sum(item["passed"] for item in checks)
            grading = {
                "expectations": checks,
                "summary": {
                    "passed": passed,
                    "failed": len(checks) - passed,
                    "total": len(checks),
                    "pass_rate": round(passed / len(checks), 2),
                },
            }
            (config_dir / "grading.json").write_text(json.dumps(grading, indent=2) + "\n")
            print(f"{eval_dir.name}/{config_dir.name}: {passed}/{len(checks)} ({passed / len(checks):.0%})")


if __name__ == "__main__":
    main()
