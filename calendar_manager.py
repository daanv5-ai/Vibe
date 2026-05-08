import os
import datetime
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

logger = logging.getLogger(__name__)

def get_calendar_service():
    """Gets a valid Google Calendar service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error("Error refreshing credentials: %s", e)
                return None
        else:
            if not os.path.exists("credentials.json"):
                logger.error("credentials.json not found! Please download it from Google Cloud Console.")
                return None
            
            # Note: This will open a browser window for local login.
            # In a remote server environment, this would need a different flow.
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except HttpError as error:
        logger.error("An error occurred: %s", error)
        return None

def list_upcoming_events(max_results=10):
    """Lists the next N upcoming events."""
    service = get_calendar_service()
    if not service:
        return "Error: Could not connect to Google Calendar. Make sure credentials.json is present and you have authorized."

    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        if not events:
            return "No upcoming events found."

        output = "📅 **Upcoming Events:**\n"
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            # Format time slightly better
            time_obj = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            time_str = time_obj.strftime("%a, %b %d @ %H:%M")
            output += f"- {time_str}: {event['summary']}\n"
        return output

    except HttpError as error:
        return f"An error occurred: {error}"

def add_calendar_event(summary, start_time_iso, end_time_iso=None, description=None, location=None):
    """
    Adds an event to the primary calendar.
    start_time_iso: ISO 8601 string (e.g., '2025-05-07T19:00:00')
    """
    service = get_calendar_service()
    if not service:
        return "Error: Could not connect to Google Calendar."

    # If end time isn't provided, default to 1 hour after start
    if not end_time_iso:
        start_dt = datetime.datetime.fromisoformat(start_time_iso)
        end_dt = start_dt + datetime.timedelta(hours=1)
        end_time_iso = end_dt.isoformat()

    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time_iso,
            'timeZone': 'Europe/Amsterdam',
        },
        'end': {
            'dateTime': end_time_iso,
            'timeZone': 'Europe/Amsterdam',
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ Event created: [{event.get('summary')}]({event.get('htmlLink')})"
    except HttpError as error:
        return f"An error occurred: {error}"
