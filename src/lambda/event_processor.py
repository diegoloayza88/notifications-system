import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
import pytz

logger = logging.getLogger()


class EventProcessor:
    """Process events and manage notifications."""

    def __init__(self, sheets_client, notification_manager, timezone):
        """
        Initialize event processor.

        Args:
            sheets_client: GoogleSheetsClient instance
            notification_manager: NotificationManager instance
            timezone: pytz timezone object
        """
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
        """
        Process events and send notifications based on rules.

        Args:
            events_data: Raw data from Google Sheets
            event_type: Type of event (concerts, interviews, study)
            notification_rules: List of notification timing rules
            current_time: Current datetime with timezone
            trigger_type: Type of trigger that invoked this

        Returns:
            Processing results summary
        """
        try:
            events_processed = 0
            notifications_sent = 0
            errors = []

            logger.info(f"Processing {len(events_data)} {event_type} events")

            for row in events_data:
                try:
                    # Parse event based on type
                    event_data = self._parse_event_row(row, event_type)

                    if not event_data or not event_data.get('event_id'):
                        logger.warning(f"Skipping invalid row: {row}")
                        continue

                    events_processed += 1

                    # Check if event needs notification
                    notifications = self._check_notification_needed(
                        event_data=event_data,
                        event_type=event_type,
                        notification_rules=notification_rules,
                        current_time=current_time,
                        trigger_type=trigger_type
                    )

                    # Send notifications
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

    def _parse_event_row(
            self,
            row: List[Any],
            event_type: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a row from Google Sheets into event data."""
        try:
            if event_type == 'concerts':
                if len(row) < 6:
                    return None
                return {
                    'event_id': row[0],
                    'band': row[1],
                    'venue': row[2],
                    'date': row[3],
                    'time': row[4],
                    'location': row[5],
                    'notified_at': row[6] if len(row) > 6 else '',
                    'notes': row[7] if len(row) > 7 else ''
                }
            elif event_type == 'interviews':
                if len(row) < 7:
                    return None
                return {
                    'event_id': row[0],
                    'company': row[1],
                    'position': row[2],
                    'date': row[3],
                    'time': row[4],
                    'interviewer': row[5],
                    'stage': row[6],
                    'notified_at': row[7] if len(row) > 7 else '',
                    'prep_notes': row[8] if len(row) > 8 else ''
                }
            else:  # study
                if len(row) < 6:
                    return None
                return {
                    'event_id': row[0],
                    'course': row[1],
                    'topic': row[2],
                    'date': row[3],
                    'duration': row[4],
                    'priority': row[5],
                    'notified_at': row[6] if len(row) > 6 else '',
                    'resources': row[7] if len(row) > 7 else ''
                }
        except Exception as e:
            logger.error(f"Error parsing row: {str(e)}")
            return None

    def _check_notification_needed(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_rules: List[Dict[str, int]],
            current_time: datetime,
            trigger_type: str
    ) -> List[str]:
        """
        Check which notifications are needed for an event.

        Returns:
            List of notification labels that should be sent
        """
        notifications_needed = []

        try:
            # Parse event datetime
            event_datetime = self._parse_event_datetime(
                event_data.get('date', ''),
                event_data.get('time', ''),
                self.timezone
            )

            if not event_datetime:
                logger.warning(f"Could not parse datetime for event {event_data.get('event_id')}")
                return notifications_needed

            # Skip past events
            if event_datetime < current_time:
                logger.debug(f"Skipping past event {event_data.get('event_id')}")
                return notifications_needed

            # Check each notification rule
            for rule in notification_rules:
                notification_time = event_datetime - timedelta(
                    days=rule['days'],
                    hours=rule['hours']
                )

                label = rule['label']

                # Special handling for study 6pm notification
                if event_type == 'study' and label == '1_day_before_6pm':
                    # Set notification time to 6pm the day before
                    notification_time = (event_datetime - timedelta(days=1)).replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )

                # Check if we're in the notification window
                # Allow 2-hour window for hourly checks, 6-hour window for daily checks
                window_hours = 2 if trigger_type == 'hourly-urgent' else 6
                window_start = notification_time - timedelta(hours=window_hours / 2)
                window_end = notification_time + timedelta(hours=window_hours / 2)

                if window_start <= current_time <= window_end:
                    # Check if already notified
                    if not self._is_already_notified(
                            event_data.get('event_id'),
                            event_type,
                            label
                    ):
                        notifications_needed.append(label)
                        logger.info(
                            f"Notification needed for {event_data.get('event_id')}: {label}"
                        )

            return notifications_needed

        except Exception as e:
            logger.error(f"Error checking notifications: {str(e)}")
            return notifications_needed

    def _parse_event_datetime(
            self,
            date_str: str,
            time_str: str,
            timezone: pytz.timezone
    ) -> Optional[datetime]:
        """Parse date and time strings into timezone-aware datetime."""
        try:
            # Expected format: YYYY-MM-DD and HH:MM
            datetime_str = f"{date_str} {time_str}"
            naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            return timezone.localize(naive_dt)
        except Exception as e:
            logger.error(f"Error parsing datetime '{date_str} {time_str}': {str(e)}")
            return None

    def _is_already_notified(
            self,
            event_id: str,
            event_type: str,
            notification_label: str
    ) -> bool:
        """Check if notification has already been sent."""
        try:
            notification_key = f"{event_id}#{notification_label}"

            response = self.table.get_item(
                Key={
                    'event_id': notification_key,
                    'event_type': event_type
                }
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
            # Send notification
            results = self.notification_manager.send_notification(
                event_data=event_data,
                event_type=event_type,
                notification_label=notification_label
            )

            # Track in DynamoDB if at least one channel succeeded
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
                            'discord': results.get('discord', False)
                        },
                        'event_details': event_data
                    }
                )

                logger.info(
                    f"Notification tracked: {notification_key} for {event_type}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error sending/tracking notification: {str(e)}")
            return False