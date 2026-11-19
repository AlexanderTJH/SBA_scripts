import json

with open ("/Users/alexanderteo/Desktop/Code/Work/SBA_scripts/data/eu_calls.json") as f:
    json_data = json.load(f)
    for item in json_data:
        print(item["Title"])