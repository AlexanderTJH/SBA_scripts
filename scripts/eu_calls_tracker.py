import json
import os
import urllib.parse
import urllib.request

# Official European Commission SEDIA Search REST API endpoint
API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text=***&pageSize=200&pageNumber=1"

# MLDM Topic Keywords
KEYWORDS = [
    "privacy", "anonymisation", "anonymization", "synthetic data", "federated learning",
    "differential privacy", "homomorphic encryption", "adversarial", "poisoning",
    "intrusion detection", "anomaly detection", "trustworthy ai", "cybersecurity", "security", "AI models"
]

def extract_field(item, keys, default="N/A"):
    """Safely extract field values from root or nested metadata dicts."""
    for k in keys:
        if k in item and item[k]:
            val = item[k]
            return val[0] if isinstance(val, list) else str(val)
    meta = item.get('metadata', {})
    if isinstance(meta, dict):
        for k in keys:
            if k in meta and meta[k]:
                val = meta[k]
                return val[0] if isinstance(val, list) else str(val)
    return default

def fetch_eu_calls():
    # Construct required form parameters for SEDIA API query
    query_dict = {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "2"]}}, # 1 = Grants / Calls for Proposals, 2 = Tenders
                {"terms": {"status": ["31094501", "31094502"]}} # 31094501 = Open, 31094502 = Forthcoming
            ]
        }
    }
    sort_dict = {"order": "DESC", "field": "startDate"}

    form_data = urllib.parse.urlencode({
        "query": json.dumps(query_dict),
        "sort": json.dumps(sort_dict)
    }).encode('utf-8')

    req = urllib.request.Request(
        API_URL,
        data=form_data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
    )

    matched_calls = []
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            results = res_data.get('results', [])

            for item in results:
                # Stringify entire item JSON to check for keyword matches across all description fields
                full_text = json.dumps(item).lower()
                found_kw = [kw for kw in KEYWORDS if kw in full_text]

                if found_kw:
                    title = extract_field(item, ['title', 'callTitle'], 'EU Funding Call')
                    topic_id = extract_field(item, ['callIdentifier', 'identifier', 'rcn'], 'N/A')
                    deadline = extract_field(item, ['deadlineDate', 'plannedOpeningDate'], 'See Call Page')
                    status_raw = extract_field(item, ['status', 'statusCode'], '')

                    clean_id = str(topic_id).strip()
                    url = f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{clean_id.lower()}" if clean_id != 'N/A' else "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-for-proposals"

                    matched_calls.append({
                        "Title": str(title)[:250],
                        "TopicID": str(topic_id),
                        "Deadline": str(deadline),
                        "Status": "Open" if "31094501" in str(status_raw) else "Forthcoming",
                        "MatchedKeywords": ", ".join(list(set(found_kw))),
                        "Programme": "Horizon Europe / EU Funding",
                        "Url": url
                    })
    except Exception as e:
        print(f"Error fetching EU calls: {e}")

    return matched_calls

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    calls_data = fetch_eu_calls()
    with open("data/eu_calls.json", "w", encoding="utf-8") as f:
        json.dump(calls_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(calls_data)} EU calls to data/eu_calls.json")