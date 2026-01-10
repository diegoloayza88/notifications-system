import logging
from datetime import datetime
from typing import Optional
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