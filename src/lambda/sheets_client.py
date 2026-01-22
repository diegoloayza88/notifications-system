import os
import json
import logging
from typing import List, Dict, Any
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta

logger = logging.getLogger()


class GoogleSheetsClient:
    """Client for interacting with Google Sheets and Calendar APIs."""

    SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self):
        """Initialize the Google Sheets and Calendar clients."""
        self.secrets_client = boto3.client('secretsmanager')
        self.sheets_credentials = self._get_credentials(self.SHEETS_SCOPES)
        self.calendar_credentials = self._get_credentials(self.CALENDAR_SCOPES)

        self.sheets_service = build('sheets', 'v4', credentials=self.sheets_credentials)
        self.calendar_service = build('calendar', 'v3', credentials=self.calendar_credentials)

    def _get_credentials(self, scopes: List[str]) -> service_account.Credentials:
        """Retrieve Google service account credentials from Secrets Manager."""
        try:
            secret_arn = os.environ['GOOGLE_CREDENTIALS']
            response = self.secrets_client.get_secret_value(SecretId=secret_arn)
            credentials_json = json.loads(response['SecretString'])

            return service_account.Credentials.from_service_account_info(
                credentials_json,
                scopes=scopes
            )
        except Exception as e:
            logger.error(f"Error retrieving Google credentials: {str(e)}")
            raise

    def read_sheet(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        """Read data from a Google Sheet."""
        try:
            logger.info(f"Reading sheet: {spreadsheet_id}, range: {range_name}")

            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            logger.info(f"Retrieved {len(values)} rows from sheet")

            return values

        except HttpError as error:
            logger.error(f"Google Sheets API error: {error}")
            raise
        except Exception as e:
            logger.error(f"Error reading sheet: {str(e)}")
            raise

    def check_calendar_event_exists(self, calendar_id: str, event_id: str) -> bool:
        """Check if an event already exists in calendar by searching description."""
        try:
            # Search for events containing this event_id in description
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                q=event_id,
                maxResults=10,
                singleEvents=True
            ).execute()

            events = events_result.get('items', [])

            # Check if any event has this exact event_id in description
            for event in events:
                description = event.get('description', '')
                if event_id in description:
                    logger.info(f"Found existing calendar event for {event_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking calendar event: {str(e)}")
            return False

    def create_calendar_event(
            self,
            calendar_id: str,
            event_data: Dict[str, Any],
            event_type: str
    ) -> str:
        """Create an event in Google Calendar."""
        try:
            # Parse date and time
            date_str = event_data.get('date', '').strip()
            time_str = event_data.get('time', '').strip()

            # Validar que tenemos fecha y hora
            if not date_str or not time_str:
                logger.error(f"Missing date or time: date='{date_str}', time='{time_str}'")
                raise ValueError(f"Event must have both date and time. Got date='{date_str}', time='{time_str}'")

            event_datetime = datetime.strptime(
                f"{date_str} {time_str}",
                '%Y-%m-%d %H:%M'
            )

            # Determine duration based on event type
            duration_hours = {
                'concerts': 3,
                'interviews': 1,
                'study': 2
            }.get(event_type, 1)

            end_datetime = event_datetime + timedelta(hours=duration_hours)

            # Build event based on type
            if event_type == 'concerts':
                summary = f"🎸 {event_data.get('band', 'Concierto')}"
                location = event_data.get('venue', '')
                description = f"""Concierto: {event_data.get('band', 'N/A')}
Lugar: {event_data.get('venue', 'N/A')}
Ubicación: {event_data.get('location', 'N/A')}
Notas: {event_data.get('notes', '')}

Event ID: {event_data.get('event_id', 'N/A')}"""

            elif event_type == 'interviews':
                summary = f"💼 Entrevista - {event_data.get('company', 'Empresa')}"
                location = "Virtual/Office"
                description = f"""Entrevista de trabajo
Empresa: {event_data.get('company', 'N/A')}
Posición: {event_data.get('position', 'N/A')}
Entrevistador: {event_data.get('interviewer', 'N/A')}
Etapa: {event_data.get('stage', 'N/A')}

Preparación: {event_data.get('prep_notes', '')}

Event ID: {event_data.get('event_id', 'N/A')}"""

            else:  # study
                summary = f"📚 Estudio - {event_data.get('topic', 'Sesión de estudio')}"
                location = "Home"
                description = f"""Sesión de estudio
Curso: {event_data.get('course', 'N/A')}
Tema: {event_data.get('topic', 'N/A')}
Duración: {event_data.get('duration', 'N/A')}
Prioridad: {event_data.get('priority', 'N/A')}

Recursos: {event_data.get('resources', '')}

Event ID: {event_data.get('event_id', 'N/A')}"""

            # Create event
            event = {
                'summary': summary,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': event_datetime.isoformat(),
                    'timeZone': 'America/Lima',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/Lima',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 60},  # 1 hour before
                    ],
                },
            }

            created_event = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            logger.info(f"Calendar event created: {created_event.get('id')}")
            return created_event.get('id', '')

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}")
            raise