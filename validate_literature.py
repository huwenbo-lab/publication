import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
REPORT_JSON = ROOT / "validation_report.json"
REPORT_MD = ROOT / "validation_report.md"
REQUIRED_FIELDS = ["Source Title", "Publication Year", "Article Title", "Author Full Names", "Abstract"]
YEAR_MIN = 2015
YEAR_MAX = 2025


def load_data_json():
    with DATA_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("data.json 不是数组格式")
    return data


def load_data_js():
    raw = DATA_JS.read_text(encoding="utf-8").strip()
    match = re.search(r"const\s+DATA\s*=\s*(\[.*\])\s*;?\s*$", raw, re.S)
    if not match:
        raise ValueError("data.js 中未找到 const DATA = [...] 结构")
    data = json.loads(match.group(1))
    if not isinstance(data, list):
        raise ValueError("data.js 不是数组格式")
    return data


def normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def validate_records(records):
    missing_counter = Counter()
    empty_counter = Counter()
    invalid_year = []
    duplicates = []
    seen = set()
    journals = Counter()
    years = Counter()
    journal_year_counts = defaultdict(int)

    for idx, item in enumerate(records):
        for field in REQUIRED_FIELDS:
            if field not in item:
                missing_counter[field] += 1
            elif str(item[field]).strip() == "":
                empty_counter[field] += 1

        year_raw = item.get("Publication Year")
        year = None
        try:
            year = int(year_raw)
        except Exception:
            invalid_year.append({"index": idx, "value": year_raw, "reason": "非整数年份"})
        else:
            if year < YEAR_MIN or year > YEAR_MAX:
                invalid_year.append({"index": idx, "value": year, "reason": "超出范围"})
            years[year] += 1

        journal = str(item.get("Source Title", "")).strip()
        title = str(item.get("Article Title", "")).strip()
        if journal:
            journals[journal] += 1
        if journal and year is not None:
            journal_year_counts[(journal, year)] += 1

        dup_key = (
            normalize_text(journal),
            normalize_text(title),
            str(year if year is not None else ""),
            normalize_text(item.get("Author Full Names", "")),
        )
        if dup_key in seen:
            duplicates.append(
                {
                    "index": idx,
                    "journal": journal,
                    "year": year,
                    "title": title[:200],
                }
            )
        else:
            seen.add(dup_key)

    return {
        "total_records": len(records),
        "missing_fields": dict(missing_counter),
        "empty_fields": dict(empty_counter),
        "invalid_year_records": invalid_year,
        "duplicate_records": duplicates,
        "journal_count": len(journals),
        "year_distribution": dict(sorted(years.items(), key=lambda x: x[0])),
        "top_journals_by_count": journals.most_common(20),
        "top_journal_year_pairs": sorted(
            [{"journal": j, "year": y, "count": c} for (j, y), c in journal_year_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:20],
    }


def compare_json_js(json_records, js_records):
    if len(json_records) != len(js_records):
        return {
            "same_length": False,
            "json_length": len(json_records),
            "js_length": len(js_records),
            "same_content_fingerprint": False,
        }

    def fingerprint(rows):
        arr = []
        for row in rows:
            arr.append(
                (
                    normalize_text(row.get("Source Title", "")),
                    normalize_text(row.get("Publication Year", "")),
                    normalize_text(row.get("Article Title", "")),
                    normalize_text(row.get("Author Full Names", "")),
                    normalize_text(row.get("Abstract", "")),
                )
            )
        arr.sort()
        return hash(tuple(arr))

    fp_json = fingerprint(json_records)
    fp_js = fingerprint(js_records)
    return {
        "same_length": True,
        "json_length": len(json_records),
        "js_length": len(js_records),
        "same_content_fingerprint": fp_json == fp_js,
    }


def build_summary(report):
    missing_total = sum(report["quality"]["missing_fields"].values())
    empty_total = sum(report["quality"]["empty_fields"].values())
    invalid_year_total = len(report["quality"]["invalid_year_records"])
    duplicate_total = len(report["quality"]["duplicate_records"])
    js_sync = report["consistency"]["same_content_fingerprint"]
    return {
        "overall_pass": missing_total == 0 and invalid_year_total == 0 and js_sync,
        "missing_total": missing_total,
        "empty_total": empty_total,
        "invalid_year_total": invalid_year_total,
        "duplicate_total": duplicate_total,
        "js_sync_ok": js_sync,
    }


def write_markdown(report):
    s = report["summary"]
    q = report["quality"]
    c = report["consistency"]
    lines = [
        "# 文献数据校验报告",
        "",
        f"- 生成时间: {report['generated_at']}",
        f"- 总记录数: {q['total_records']}",
        f"- 期刊数量: {q['journal_count']}",
        f"- 年份范围: {YEAR_MIN}-{YEAR_MAX}",
        "",
        "## 总体结论",
        "",
        f"- 校验通过: {'是' if s['overall_pass'] else '否'}",
        f"- 缺失字段数: {s['missing_total']}",
        f"- 空值字段数: {s['empty_total']}",
        f"- 非法年份记录数: {s['invalid_year_total']}",
        f"- 重复记录数: {s['duplicate_total']}",
        f"- data.json 与 data.js 一致: {'是' if s['js_sync_ok'] else '否'}",
        "",
        "## 字段缺失统计",
        "",
    ]
    if q["missing_fields"]:
        for k, v in q["missing_fields"].items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- 无")

    lines += ["", "## 字段空值统计", ""]
    if q["empty_fields"]:
        for k, v in q["empty_fields"].items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- 无")

    lines += ["", "## data.json / data.js 一致性", ""]
    lines += [
        f"- 长度一致: {'是' if c['same_length'] else '否'}",
        f"- data.json 条数: {c['json_length']}",
        f"- data.js 条数: {c['js_length']}",
        f"- 指纹一致: {'是' if c['same_content_fingerprint'] else '否'}",
    ]

    lines += ["", "## 年份分布", ""]
    for year, count in q["year_distribution"].items():
        lines.append(f"- {year}: {count}")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    json_records = load_data_json()
    js_records = load_data_js()
    quality = validate_records(json_records)
    consistency = compare_json_js(json_records, js_records)
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "quality": quality,
        "consistency": consistency,
    }
    report["summary"] = build_summary(report)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report)
    print(f"校验完成: {REPORT_JSON.name}, {REPORT_MD.name}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
