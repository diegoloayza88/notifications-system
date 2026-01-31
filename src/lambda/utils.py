import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import pytz

logger = logging.getLogger()


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse duration string to minutes.

    Args:
        duration_str: Duration string like '2h', '30m', '1.5h'

    Returns:
        Duration in minutes or None if invalid
    """
    try:
        duration_str = duration_str.strip().lower()

        if 'h' in duration_str:
            hours = float(duration_str.replace('h', ''))
            return int(hours * 60)
        elif 'm' in duration_str:
            return int(duration_str.replace('m', ''))
        else:
            # Assume hours if no unit
            return int(float(duration_str) * 60)
    except Exception as e:
        logger.error(f"Error parsing duration '{duration_str}': {str(e)}")
        return None


def format_datetime_for_display(
        dt: datetime,
        timezone: pytz.timezone,
        format_str: str = '%Y-%m-%d %H:%M %Z'
) -> str:
    """Format datetime for display in notifications."""
    try:
        return dt.astimezone(timezone).strftime(format_str)
    except Exception as e:
        logger.error(f"Error formatting datetime: {str(e)}")
        return str(dt)


def calculate_time_until_event(
        event_datetime: datetime,
        current_time: datetime
) -> str:
    """Calculate human-readable time until event."""
    try:
        delta = event_datetime - current_time

        if delta.days > 0:
            return f"{delta.days} día(s)"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hora(s)"
        else:
            minutes = delta.seconds // 60
            return f"{minutes} minuto(s)"
    except Exception as e:
        logger.error(f"Error calculating time until event: {str(e)}")
        return "N/A"


def parse_event_row(row: List[Any], event_type: str) -> Optional[Dict[str, Any]]:
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
                'resources': row[7] if len(row) > 7 else ''
            }
    except Exception as e:
        logger.error(f"Error parsing row: {str(e)}")
        return None


def parse_event_datetime(date_str: str, time_str: str, timezone) -> Optional[datetime]:
    """Parse date and time strings into timezone-aware datetime."""
    try:
        # Limpiar espacios en blanco
        date_str = date_str.strip() if date_str else ''
        time_str = time_str.strip() if time_str else ''

        # Validar que tenemos ambos valores
        if not date_str or not time_str:
            logger.warning(f"Missing date or time: date='{date_str}', time='{time_str}'")
            return None

        datetime_str = f"{date_str} {time_str}"
        naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        return timezone.localize(naive_dt)
    except Exception as e:
        logger.error(f"Error parsing datetime '{date_str}' '{time_str}': {str(e)}")
        return None