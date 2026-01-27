import os
import requests
import json
import base64

def get_token():
    domain = os.environ.get('SYNTHETICDATA_OKTA_DOMAIN')
    client_id = os.environ.get('SYNTHETICDATA_OKTA_CLIENT_ID')
    client_secret = os.environ.get('SYNTHETICDATA_OKTA_CLIENT_SECRET')

    if not all([domain, client_id, client_secret]):
        print("Error: Please export SYNTHETICDATA_OKTA_DOMAIN, SYNTHETICDATA_OKTA_CLIENT_ID, and SYNTHETICDATA_OKTA_CLIENT_SECRET")
        return

    url = f"https://{domain}/oauth2/default/v1/token"
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'client_credentials',
        'scope': 'syntheticdata:invoke'
    }

    print(f"Requesting token from {url}...")
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"Failed to get token: {response.status_code}")
        print(response.text)
        return

    token = response.json().get('access_token')
    print("\nSuccessfully retrieved token!")
    print(f"RAW TOKEN: {token}")
    
    # Decode JWT (no verify, just debug)
    parts = token.split('.')
    if len(parts) == 3:
        payload = parts[1]
        padded = payload + '=' * (4 - len(payload) % 4)
        claims = json.loads(base64.b64decode(padded).decode())
        
        print("\n--- Token Claims ---")
        print(f"Audience (aud): {claims.get('aud')}")
        print(f"Issuer (iss):   {claims.get('iss')}")
        print(f"Client ID (cid): {claims.get('cid')}")
        print("--------------------")
        
        expected_aud = os.environ.get('SYNTHETICDATA_OKTA_AUDIENCE')
        print(f"\nYour Runtime is expecting Audience: '{expected_aud}'")
        
        if claims.get('aud') == expected_aud:
            print("✅ MATCH! Audience configuration looks correct.")
        else:
            print("❌ MISMATCH! You need to redeploy the Runtime with:")
            print(f'export SYNTHETICDATA_OKTA_AUDIENCE="{claims.get("aud")}"')
    else:
        print("Could not decode token parts.")

if __name__ == "__main__":
    get_token()
