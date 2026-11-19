from datetime import date, datetime, timezone
import json
import os
import re
import urllib.request
import yaml

SEC_URL = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/master/_data/conferences.yml"
AI_URL = "https://raw.githubusercontent.com/paperswithcode/ai-deadlines/gh-pages/_data/conferences.yml"

KEYWORDS = [
    "privacy", "anonymisation", "anonymization", "synthetic data", "federated learning",
    "differential privacy", "homomorphic encryption", "cryptography",
    "adversarial", "poisoning", "backdoor", "trustworthy ai", "robust ai",
    "intrusion detection", "anomaly detection", "cybersecurity", "security",
    "machine learning", "data management", "artificial intelligence", "ai"
]

EXCLUDED_FIELDS = {
    "link", "dblp", "place", "location", "timezone", "date", "deadline",
    "abstract_deadline", "start", "end", "year", "hindex"
}

def parse_yaml(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return yaml.safe_load(content) or []
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def parse_deadline_date(raw_deadline):
    """Convert YAML date/datetime/string into a Python date object, or None if unparseable."""
    if not raw_deadline:
        return None
    if isinstance(raw_deadline, datetime):
        return raw_deadline.date()
    if isinstance(raw_deadline, date):
        return raw_deadline

    match = re.search(r"(\d{4}-\d{2}-\d{2})", str(raw_deadline))
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None

def find_matched_keywords(conf):
    """Scan all descriptive YAML fields for MLDM keywords using word boundaries."""
    if not isinstance(conf, dict):
        return []

    text_parts = []
    for key, value in conf.items():
        if key in EXCLUDED_FIELDS or value is None:
            continue
        if isinstance(value, list):
            text_parts.extend(str(v) for v in value)
        elif not isinstance(value, dict):
            text_parts.append(str(value))

    searchable_text = " ".join(text_parts).lower()

    matched = [
        kw for kw in KEYWORDS
        if re.search(rf"\b{re.escape(kw)}\b", searchable_text)
    ]
    return sorted(set(matched))

def normalize_cycles(conf):
    """Normalize both ai-deadlines ('deadlines') and sec-deadlines ('deadline' list) schemas."""
    deadlines = conf.get("deadlines")
    if isinstance(deadlines, list) and deadlines:
        return deadlines

    raw_dl = conf.get("deadline") or conf.get("date")
    raw_abs = conf.get("abstract_deadline")
    year = conf.get("year", "")

    # sec-deadlines stores deadline (and optionally abstract_deadline) as a list of strings
    if isinstance(raw_dl, list):
        cycles = []
        for idx, dl_item in enumerate(raw_dl):
            abs_item = (
                raw_abs[idx]
                if isinstance(raw_abs, list) and idx < len(raw_abs)
                else (raw_abs if raw_abs and not isinstance(raw_abs, list) else "N/A")
            )
            cycles.append({
                "deadline": dl_item,
                "abstract_deadline": abs_item,
                "year": year
            })
        return cycles

    return [{
        "deadline": raw_dl,
        "abstract_deadline": raw_abs or "N/A",
        "year": year
    }]

def extract_category(conf):
    """Use 'sub' (ai-deadlines) or 'tags' (sec-deadlines) for Category."""
    if conf.get("sub"):
        return str(conf["sub"]).strip()
    tags = conf.get("tags")
    if isinstance(tags, list) and tags:
        return ", ".join(str(t).strip() for t in tags)
    return "Security/AI"

def fetch_all_conferences():
    sec_data = parse_yaml(SEC_URL)
    ai_data = parse_yaml(AI_URL)
    all_raw = sec_data + ai_data

    today = datetime.now(timezone.utc).date()
    results = []
    seen = set()

    matched_conf_count = 0
    skipped_past = 0
    skipped_unparseable = 0

    for conf in all_raw:
        matched_kw = find_matched_keywords(conf)
        if not matched_kw:
            continue
        matched_conf_count += 1

        # sec-deadlines uses 'name'; ai-deadlines uses 'title'
        conf_name = str(conf.get("name") or conf.get("title") or "Unknown Conference").strip()
        category = extract_category(conf)
        cycles = normalize_cycles(conf)

        for cycle in cycles:
            if isinstance(cycle, dict):
                raw_deadline = cycle.get("deadline") or cycle.get("date") or conf.get("deadline") or conf.get("date")
                abstract_dl = cycle.get("abstract_deadline") or cycle.get("abstract") or "N/A"
                year_val = cycle.get("year") or conf.get("year")
                cycle_type = str(cycle.get("type") or cycle.get("round") or "").strip()
            else:
                raw_deadline = cycle
                abstract_dl = "N/A"
                year_val = conf.get("year")
                cycle_type = ""

            deadline_dt = parse_deadline_date(raw_deadline)
            if deadline_dt is None:
                skipped_unparseable += 1
                continue
            if deadline_dt < today:
                skipped_past += 1
                continue

            year = year_val or deadline_dt.year
            suffix = f" ({cycle_type})" if cycle_type else ""
            entry_title = f"{conf_name} {year}{suffix}".strip()
            deadline_str = str(raw_deadline).strip()

            dedup_key = (entry_title, deadline_str)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            results.append({
                "Title": entry_title,
                "Deadline": deadline_str,
                "AbstractDeadline": str(abstract_dl).strip(),
                "Location": str(conf.get("place", conf.get("location", "TBA"))).strip(),
                "Category": category,
                "MatchedKeywords": ", ".join(matched_kw),
                "Url": str(conf.get("link", "")).strip()
            })

    results.sort(key=lambda x: str(parse_deadline_date(x["Deadline"])))
    print(
        f"Total fetched: {len(all_raw)} | Matched by keywords: {matched_conf_count} | "
        f"Skipped (past): {skipped_past} | Skipped (no/TBA date): {skipped_unparseable}"
    )
    return results

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conf_data = fetch_all_conferences()
    with open("data/conferences.json", "w", encoding="utf-8") as f:
        json.dump(conf_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(conf_data)} upcoming conferences to data/conferences.json")
