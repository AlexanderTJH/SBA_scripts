import json
import os
import urllib.request
import yaml

# Correct raw gh-pages data URLs
SEC_URL = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/master/_data/conferences.yml"
AI_URL = "https://raw.githubusercontent.com/paperswithcode/ai-deadlines/gh-pages/_data/conferences.yml"

# Target acronyms / titles for MLDM
TARGET_CONFS = {
    "pets", "s&p", "sp", "usenix", "ccs", "ndss", "eurosp", "esorics", "ares", 
    "neurips", "icml", "iclr", "aaai", "ijcai", "kdd", "cd-make"
}

def parse_yaml(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            return yaml.safe_load(content) or []
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def fetch_all_conferences():
    sec_data = parse_yaml(SEC_URL)
    ai_data = parse_yaml(AI_URL)
    all_raw = sec_data + ai_data

    results = []
    seen = set()

    for conf in all_raw:
        title = str(conf.get('title', ''))
        conf_id = str(conf.get('id', '')).lower()

        # Match against target list
        if any(tc == conf_id or tc in title.lower() for tc in TARGET_CONFS):
            deadlines = conf.get('deadlines', [])
            if not deadlines and 'deadline' in conf:
                deadlines = [{'deadline': conf.get('deadline'), 'year': conf.get('year', '')}]

            for cycle in deadlines:
                entry_title = f"{title} {cycle.get('year', conf.get('year', ''))}".strip()
                if entry_title in seen:
                    continue
                seen.add(entry_title)

                results.append({
                    "Title": entry_title,
                    "Deadline": str(cycle.get('deadline', conf.get('deadline', 'TBA'))),
                    "AbstractDeadline": str(cycle.get('abstract_deadline', 'N/A')),
                    "Location": str(conf.get('place', conf.get('location', 'TBA'))),
                    "Category": str(conf.get('sub', 'Security/AI')),
                    "Url": str(conf.get('link', ''))
                })

    return results

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conf_data = fetch_all_conferences()
    with open("data/conferences.json", "w", encoding="utf-8") as f:
        json.dump(conf_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(conf_data)} conferences to data/conferences.json")