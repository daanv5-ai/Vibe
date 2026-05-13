import json
import requests

TOKEN_FILE = "whoop_token.json"

with open(TOKEN_FILE, "r") as f:
    tokens = json.load(f)

access_token = tokens["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

urls_to_test = [
    "https://api.prod.whoop.com/developer/v1/recovery",
    "https://api.prod.whoop.com/developer/v1/cycle",
    "https://api.prod.whoop.com/developer/v2/recovery",
    "https://api.prod.whoop.com/developer/v2/cycle",
    "https://api.prod.whoop.com/developer/v1/activity/sleep",
    "https://api.prod.whoop.com/developer/v2/activity/sleep"
]

for url in urls_to_test:
    res = requests.get(url, headers=headers)
    print(f"{url} -> {res.status_code}")
    if res.status_code == 200:
        print(f"Data snippet: {str(res.json())[:100]}")
    else:
        print(res.text)
