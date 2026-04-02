import argparse
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


ROOT = Path(__file__).resolve().parent
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
OUT_JSON = ROOT / "data_enriched.json"
OUT_JS = ROOT / "data_enriched.js"
REPORT_JSON = ROOT / "enrichment_report.json"
REPORT_MD = ROOT / "enrichment_report.md"


def now():
    return datetime.now().isoformat(timespec="seconds")


def get_url(url, accept="application/json, text/html", timeout=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": accept,
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type", "")
        body = resp.read()
    return body, content_type


def normalize_text(v):
    text = str(v or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def text_similarity(a, b):
    sa = set(normalize_text(a).split())
    sb = set(normalize_text(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def clean_html_text(text):
    t = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    t = re.sub(r"(?is)<style.*?>.*?</style>", " ", t)
    t = re.sub(r"(?is)<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;|&#160;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"&quot;", "\"", t)
    t = re.sub(r"&apos;", "'", t)
    t = re.sub(r"&lt;", "<", t)
    t = re.sub(r"&gt;", ">", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_meta_abstract(html):
    patterns = [
        r'(?is)<meta[^>]+name=["\']citation_abstract["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+name=["\']dc\.description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+name=["\']twitter:description["\'][^>]+content=["\'](.*?)["\']',
        r'(?is)<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            val = clean_html_text(m.group(1))
            if len(val) > 120:
                return val
    jd = re.findall(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html)
    for block in jd:
        text = block.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except Exception:
            continue
        nodes = obj if isinstance(obj, list) else [obj]
        for n in nodes:
            if isinstance(n, dict):
                for key in ("description", "abstract"):
                    if key in n and isinstance(n[key], str):
                        val = clean_html_text(n[key])
                        if len(val) > 120:
                            return val
    block_patterns = [
        r'(?is)<section[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</section>',
        r'(?is)<div[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</div>',
        r'(?is)<p[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</p>',
    ]
    for p in block_patterns:
        m = re.search(p, html)
        if m:
            val = clean_html_text(m.group(1))
            if len(val) > 120:
                return val
    return ""


def fetch_crossref_candidates(title, journal, year, rows=8):
    q = quote_plus(f"{title} {journal} {year}")
    url = f"https://api.crossref.org/works?query.bibliographic={q}&rows={rows}"
    try:
        body, ctype = get_url(url, accept="application/json")
    except Exception:
        return []
    if "json" not in ctype:
        return []
    try:
        payload = json.loads(body.decode("utf-8", errors="ignore"))
    except Exception:
        return []
    items = payload.get("message", {}).get("items", [])
    out = []
    for it in items:
        t = (it.get("title") or [""])[0]
        j = (it.get("container-title") or [""])[0]
        doi = it.get("DOI", "")
        y = None
        issued = it.get("issued", {}).get("date-parts", [])
        if issued and issued[0]:
            y = issued[0][0]
        score = 0.7 * text_similarity(t, title) + 0.2 * text_similarity(j, journal)
        if y is not None and str(y) == str(year):
            score += 0.2
        out.append({"title": t, "journal": j, "doi": doi, "year": y, "score": score})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def fetch_abstract_from_doi(doi):
    doi_url = f"https://doi.org/{doi}"
    try:
        body, ctype = get_url(doi_url, accept="text/html,application/xhtml+xml")
    except (HTTPError, URLError, TimeoutError, ConnectionResetError, OSError, Exception):
        return "", doi_url, ""
    html = body.decode("utf-8", errors="ignore")
    abstract = extract_meta_abstract(html)
    return abstract, doi_url, ctype


def openalex_inverted_to_text(inverted):
    if not isinstance(inverted, dict) or not inverted:
        return ""
    pos_words = []
    for w, poses in inverted.items():
        if not isinstance(poses, list):
            continue
        for p in poses:
            if isinstance(p, int):
                pos_words.append((p, w))
    if not pos_words:
        return ""
    pos_words.sort(key=lambda x: x[0])
    text = " ".join([w for _, w in pos_words]).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def fetch_abstract_from_openalex(doi):
    doi_id = quote_plus(f"https://doi.org/{doi}")
    url = f"https://api.openalex.org/works/{doi_id}"
    try:
        body, ctype = get_url(url, accept="application/json")
    except Exception:
        return "", url
    if "json" not in ctype:
        return "", url
    try:
        obj = json.loads(body.decode("utf-8", errors="ignore"))
    except Exception:
        return "", url
    inv = obj.get("abstract_inverted_index")
    text = openalex_inverted_to_text(inv)
    if len(text) > 120:
        return text, url
    return "", url


def enrich_records(records, max_records=0, sleep_sec=0.8):
    missing_idx = [i for i, r in enumerate(records) if not str(r.get("Abstract", "")).strip()]
    if max_records and max_records > 0:
        missing_idx = missing_idx[:max_records]
    result = {
        "started_at": now(),
        "target_missing_count": len([r for r in records if not str(r.get("Abstract", "")).strip()]),
        "processed_count": len(missing_idx),
        "updated_count": 0,
        "failed_count": 0,
        "updated_examples": [],
        "failed_examples": [],
    }
    for i, idx in enumerate(missing_idx, start=1):
        row = records[idx]
        title = row.get("Article Title", "")
        journal = row.get("Source Title", "")
        year = row.get("Publication Year", "")
        candidates = fetch_crossref_candidates(title, journal, year)
        chosen = candidates[0] if candidates else None
        if not chosen or not chosen.get("doi") or chosen["score"] < 0.45:
            result["failed_count"] += 1
            if len(result["failed_examples"]) < 30:
                result["failed_examples"].append(
                    {"index": idx, "title": title, "journal": journal, "year": year, "reason": "未找到可信 DOI 候选"}
                )
            continue
        abstract, source_url, _ = fetch_abstract_from_doi(chosen["doi"])
        source_kind = "journal_landing_page"
        if not abstract:
            abstract, source_url = fetch_abstract_from_openalex(chosen["doi"])
            source_kind = "openalex_by_doi"
        if abstract and len(abstract) > 120:
            row["Abstract"] = abstract
            row["Data Enrichment Source"] = source_url
            row["Data Enrichment DOI"] = chosen["doi"]
            row["Data Enrichment Method"] = source_kind
            result["updated_count"] += 1
            if len(result["updated_examples"]) < 30:
                result["updated_examples"].append(
                    {
                        "index": idx,
                        "title": title,
                        "journal": journal,
                        "year": year,
                        "doi": chosen["doi"],
                        "source_url": source_url,
                        "source_kind": source_kind,
                        "score": round(chosen["score"], 3),
                    }
                )
        else:
            result["failed_count"] += 1
            if len(result["failed_examples"]) < 30:
                result["failed_examples"].append(
                    {
                        "index": idx,
                        "title": title,
                        "journal": journal,
                        "year": year,
                        "doi": chosen["doi"],
                        "reason": "官网落地页未提取到可用摘要",
                    }
                )
        if i % 25 == 0:
            print(f"Processed {i}/{len(missing_idx)} | updated={result['updated_count']} failed={result['failed_count']}")
        time.sleep(sleep_sec + random.random() * 0.4)
    result["finished_at"] = now()
    result["remaining_missing_count"] = len([r for r in records if not str(r.get("Abstract", "")).strip()])
    return result


def write_outputs(records, report):
    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_JS.write_text("const DATA = " + json.dumps(records, ensure_ascii=False, indent=2) + ";", encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 官网补全报告",
        "",
        f"- 开始时间: {report['started_at']}",
        f"- 结束时间: {report['finished_at']}",
        f"- 初始缺失摘要: {report['target_missing_count']}",
        f"- 本轮处理记录: {report['processed_count']}",
        f"- 本轮补全成功: {report['updated_count']}",
        f"- 本轮补全失败: {report['failed_count']}",
        f"- 当前剩余缺失摘要: {report['remaining_missing_count']}",
        "",
        "## 成功样例（最多30条）",
        "",
    ]
    if report["updated_examples"]:
        for x in report["updated_examples"]:
            lines.append(f"- [{x['journal']}|{x['year']}] {x['title']} | DOI={x['doi']} | score={x['score']}")
    else:
        lines.append("- 无")
    lines += ["", "## 失败样例（最多30条）", ""]
    if report["failed_examples"]:
        for x in report["failed_examples"]:
            lines.append(f"- [{x['journal']}|{x['year']}] {x['title']} | {x['reason']}")
    else:
        lines.append("- 无")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    records = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    report = enrich_records(records, max_records=args.limit, sleep_sec=args.sleep)
    write_outputs(records, report)
    if args.overwrite:
        DATA_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        DATA_JS.write_text("const DATA = " + json.dumps(records, ensure_ascii=False, indent=2) + ";", encoding="utf-8")
    print(json.dumps({
        "updated_count": report["updated_count"],
        "failed_count": report["failed_count"],
        "remaining_missing_count": report["remaining_missing_count"],
        "output_json": str(OUT_JSON.name),
        "output_js": str(OUT_JS.name),
        "report_json": str(REPORT_JSON.name),
        "report_md": str(REPORT_MD.name),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
