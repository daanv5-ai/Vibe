import os
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()

WHOOP_CLIENT_ID = os.environ.get("WHOOP_CLIENT_ID")
WHOOP_CLIENT_SECRET = os.environ.get("WHOOP_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
TOKEN_FILE = "whoop_token.json"

auth_code = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window and return to your terminal.")
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization failed! No code provided.")

def get_tokens(code):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": WHOOP_CLIENT_ID,
        "client_secret": WHOOP_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(TOKEN_URL, data=data)
    response.raise_for_status()
    tokens = response.json()
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)
    print("Tokens successfully saved to whoop_token.json")

def main():
    if not WHOOP_CLIENT_ID or not WHOOP_CLIENT_SECRET:
        print("Error: Please set WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET in your .env file.")
        return

    # Start local server to catch the redirect
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, OAuthHandler)

    # Open browser for user to authenticate
    scope = "read:recovery read:sleep read:workout read:cycles read:profile offline"
    auth_request_url = f"{AUTH_URL}?client_id={WHOOP_CLIENT_ID}&response_type=code&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&scope={urllib.parse.quote(scope)}&state=whoop_auth"
    
    print(f"Opening browser to authenticate with Whoop...")
    print(f"If the browser doesn't open automatically, navigate to this URL:")
    print(auth_request_url)
    
    webbrowser.open(auth_request_url)
    
    # Wait for one request
    print("\nWaiting for authentication callback on http://localhost:8000/callback...")
    httpd.handle_request()
    
    if auth_code:
        print("Authorization code received. Fetching tokens...")
        get_tokens(auth_code)
    else:
        print("Failed to get authorization code.")

if __name__ == "__main__":
    main()
