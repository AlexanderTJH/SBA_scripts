import json
import os
import urllib.request

EU_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA"

KEYWORDS = [
    "privacy", "anonymisation", "anonymization", "synthetic data", "federated learning",
    "differential privacy", "homomorphic encryption", "adversarial", "poisoning",
    "intrusion detection", "anomaly detection", "trustworthy ai", "cybersecurity", "security"
]

def fetch_eu_calls():
    # Use generic search terms in the request to broaden raw matches from EU server
    payload = json.dumps({
        "query": "security OR privacy OR artificial intelligence",
        "bool": {
            "must": [
                {"terms": {"type": ["1"]}}, # 1 = Grants / Calls for Proposals
                {"terms": {"status": ["31094501", "31094502"]}} # Open & Forthcoming
            ]
        },
        "pageSize": 100
    }).encode('utf-8')

    req = urllib.request.Request(
        EU_API_URL, 
        data=payload, 
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error querying EU API: {e}")
        return []

    matched_calls = []
    # Results are usually inside 'results' or 'items'
    items = res_data.get('results', []) or res_data.get('items', [])
    
    for item in items:
        # Recursively stringify the whole item dict to catch terms anywhere in nested fields
        full_text = json.dumps(item).lower()
        found_kw = [kw for kw in KEYWORDS if kw in full_text]
        
        if found_kw:
            title = item.get('title') or item.get('callTitle') or 'EU Funding Opportunity'
            topic_id = item.get('callIdentifier') or item.get('identifier') or 'N/A'
            deadline = item.get('deadlineDate') or item.get('plannedOpeningDate') or 'TBA'
            
            matched_calls.append({
                "Title": str(title)[:250],
                "TopicID": str(topic_id),
                "Deadline": str(deadline),
                "Status": "Open" if "31094501" in str(item.get('status', '')) else "Forthcoming",
                "MatchedKeywords": ", ".join(list(set(found_kw))),
                "Programme": item.get('programmePeriod', 'Horizon Europe'),
                "Url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{str(topic_id).lower()}"
            })

    return matched_calls

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    calls_data = fetch_eu_calls()
    with open("data/eu_calls.json", "w") as f:
        json.dump(calls_data, f, indent=2)
    print(f"Saved {len(calls_data)} EU calls to data/eu_calls.json")