import json
import os
import urllib.request
import yaml

SEC_URL = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/master/_data/conferences.yml"
AI_URL = "https://raw.githubusercontent.com/ai-deadlines/ai-deadlines.github.io/master/_data/conferences.yml"

# Target acronyms / titles
TARGET_CONFS = {"pets", "s&P", "sp", "usenix", "ccs", "ndss", "eurosp", "esorics", "ares", "neurips", "icml", "iclr", "aaai", "ijcai", "kdd", "cd-make"}

def parse_yaml(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return yaml.safe_load(response.read()) or []
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def fetch_all_conferences():
    sec_data = parse_yaml(SEC_URL)
    ai_data = parse_yaml(AI_URL)
    all_raw = sec_data + ai_data

    results = []
    for conf in all_raw:
        title = conf.get('title', '')
        conf_id = str(conf.get('id', '')).lower()

        # Match either in full title or short conference id
        if any(tc in title.lower() or tc in conf_id for tc in TARGET_CONFS):
            deadlines = conf.get('deadlines', [])
            # Fallback if deadlines is listed directly at root level
            if not deadlines and 'deadline' in conf:
                deadlines = [{'deadline': conf.get('deadline'), 'year': conf.get('year', '')}]
            
            for cycle in deadlines:
                results.append({
                    "Title": f"{title} {cycle.get('year', conf.get('year', ''))}".strip(),
                    "Deadline": str(cycle.get('deadline', conf.get('deadline', 'TBA'))),
                    "AbstractDeadline": str(cycle.get('abstract_deadline', 'N/A')),
                    "Location": conf.get('place', conf.get('location', 'TBA')),
                    "Category": conf.get('sub', 'Security/AI'),
                    "Url": conf.get('link', '')
                })
    return results

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conf_data = fetch_all_conferences()
    with open("data/conferences.json", "w") as f:
        json.dump(conf_data, f, indent=2)
    print(f"Saved {len(conf_data)} conferences to data/conferences.json")