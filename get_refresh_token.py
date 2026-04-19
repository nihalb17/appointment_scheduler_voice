"""
Script to generate a new refresh token with Calendar API scopes.
Run this after adding Calendar scopes to your OAuth consent screen.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes needed for the appointment scheduler
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]

def main():
    print("=" * 60)
    print("Google OAuth Refresh Token Generator")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Open a browser for you to authorize the app")
    print("2. Generate a refresh token with Calendar API permissions")
    print("3. Display the token for you to copy to .env")
    print()
    
    # Path to your client secrets file (downloaded from Google Cloud Console)
    client_secrets_file = input("Enter path to your client_secrets.json file: ").strip()
    
    if not os.path.exists(client_secrets_file):
        print(f"Error: File not found: {client_secrets_file}")
        return
    
    try:
        # Create the flow
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file,
            SCOPES,
            redirect_uri='http://localhost:8080'
        )
        
        print("\nOpening browser for authorization...")
        print("If browser doesn't open, copy the URL from the terminal.\n")
        
        # Run the OAuth flow
        credentials = flow.run_local_server(port=8080)
        
        print("\n" + "=" * 60)
        print("SUCCESS! Copy these values to your .env file:")
        print("=" * 60)
        print()
        print(f"GOOGLE_CLIENT_ID={credentials.client_id}")
        print(f"GOOGLE_CLIENT_SECRET={credentials.client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}")
        print()
        print("Also ensure you have:")
        print("GOOGLE_CALENDAR_ID=primary")
        print()
        print("=" * 60)
        
        # Save to a file for convenience
        output_file = "oauth_credentials.txt"
        with open(output_file, "w") as f:
            f.write(f"GOOGLE_CLIENT_ID={credentials.client_id}\n")
            f.write(f"GOOGLE_CLIENT_SECRET={credentials.client_secret}\n")
            f.write(f"GOOGLE_REFRESH_TOKEN={credentials.refresh_token}\n")
        print(f"\nCredentials also saved to: {output_file}")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you added Calendar scopes to OAuth consent screen")
        print("2. Make sure you're added as a test user")
        print("3. Make sure the OAuth consent screen is published (or in testing with you as test user)")

if __name__ == "__main__":
    main()
