import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

    def get_calendar_event(self, calendar_id: str, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a calendar event by searching for event_id in description."""
        try:
            events_result = self.calendar_service.events().list(
                calendarId=calendar_id,
                q=event_id,
                maxResults=10,
                singleEvents=True
            ).execute()

            events = events_result.get('items', [])

            for event in events:
                description = event.get('description', '')
                if event_id in description:
                    logger.debug(f"Found existing calendar event for {event_id}: {event.get('id')}")
                    return event

            return None

        except Exception as e:
            logger.error(f"Error getting calendar event: {str(e)}")
            return None

    def check_calendar_event_exists(self, calendar_id: str, event_id: str) -> bool:
        """Check if an event already exists in calendar by searching description."""
        return self.get_calendar_event(calendar_id, event_id) is not None

    def list_calendar_events_with_event_ids(self, calendar_id: str) -> List[Dict[str, Any]]:
        """List all calendar events that have 'Event ID:' in their description."""
        try:
            events = []
            page_token = None

            while True:
                events_result = self.calendar_service.events().list(
                    calendarId=calendar_id,
                    maxResults=100,
                    singleEvents=True,
                    pageToken=page_token
                ).execute()

                items = events_result.get('items', [])

                # Filter events with Event ID in description
                for event in items:
                    description = event.get('description', '')
                    if 'Event ID:' in description:
                        events.append(event)

                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"Found {len(events)} calendar events with Event IDs")
            return events

        except Exception as e:
            logger.error(f"Error listing calendar events: {str(e)}")
            return []

    def extract_event_id_from_description(self, description: str) -> Optional[str]:
        """Extract Event ID from calendar event description."""
        try:
            if 'Event ID:' in description:
                # Find the line with Event ID
                for line in description.split('\n'):
                    if 'Event ID:' in line:
                        # Extract everything after "Event ID:"
                        event_id = line.split('Event ID:')[1].strip()
                        return event_id
            return None
        except Exception as e:
            logger.error(f"Error extracting event ID: {str(e)}")
            return None

    def create_calendar_event(
            self,
            calendar_id: str,
            event_data: Dict[str, Any],
            event_type: str
    ) -> str:
        """Create an event in Google Calendar."""
        try:
            date_str = event_data.get('date', '').strip()
            time_str = event_data.get('time', '').strip()

            if not date_str or not time_str:
                logger.error(f"Missing date or time: date='{date_str}', time='{time_str}'")
                raise ValueError(f"Event must have both date and time. Got date='{date_str}', time='{time_str}'")

            event_datetime = datetime.strptime(
                f"{date_str} {time_str}",
                '%Y-%m-%d %H:%M'
            )

            duration_hours = {
                'concerts': 3,
                'interviews': 1,
                'study': 2
            }.get(event_type, 1)

            end_datetime = event_datetime + timedelta(hours=duration_hours)

            # Build event based on type
            summary, location, description = self._build_event_content(event_data, event_type)

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
                        {'method': 'popup', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 60},
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

    def update_calendar_event(
            self,
            calendar_id: str,
            calendar_event_id: str,
            event_data: Dict[str, Any],
            event_type: str
    ) -> bool:
        """Update an existing calendar event."""
        try:
            date_str = event_data.get('date', '').strip()
            time_str = event_data.get('time', '').strip()

            if not date_str or not time_str:
                logger.error(f"Missing date or time: date='{date_str}', time='{time_str}'")
                return False

            event_datetime = datetime.strptime(
                f"{date_str} {time_str}",
                '%Y-%m-%d %H:%M'
            )

            duration_hours = {
                'concerts': 3,
                'interviews': 1,
                'study': 2
            }.get(event_type, 1)

            end_datetime = event_datetime + timedelta(hours=duration_hours)

            # Build event content
            summary, location, description = self._build_event_content(event_data, event_type)

            # Update event
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
                        {'method': 'popup', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 60},
                    ],
                },
            }

            self.calendar_service.events().update(
                calendarId=calendar_id,
                eventId=calendar_event_id,
                body=event
            ).execute()

            logger.info(f"Calendar event updated: {calendar_event_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating calendar event: {str(e)}")
            return False

    def delete_calendar_event(self, calendar_id: str, calendar_event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            self.calendar_service.events().delete(
                calendarId=calendar_id,
                eventId=calendar_event_id
            ).execute()

            logger.info(f"Calendar event deleted: {calendar_event_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}")
            return False

    def _build_event_content(self, event_data: Dict[str, Any], event_type: str) -> Tuple[str, str, str]:
        """Build summary, location, and description for calendar event."""
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

        return summary, location, description

    def events_are_different(
            self,
            sheet_event_data: Dict[str, Any],
            calendar_event: Dict[str, Any],
            event_type: str
    ) -> bool:
        """Compare sheet event data with calendar event to detect changes."""
        try:
            # Build what the calendar event SHOULD look like
            expected_summary, expected_location, expected_description = self._build_event_content(
                sheet_event_data, event_type
            )

            # Compare summary
            if calendar_event.get('summary', '') != expected_summary:
                logger.debug(f"Summary differs: '{calendar_event.get('summary')}' vs '{expected_summary}'")
                return True

            # Compare location
            if calendar_event.get('location', '') != expected_location:
                logger.debug(f"Location differs")
                return True

            # Compare description (normalize whitespace)
            cal_desc = ' '.join(calendar_event.get('description', '').split())
            exp_desc = ' '.join(expected_description.split())
            if cal_desc != exp_desc:
                logger.debug(f"Description differs")
                return True

            # Compare datetime
            date_str = sheet_event_data.get('date', '').strip()
            time_str = sheet_event_data.get('time', '').strip()

            if date_str and time_str:
                expected_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')

                cal_start = calendar_event.get('start', {}).get('dateTime', '')
                if cal_start:
                    # Parse calendar datetime (ISO format)
                    cal_datetime = datetime.fromisoformat(cal_start.replace('Z', '+00:00'))
                    cal_datetime_naive = cal_datetime.replace(tzinfo=None)

                    if cal_datetime_naive != expected_datetime:
                        logger.debug(f"DateTime differs: {cal_datetime_naive} vs {expected_datetime}")
                        return True

            return False

        except Exception as e:
            logger.error(f"Error comparing events: {str(e)}")
            return False