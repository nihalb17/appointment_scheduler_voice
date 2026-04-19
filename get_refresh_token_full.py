"""Script to get Google OAuth refresh token with all required scopes.

This script will open a browser for you to authorize access to:
- Google Calendar (read/write)
- Google Docs (create/edit)
- Gmail (send email)
- Google Sheets (append data)
- Google Drive (file management)
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes required for all MCP tools
SCOPES = [
    'https://www.googleapis.com/auth/calendar',  # Calendar read/write
    'https://www.googleapis.com/auth/documents',  # Google Docs
    'https://www.googleapis.com/auth/gmail.send',  # Gmail send
    'https://www.googleapis.com/auth/spreadsheets',  # Google Sheets
    'https://www.googleapis.com/auth/drive.file',  # Google Drive (for folder operations)
]

def main():
    print("=" * 60)
    print("Google OAuth Token Generator")
    print("=" * 60)
    print()
    print("This will authorize the application to access:")
    print("  - Google Calendar (create/delete events)")
    print("  - Google Docs (create meeting notes)")
    print("  - Gmail (send booking confirmations)")
    print("  - Google Sheets (log bookings/cancellations)")
    print("  - Google Drive (manage files)")
    print()
    
    # Check for client_secret.json
    if not os.path.exists('client_secret.json'):
        print("ERROR: client_secret.json not found!")
        print("Please download it from Google Cloud Console:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Navigate to APIs & Services > Credentials")
        print("  3. Download the OAuth 2.0 client credentials")
        print("  4. Save as client_secret.json in this directory")
        return
    
    # Create the flow
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES
    )
    
    # Run the OAuth flow
    print("Opening browser for authorization...")
    creds = flow.run_local_server(port=0)
    
    print()
    print("=" * 60)
    print("Authorization successful!")
    print("=" * 60)
    print()
    print("Refresh Token (save this in your .env file as GOOGLE_REFRESH_TOKEN):")
    print()
    print(creds.refresh_token)
    print()
    print("=" * 60)
    
    # Also save to a file
    with open('oauth_credentials_full.txt', 'w') as f:
        f.write(f"Refresh Token: {creds.refresh_token}\n")
        f.write(f"Token URI: {creds.token_uri}\n")
        f.write(f"Client ID: {creds.client_id}\n")
        f.write(f"Scopes: {', '.join(SCOPES)}\n")
    
    print("Credentials also saved to: oauth_credentials_full.txt")
    print()
    print("IMPORTANT: Update your .env file with the new GOOGLE_REFRESH_TOKEN")

if __name__ == '__main__':
    main()
