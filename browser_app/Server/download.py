import requests
from pathlib import Path
import json
import re

url_pattern = r'(?:https?:\/\/)?(\S+?)\/'

def download_file(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception if the request was unsuccessful
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Download completed. File saved to {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

data_path = (Path(__file__) / "../../Data").resolve()
print(data_path)
for f in data_path.glob("*.json"):
    print(f)
    with open(f) as fp:
        data = json.load(fp)
        urls = []
        for claim in data:
            for ref in claim['supports'] + claim['contradicts']:
                for l in ref['links']:
                    for url in l['source']:
                        urls.append(url)
        urls = list(set(urls))
        print("Downloading favicons from:")
        print(urls)
        for url in urls:
            stem = re.findall(url_pattern, url)[0]
            favicon = "https://" + stem + '/favicon.ico'
            download_file(favicon, data_path / 'images' / stem)

