import json
import os
import logging
from datetime import datetime
import pytz
from typing import Dict, Any

from sheets_client import GoogleSheetsClient
from notification_manager import NotificationManager
from event_processor import EventProcessor
from utils import parse_event_row, parse_event_datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
TIMEZONE = os.environ.get('TIMEZONE', 'America/Lima')
CONCERTS_SHEET_ID = os.environ.get('CONCERTS_SHEET_ID', '')
INTERVIEWS_SHEET_ID = os.environ.get('INTERVIEWS_SHEET_ID', '')
STUDY_SHEET_ID = os.environ.get('STUDY_SHEET_ID', '')
GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', '')

# Notification rules configuration
NOTIFICATION_RULES = {
    'concerts': [
        {'days': 14, 'hours': 0, 'label': '2_weeks_before'},
        {'days': 1, 'hours': 0, 'label': '1_day_before'},
        {'days': 0, 'hours': 4, 'label': '4_hours_before'}
    ],
    'interviews': [
        {'days': 7, 'hours': 0, 'label': '1_week_before'},
        {'days': 1, 'hours': 0, 'label': '1_day_before'},
        {'days': 0, 'hours': 1, 'label': '1_hour_before'}
    ],
    'study': [
        {'days': 1, 'hours': 0, 'label': '1_day_before_6pm'}
    ]
}


# ← ELIMINAR _parse_event_row y _parse_event_datetime de aquí


def sync_calendar_events(
        sheets_client: GoogleSheetsClient,
        current_time: datetime,
        timezone: pytz.timezone
) -> Dict[str, Any]:
    """
    Sync all future events to Google Calendar.
    - Creates calendar events for new events
    - Updates calendar events if data changed in sheet
    - Deletes calendar events if removed from sheet
    """
    sync_results = {
        'concerts': {'checked': 0, 'created': 0, 'updated': 0, 'deleted': 0, 'skipped': 0, 'errors': 0},
        'interviews': {'checked': 0, 'created': 0, 'updated': 0, 'deleted': 0, 'skipped': 0, 'errors': 0},
        'study': {'checked': 0, 'created': 0, 'updated': 0, 'deleted': 0, 'skipped': 0, 'errors': 0}
    }

    if not GOOGLE_CALENDAR_ID:
        logger.warning("GOOGLE_CALENDAR_ID not configured, skipping calendar sync")
        return sync_results

    logger.info("Starting comprehensive calendar sync...")

    # Step 1: Collect all event IDs that SHOULD exist from sheets
    sheet_event_ids = {}  # {event_id: (event_data, event_type)}

    event_configs = [
        ('concerts', CONCERTS_SHEET_ID, 'Sheet1!A2:H'),
        ('interviews', INTERVIEWS_SHEET_ID, 'Sheet1!A2:I'),
        ('study', STUDY_SHEET_ID, 'Sheet1!A2:H')
    ]

    for event_type, sheet_id, range_name in event_configs:
        if not sheet_id:
            continue

        try:
            events_data = sheets_client.read_sheet(sheet_id, range_name)

            for row in events_data:
                sync_results[event_type]['checked'] += 1

                try:
                    event_data = parse_event_row(row, event_type)  # ← USAR FUNCIÓN IMPORTADA

                    if not event_data or not event_data.get('event_id'):
                        continue

                    # Check if event is in the future
                    event_datetime = parse_event_datetime(  # ← USAR FUNCIÓN IMPORTADA
                        event_data.get('date', ''),
                        event_data.get('time', ''),
                        timezone
                    )

                    if not event_datetime:
                        sync_results[event_type]['errors'] += 1
                        continue

                    # Only sync future events
                    if event_datetime < current_time:
                        sync_results[event_type]['skipped'] += 1
                        continue

                    # Store for comparison
                    event_id = event_data.get('event_id', '')
                    sheet_event_ids[event_id] = (event_data, event_type)

                except Exception as e:
                    logger.error(f"Error processing row {row}: {str(e)}")
                    sync_results[event_type]['errors'] += 1

        except Exception as e:
            logger.error(f"Error reading {event_type} sheet: {str(e)}")

    logger.info(f"Found {len(sheet_event_ids)} future events in sheets")

    # Step 2: Get all calendar events with Event IDs
    calendar_events = sheets_client.list_calendar_events_with_event_ids(GOOGLE_CALENDAR_ID)
    calendar_event_map = {}  # {event_id: calendar_event}

    for cal_event in calendar_events:
        description = cal_event.get('description', '')
        event_id = sheets_client.extract_event_id_from_description(description)
        if event_id:
            calendar_event_map[event_id] = cal_event

    logger.info(f"Found {len(calendar_event_map)} events in calendar with Event IDs")

    # Step 3: Process differences

    # 3a. Create or Update events from sheets
    for event_id, (event_data, event_type) in sheet_event_ids.items():
        try:
            if event_id not in calendar_event_map:
                # CREATE: Event in sheet but not in calendar
                logger.info(f"Creating calendar event for {event_id}")
                sheets_client.create_calendar_event(
                    calendar_id=GOOGLE_CALENDAR_ID,
                    event_data=event_data,
                    event_type=event_type
                )
                sync_results[event_type]['created'] += 1
            else:
                # Check if UPDATE needed
                calendar_event = calendar_event_map[event_id]

                if sheets_client.events_are_different(event_data, calendar_event, event_type):
                    logger.info(f"Updating calendar event for {event_id}")
                    sheets_client.update_calendar_event(
                        calendar_id=GOOGLE_CALENDAR_ID,
                        calendar_event_id=calendar_event.get('id'),
                        event_data=event_data,
                        event_type=event_type
                    )
                    sync_results[event_type]['updated'] += 1
                else:
                    logger.debug(f"No changes for {event_id}")
                    sync_results[event_type]['skipped'] += 1

        except Exception as e:
            logger.error(f"Error syncing event {event_id}: {str(e)}")
            sync_results[event_type]['errors'] += 1

    # 3b. Delete events removed from sheets
    for event_id, calendar_event in calendar_event_map.items():
        if event_id not in sheet_event_ids:
            # DELETE: Event in calendar but not in sheet
            try:
                logger.info(f"Deleting calendar event for removed Event ID: {event_id}")
                sheets_client.delete_calendar_event(
                    calendar_id=GOOGLE_CALENDAR_ID,
                    calendar_event_id=calendar_event.get('id')
                )

                # Determine event type for stats (from calendar event summary)
                summary = calendar_event.get('summary', '')
                if '🎸' in summary:
                    sync_results['concerts']['deleted'] += 1
                elif '💼' in summary:
                    sync_results['interviews']['deleted'] += 1
                elif '📚' in summary:
                    sync_results['study']['deleted'] += 1

            except Exception as e:
                logger.error(f"Error deleting calendar event {event_id}: {str(e)}")

    logger.info(f"Calendar sync complete: {sync_results}")
    return sync_results


