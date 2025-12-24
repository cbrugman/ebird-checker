import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

EBIRD_API_KEY = os.environ.get('EBIRD_API_KEY')
EBIRD_API_BASE = "https://api.ebird.org/v2"

if not EBIRD_API_KEY:
    print("Error: EBIRD_API_KEY not found in environment variables.")
    exit(1)

def fetch_json(url, params=None):
    headers = {'X-eBirdApiToken': EBIRD_API_KEY}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Error fetching {url}: {response.status_code} {response.text}")
        response.raise_for_status()
    return response.json()

def main():
    print("Fetching global taxonomy (locale=en_CA)...")
    taxonomy = fetch_json(f"{EBIRD_API_BASE}/ref/taxonomy/ebird", params={'fmt': 'json', 'locale': 'en_CA'})
    print(f"Fetched {len(taxonomy)} taxonomy entries.")

    print("Fetching species list for region CA...")
    # This endpoint returns a simple list of species codes
    ca_species_codes = fetch_json(f"{EBIRD_API_BASE}/product/spplist/CA")
    print(f"Fetched {len(ca_species_codes)} species codes for Canada.")
    
    ca_species_set = set(ca_species_codes)
    
    # Filter taxonomy
    filtered_species = []
    for species in taxonomy:
        if species['speciesCode'] in ca_species_set:
            filtered_species.append({
                'code': species['speciesCode'],
                'commonName': species['comName'],
                'sciName': species['sciName']
            })
            
    print(f"Filtered down to {len(filtered_species)} species.")
    
    output_path = os.path.join('static', 'species.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_species, f, ensure_ascii=False, indent=2)
        
    print(f"Saved species list to {output_path}")

if __name__ == "__main__":
    main()
