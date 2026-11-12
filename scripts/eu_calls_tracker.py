import html
import json
import os
import re
import requests

SEARCH_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
FACET_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/facet"

KEYWORDS = [
    "privacy", "anonymisation", "anonymization", "synthetic data", "federated learning",
    "differential privacy", "homomorphic encryption", "adversarial", "poisoning",
    "intrusion detection", "anomaly detection", "trustworthy ai", "cybersecurity",
    "security", "ai models"
]

def clean_html(raw_text):
    """Strip HTML tags, decode entities (&nbsp;), and normalize whitespace."""
    if not raw_text:
        return ""
    unescaped = html.unescape(str(raw_text))
    no_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", no_tags).strip()

def extract_field(item, keys, default="N/A"):
    """Safely extract field values from root or nested metadata dicts."""
    for k in keys:
        if k in item and item[k]:
            val = item[k]
            return val[0] if isinstance(val, list) else str(val)
    meta = item.get("metadata", {})
    if isinstance(meta, dict):
        for k in keys:
            if k in meta and meta[k]:
                val = meta[k]
                return val[0] if isinstance(val, list) else str(val)
    return default

def fetch_facet_lookup(query_dict):
    """Query the SEDIA Facet API to map numeric reference codes to human-readable labels."""
    lookup = {
        "31094501": "Open",
        "31094502": "Forthcoming",
        "43108390": "Horizon Europe (HORIZON)"
    }

    params = {"apiKey": "SEDIA", "text": "***"}
    files = {
        "query": ("blob", json.dumps(query_dict), "application/json"),
        "languages": ("blob", json.dumps(["en"]), "application/json")
    }

    try:
        response = requests.post(FACET_API_URL, params=params, files=files, timeout=30)
        response.raise_for_status()
        data = response.json()

        for facet in data.get("facets", []):
            for entry in facet.get("values", []):
                code = str(
                    entry.get("rawValue")
                    or entry.get("code")
                    or entry.get("id")
                    or ""
                ).strip()
                label = str(
                    entry.get("value")
                    or entry.get("description")
                    or entry.get("label")
                    or ""
                ).strip()
                if code and label:
                    lookup[code] = label
    except Exception as e:
        print(f"Warning: Facet API lookup failed, using fallback labels ({e})")

    return lookup

def fetch_eu_calls():
    # Types 1 (Topics), 2 (General Calls), 8 (Cascade Funding) | Status: Open & Forthcoming
    query_dict = {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "2", "8"]}},
                {"terms": {"status": ["31094501", "31094502"]}}
            ]
        }
    }
    sort_dict = {"field": "startDate", "order": "DESC"}

    # Step 1: Fetch reference code translations from the Facet API
    facet_lookup = fetch_facet_lookup(query_dict)

    # Step 2: Fetch matching calls from the Search API
    matched_calls = []
    seen_ids = set()
    page = 1
    page_size = 100

    while True:
        params = {
            "apiKey": "SEDIA",
            "text": "***",
            "pageSize": str(page_size),
            "pageNumber": str(page)
        }
        files = {
            "query": ("blob", json.dumps(query_dict), "application/json"),
            "languages": ("blob", json.dumps(["en"]), "application/json"),
            "sort": ("blob", json.dumps(sort_dict), "application/json")
        }

        try:
            response = requests.post(SEARCH_API_URL, params=params, files=files, timeout=30)
            response.raise_for_status()
            res_data = response.json()
        except Exception as e:
            print(f"Error fetching EU calls on page {page}: {e}")
            break

        results = res_data.get("results", [])
        if not results:
            break

        for item in results:
            # Enforce English-only records
            lang = extract_field(item, ["language"], "en").lower()
            if lang != "en":
                continue

            meta = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}

            # Search across Title, Summary, Content, Keywords, and cleaned Topic Description
            raw_sections = [
                item.get("title", ""),
                item.get("summary", ""),
                item.get("content", ""),
                json.dumps(meta.get("title", "")),
                json.dumps(meta.get("keywords", "")),
                json.dumps(meta.get("descriptionByte", ""))
            ]
            searchable_text = clean_html(" ".join(str(s) for s in raw_sections)).lower()

            found_kw = [kw for kw in KEYWORDS if kw in searchable_text]
            if not found_kw:
                continue

            topic_id = extract_field(item, ["identifier", "callIdentifier", "rcn"], "N/A").strip()
            if topic_id in seen_ids:
                continue
            seen_ids.add(topic_id)

            title = clean_html(extract_field(item, ["title", "callTitle"], "EU Funding Call"))
            deadline = extract_field(item, ["deadlineDate", "plannedOpeningDate"], "See Call Page")

            # Translate numeric status and frameworkProgramme codes via Facet API lookup
            status_code = extract_field(item, ["status", "statusCode"], "").strip()
            status_label = facet_lookup.get(
                status_code,
                "Open" if "31094501" in status_code else "Forthcoming"
            )

            prog_code = extract_field(item, ["frameworkProgramme"], "").strip()
            programme_label = facet_lookup.get(
                prog_code,
                extract_field(item, ["programmePeriod"], "EU Funding Programme")
            )

            api_url = extract_field(item, ["url"], "")
            if api_url.startswith("http"):
                topic_url = api_url
            elif topic_id != "N/A":
                topic_url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_id.lower()}"
            else:
                topic_url = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-for-proposals"

            matched_calls.append({
                "Title": title[:250],
                "TopicID": topic_id,
                "Deadline": str(deadline),
                "Status": status_label,
                "MatchedKeywords": ", ".join(sorted(set(found_kw))),
                "Programme": programme_label,
                "Url": topic_url
            })

        total_results = res_data.get("totalResults", 0)
        if page * page_size >= total_results:
            break
        page += 1

    return matched_calls

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    calls_data = fetch_eu_calls()
    with open("data/eu_calls.json", "w", encoding="utf-8") as f:
        json.dump(calls_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(calls_data)} EU calls to data/eu_calls.json")