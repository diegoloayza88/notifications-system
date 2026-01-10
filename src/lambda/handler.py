import json
import os
import logging
from datetime import datetime
import pytz
from typing import Dict, Any

from sheets_client import GoogleSheetsClient
from notification_manager import NotificationManager
from event_processor import EventProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
TIMEZONE = os.environ.get('TIMEZONE', 'America/Lima')
CONCERTS_SHEET_ID = os.environ['CONCERTS_SHEET_ID']
INTERVIEWS_SHEET_ID = os.environ['INTERVIEWS_SHEET_ID']
STUDY_SHEET_ID = os.environ['STUDY_SHEET_ID']

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

def main(event: Dict[str, Any], context: Any):
    """
    Main Lambda handler function

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
            'summary': {}
        }

        # Process concerts
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
        if trigger_type == 'evening-check' or trigger_type == 'manual':
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

        results['summary'] = {
            'total_events_processed': total_events_processed,
            'total_notifications_sent': total_notifications,
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