def main(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function.

    Args:
        event: Lambda event object containing trigger information
        context: Lambda context object

    Returns:
        Response dictionary with status and details
    """
    try:
        logger.info(f"Starting event processor - Environment: {ENVIRONMENT}")
        logger.info(f"Trigger event: {json.dumps(event)}")

        # Initialize timezone
        tz = pytz.timezone(TIMEZONE)
        current_time = datetime.now(tz)
        trigger_type = event.get('trigger_type', 'manual')

        logger.info(f"Current time: {current_time} ({TIMEZONE})")
        logger.info(f"Trigger type: {trigger_type}")

        # Initialize clients
        sheets_client = GoogleSheetsClient()
        notification_manager = NotificationManager()
        event_processor = EventProcessor(
            sheets_client=sheets_client,
            notification_manager=notification_manager,
            timezone=tz
        )

        # Process each event type
        results = {
            'concerts': {},
            'interviews': {},
            'study': {},
            'calendar_sync': {},
            'summary': {}
        }

        # Process concerts
        if CONCERTS_SHEET_ID:
            logger.info("Processing concerts...")
            concerts_data = sheets_client.read_sheet(CONCERTS_SHEET_ID, 'Sheet1!A2:H')
            results['concerts'] = event_processor.process_events(
                events_data=concerts_data,
                event_type='concerts',
                notification_rules=NOTIFICATION_RULES['concerts'],
                current_time=current_time,
                trigger_type=trigger_type
            )

        # Process interviews
        if INTERVIEWS_SHEET_ID:
            logger.info("Processing interviews...")
            interviews_data = sheets_client.read_sheet(INTERVIEWS_SHEET_ID, 'Sheet1!A2:I')
            results['interviews'] = event_processor.process_events(
                events_data=interviews_data,
                event_type='interviews',
                notification_rules=NOTIFICATION_RULES['interviews'],
                current_time=current_time,
                trigger_type=trigger_type
            )

        # Process study schedule (only on evening check)
        if STUDY_SHEET_ID and (trigger_type == 'evening-check' or trigger_type == 'manual'):
            logger.info("Processing study schedule...")
            study_data = sheets_client.read_sheet(STUDY_SHEET_ID, 'Sheet1!A2:H')
            results['study'] = event_processor.process_events(
                events_data=study_data,
                event_type='study',
                notification_rules=NOTIFICATION_RULES['study'],
                current_time=current_time,
                trigger_type=trigger_type
            )
        else:
            logger.info("Skipping study schedule (not evening check)")
            results['study'] = {'skipped': True}

        # Sync calendar events (create missing ones, update changed ones, delete removed ones)
        logger.info("Syncing calendar events...")
        results['calendar_sync'] = sync_calendar_events(
            sheets_client=sheets_client,
            current_time=current_time,
            timezone=tz
        )

        # Generate summary
        total_notifications = (
                results['concerts'].get('notifications_sent', 0) +
                results['interviews'].get('notifications_sent', 0) +
                results['study'].get('notifications_sent', 0)
        )

        total_events_processed = (
                results['concerts'].get('events_processed', 0) +
                results['interviews'].get('events_processed', 0) +
                results['study'].get('events_processed', 0)
        )

        total_calendar_created = (
                results['calendar_sync'].get('concerts', {}).get('created', 0) +
                results['calendar_sync'].get('interviews', {}).get('created', 0) +
                results['calendar_sync'].get('study', {}).get('created', 0)
        )

        total_calendar_updated = (
                results['calendar_sync'].get('concerts', {}).get('updated', 0) +
                results['calendar_sync'].get('interviews', {}).get('updated', 0) +
                results['calendar_sync'].get('study', {}).get('updated', 0)
        )

        total_calendar_deleted = (
                results['calendar_sync'].get('concerts', {}).get('deleted', 0) +
                results['calendar_sync'].get('interviews', {}).get('deleted', 0) +
                results['calendar_sync'].get('study', {}).get('deleted', 0)
        )

        results['summary'] = {
            'total_events_processed': total_events_processed,
            'total_notifications_sent': total_notifications,
            'total_calendar_events_created': total_calendar_created,
            'total_calendar_events_updated': total_calendar_updated,
            'total_calendar_events_deleted': total_calendar_deleted,
            'execution_time': current_time.isoformat(),
            'trigger_type': trigger_type
        }

        logger.info(f"Processing complete. Summary: {json.dumps(results['summary'])}")

        return {
            'statusCode': 200,
            'body': json.dumps(results, default=str)
        }

    except Exception as e:
        logger.error(f"Error in main handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'error_type': type(e).__name__
            })
        }
