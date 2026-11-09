import json
import os
import urllib.request
import xml.etree.ElementTree as ET

# Official EU Portal XML Feed for Grants & Calls
EU_RSS_URL = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-search;status=31094501,31094502?format=rss"

# Secondary JSON endpoint for direct query fallback
EU_DIRECT_JSON = "https://ec.europa.eu/info/funding-tenders/opportunities/data/referenceData/grants.json"

KEYWORDS = [
    "privacy", "anonymisation", "anonymization", "synthetic data", "federated learning",
    "differential privacy", "homomorphic encryption", "adversarial", "poisoning",
    "intrusion detection", "anomaly detection", "trustworthy ai", "cybersecurity", "security"
]

def fetch_eu_calls():
    matched_calls = []
    
    # Try fetching public RSS/XML feed first
    try:
        req = urllib.request.Request(EU_RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            for item in root.findall('.//item'):
                title = item.findtext('title', '')
                description = item.findtext('description', '')
                link = item.findtext('link', '')

                full_text = f"{title} {description}".lower()
                found_kw = [kw for kw in KEYWORDS if kw in full_text]

                if found_kw:
                    matched_calls.append({
                        "Title": title[:250],
                        "TopicID": link.split('/')[-1] if link else "N/A",
                        "Deadline": "See Call Link",
                        "Status": "Open / Forthcoming",
                        "MatchedKeywords": ", ".join(list(set(found_kw))),
                        "Programme": "Horizon Europe / Digital Europe",
                        "Url": link
                    })
    except Exception as e:
        print(f"RSS feed parsing failed: {e}. Trying fallback...")

    # Fallback: Query simplified JSON catalog if RSS returns empty
    if not matched_calls:
        try:
            req = urllib.request.Request(EU_DIRECT_JSON, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                for item in data.get('topics', []):
                    text = json.dumps(item).lower()
                    found_kw = [kw for kw in KEYWORDS if kw in text]
                    if found_kw:
                        matched_calls.append({
                            "Title": str(item.get('title', 'EU Call'))[:250],
                            "TopicID": str(item.get('identifier', 'N/A')),
                            "Deadline": str(item.get('deadlineDate', 'TBA')),
                            "Status": "Open",
                            "MatchedKeywords": ", ".join(list(set(found_kw))),
                            "Programme": str(item.get('programme', 'Horizon Europe')),
                            "Url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{str(item.get('identifier','')).lower()}"
                        })
        except Exception as e:
            print(f"Fallback JSON query failed: {e}")

    return matched_calls

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    calls_data = fetch_eu_calls()
    with open("data/eu_calls.json", "w", encoding="utf-8") as f:
        json.dump(calls_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(calls_data)} EU calls to data/eu_calls.json")