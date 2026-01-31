import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import boto3

from utils import parse_event_row, parse_event_datetime

logger = logging.getLogger()


class EventProcessor:
    """Process events and manage notifications."""

    def __init__(self, sheets_client, notification_manager, timezone):
        """Initialize event processor."""
        self.sheets_client = sheets_client
        self.notification_manager = notification_manager
        self.timezone = timezone
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ['DYNAMODB_TABLE']
        self.table = self.dynamodb.Table(self.table_name)

    def process_events(
            self,
            events_data: List[List[Any]],
            event_type: str,
            notification_rules: List[Dict[str, int]],
            current_time: datetime,
            trigger_type: str
    ) -> Dict[str, Any]:
        """Process events and send notifications based on rules."""
        try:
            events_processed = 0
            notifications_sent = 0
            errors = []

            logger.info(f"Processing {len(events_data)} {event_type} events")

            for row in events_data:
                try:
                    event_data = parse_event_row(row, event_type)  # ← USAR FUNCIÓN IMPORTADA

                    if not event_data or not event_data.get('event_id'):
                        logger.warning(f"Skipping invalid row: {row}")
                        continue

                    events_processed += 1

                    notifications = self._check_notification_needed(
                        event_data=event_data,
                        event_type=event_type,
                        notification_rules=notification_rules,
                        current_time=current_time,
                        trigger_type=trigger_type
                    )

                    for notification_label in notifications:
                        if self._send_and_track_notification(
                                event_data=event_data,
                                event_type=event_type,
                                notification_label=notification_label,
                                current_time=current_time
                        ):
                            notifications_sent += 1

                except Exception as e:
                    error_msg = f"Error processing row {row}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            return {
                'events_processed': events_processed,
                'notifications_sent': notifications_sent,
                'errors': errors,
                'error_count': len(errors)
            }

        except Exception as e:
            logger.error(f"Error in process_events: {str(e)}")
            raise

    def _check_notification_needed(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_rules: List[Dict[str, int]],
            current_time: datetime,
            trigger_type: str
    ) -> List[str]:
        """Check which notifications are needed for an event."""
        notifications_needed = []

        try:
            event_datetime = parse_event_datetime(  # ← USAR FUNCIÓN IMPORTADA
                event_data.get('date', ''),
                event_data.get('time', ''),
                self.timezone
            )

            if not event_datetime or event_datetime < current_time:
                return notifications_needed

            for rule in notification_rules:
                notification_time = event_datetime - timedelta(
                    days=rule['days'],
                    hours=rule['hours']
                )

                label = rule['label']

                if event_type == 'study' and label == '1_day_before_6pm':
                    notification_time = (event_datetime - timedelta(days=1)).replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )

                window_hours = 2 if trigger_type == 'hourly-urgent' else 6
                window_start = notification_time - timedelta(hours=window_hours / 2)
                window_end = notification_time + timedelta(hours=window_hours / 2)

                if window_start <= current_time <= window_end:
                    if not self._is_already_notified(event_data.get('event_id'), event_type, label):
                        notifications_needed.append(label)

            return notifications_needed

        except Exception as e:
            logger.error(f"Error checking notifications: {str(e)}")
            return notifications_needed

    # ← ELIMINAR _parse_event_datetime de aquí

    def _is_already_notified(self, event_id: str, event_type: str, notification_label: str) -> bool:
        """Check if notification has already been sent."""
        try:
            notification_key = f"{event_id}#{notification_label}"
            response = self.table.get_item(
                Key={'event_id': notification_key, 'event_type': event_type}
            )
            return 'Item' in response
        except Exception as e:
            logger.error(f"Error checking notification status: {str(e)}")
            return False

    def _send_and_track_notification(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_label: str,
            current_time: datetime
    ) -> bool:
        """Send notification and track it in DynamoDB."""
        try:
            # Get calendar ID from environment
            calendar_id = os.environ.get('GOOGLE_CALENDAR_ID', '')

            # Send notification with all channels
            results = self.notification_manager.send_notification(
                event_data=event_data,
                event_type=event_type,
                notification_label=notification_label,
                sheets_client=self.sheets_client,
                calendar_id=calendar_id
            )

            # Track if at least one channel succeeded
            if results.get('email') or results.get('discord'):
                notification_key = f"{event_data.get('event_id')}#{notification_label}"

                self.table.put_item(
                    Item={
                        'event_id': notification_key,
                        'event_type': event_type,
                        'event_date': event_data.get('date', ''),
                        'notification_label': notification_label,
                        'sent_at': current_time.isoformat(),
                        'channels': {
                            'email': results.get('email', False),
                            'discord': results.get('discord', False),
                            'calendar': results.get('calendar', False)
                        }
                    }
                )

                logger.info(f"Notification tracked: {notification_key} - Channels: {results}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error sending/tracking notification: {str(e)}")
            return False
