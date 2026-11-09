import json
import os
import urllib.request
import yaml

# Source: Open security deadlines repo
YAML_URL = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/master/_data/conferences.yml"

# MLDM Target Conferences
TARGET_CONFS = {"PETS", "IEEE S&P", "USENIX Security", "ACM CCS", "NDSS", "EuroS&P", "ESORICS", "ARES", "NeurIPS", "ICML", "ICLR", "AAAI", "CD-MAKE"}

def fetch_conferences():
    req = urllib.request.Request(YAML_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = yaml.safe_load(response.read())

    results = []
    for conf in data:
        title = conf.get('title', '')
        if any(tc.lower() in title.lower() for tc in TARGET_CONFS):
            # Extract main deadline year/info
            for cycle in conf.get('deadlines', []):
                results.append({
                    "Title": f"{title} {cycle.get('year', '')}",
                    "Deadline": cycle.get('deadline', 'TBA'),
                    "AbstractDeadline": cycle.get('abstract_deadline', 'N/A'),
                    "Location": conf.get('place', 'TBA'),
                    "Category": conf.get('sub', 'Security/Privacy'),
                    "Url": conf.get('link', '')
                })
    return results

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conf_data = fetch_conferences()
    with open("data/conferences.json", "w") as f:
        json.dump(conf_data, f, indent=2)
    print(f"Saved {len(conf_data)} conferences to data/conferences.json")