import json
import os
import urllib.request

EU_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA"

KEYWORDS = [
    "anonymisation", "anonymization", "synthetic data", "federated learning",
    "differential privacy", "homomorphic encryption", "privacy enhancing",
    "adversarial", "poisoning", "intrusion detection", "anomaly detection",
    "trustworthy ai", "robust ai"
]

def fetch_eu_calls():
    payload = json.dumps({
        "bool": {
            "must": [
                {"terms": {"type": ["1"]}},
                {"terms": {"status": ["31094501", "31094502"]}} # Open & Forthcoming
            ]
        }
    }).encode('utf-8')

    req = urllib.request.Request(EU_API_URL, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error querying EU API: {e}")
        return []

    matched_calls = []
    for item in res_data.get('results', []):
        text_content = f"{item.get('title', '')} {item.get('teaser', '')} {item.get('description', '')}".lower()
        matched_kw = [kw for kw in KEYWORDS if kw in text_content]
        
        if matched_kw:
            matched_calls.append({
                "Title": item.get('title', 'No Title')[:250],
                "TopicID": item.get('callIdentifier', 'N/A'),
                "Deadline": item.get('deadlineDate', 'TBA'),
                "Status": "Open" if "31094501" in item.get('status', []) else "Forthcoming",
                "MatchedKeywords": ", ".join(matched_kw),
                "Programme": item.get('programmePeriod', 'Horizon Europe'),
                "Url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{item.get('identifier', '').lower()}"
            })
    return matched_calls

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    calls_data = fetch_eu_calls()
    with open("data/eu_calls.json", "w") as f:
        json.dump(calls_data, f, indent=2)
    print(f"Saved {len(calls_data)} EU calls to data/eu_calls.json")