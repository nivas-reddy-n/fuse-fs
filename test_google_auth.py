#!/usr/bin/env python3
"""
Test Google Drive authentication with credentials.json
"""
import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Use the same scopes as in your config file
SCOPES = ['https://www.googleapis.com/auth/drive']

def test_google_drive_auth():
    """Test Google Drive authentication and list files."""
    print("Testing Google Drive authentication...")
    
    credentials_file = 'credentials.json'
    token_file = 'token.json'
    
    # Check if credentials file exists
    if not os.path.exists(credentials_file):
        print(f"Error: Credentials file '{credentials_file}' not found")
        return False
    
    creds = None
    
    # Check if token.json exists
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_info(
                info=eval(open(token_file, 'r').read()),
                scopes=SCOPES
            )
            print("Found existing token.json file")
        except Exception as e:
            print(f"Error loading credentials from token file: {e}")
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        
        # If still no valid credentials, start OAuth flow
        if not creds:
            try:
                print("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                print("OAuth flow completed successfully")
                
                # Save the credentials for the next run
                with open(token_file, 'w') as token:
                    token.write(str(creds.to_json()))
                print(f"Saved credentials to {token_file}")
            except Exception as e:
                print(f"Error during OAuth flow: {e}")
                return False
    
    try:
        # Build the service
        service = build('drive', 'v3', credentials=creds)
        print("Successfully authenticated with Google Drive")
        
        # List files to test the connection
        print("\nListing files from your Google Drive:")
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        
        if not items:
            print("No files found.")
        else:
            for item in items:
                print(f"{item['name']} (ID: {item['id']})")
        
        return True
    except Exception as e:
        print(f"Error testing Google Drive API: {e}")
        return False

if __name__ == "__main__":
    success = test_google_drive_auth()
    print("\nAuthentication test:", "SUCCESS" if success else "FAILED")
    if success:
        print("Your Google Drive integration is configured correctly!")
        print("The token.json file has been created with your credentials.")
    else:
        print("Please check the error messages above and try again.") 