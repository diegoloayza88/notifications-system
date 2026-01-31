import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3
import requests

logger = logging.getLogger()


class NotificationManager:
    """Manager for sending notifications via email, Discord, and Calendar."""

    def __init__(self):
        """Initialize notification clients."""
        self.sns_client = boto3.client('sns')
        self.secrets_client = boto3.client('secretsmanager')
        self.sns_topic_arn = os.environ['SNS_TOPIC_ARN']
        self.discord_webhook_url = self._get_discord_webhook()

    def _get_discord_webhook(self) -> str:
        """Retrieve Discord webhook URL from Secrets Manager."""
        try:
            secret_arn = os.environ['DISCORD_WEBHOOK']
            response = self.secrets_client.get_secret_value(SecretId=secret_arn)
            return response['SecretString']
        except Exception as e:
            logger.error(f"Error retrieving Discord webhook: {str(e)}")
            raise

    def send_notification(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_label: str,
            sheets_client=None,
            calendar_id: str = ''
    ) -> Dict[str, bool]:
        """Send notification via all channels."""
        results = {
            'email': False,
            'discord': False,
            'calendar': False
        }

        try:
            # Format messages
            email_message = self._format_email_message(event_data, event_type, notification_label)
            discord_message = self._format_discord_message(event_data, event_type, notification_label)

            # Send email via SNS
            try:
                self.sns_client.publish(
                    TopicArn=self.sns_topic_arn,
                    Subject=email_message['subject'],
                    Message=email_message['body']
                )
                results['email'] = True
                logger.info(f"Email sent for event {event_data.get('event_id')}")
            except Exception as e:
                logger.error(f"Error sending email: {str(e)}")

            # Send Discord notification
            try:
                response = requests.post(
                    self.discord_webhook_url,
                    json=discord_message,
                    timeout=10
                )
                response.raise_for_status()
                results['discord'] = True
                logger.info(f"Discord notification sent for event {event_data.get('event_id')}")
            except Exception as e:
                logger.error(f"Error sending Discord notification: {str(e)}")

            # Create Google Calendar event
            if sheets_client and calendar_id:
                try:
                    event_id_str = event_data.get('event_id', '')

                    # Check if event already exists
                    if not sheets_client.check_calendar_event_exists(calendar_id, event_id_str):
                        logger.info(f"Creating calendar event for {event_id_str}")
                        cal_event_id = sheets_client.create_calendar_event(
                            calendar_id=calendar_id,
                            event_data=event_data,
                            event_type=event_type
                        )
                        results['calendar'] = True
                        logger.info(f"Calendar event created: {cal_event_id}")
                    else:
                        logger.info(f"Calendar event already exists for {event_id_str}")
                        results['calendar'] = True

                except Exception as e:
                    logger.error(f"Error with calendar event: {str(e)}")

            return results

        except Exception as e:
            logger.error(f"Error in send_notification: {str(e)}")
            return results

    def _format_email_message(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_label: str
    ) -> Dict[str, str]:
        """Format email message based on event type."""

        if event_type == 'concerts':
            subjects = {
                '2_weeks_before': f"🎸 Concierto en 2 semanas - {event_data.get('band', 'N/A')}",
                '1_day_before': f"🎸 ¡Mañana es el concierto de {event_data.get('band', 'N/A')}!",
                '4_hours_before': f"⏰ En 4 horas - Concierto de {event_data.get('band', 'N/A')}"
            }

            body = f"""¡Hola Diego!

Recordatorio de concierto:

🎤 Artista: {event_data.get('band', 'N/A')}
📍 Lugar: {event_data.get('venue', 'N/A')}
📅 Fecha: {event_data.get('date', 'N/A')}
🕒 Hora: {event_data.get('time', 'N/A')}
🌎 Ubicación: {event_data.get('location', 'N/A')}

{event_data.get('notes', '')}

¡Disfrútalo! 🎉
"""

        elif event_type == 'interviews':
            subjects = {
                '1_week_before': f"💼 Entrevista en 1 semana - {event_data.get('company', 'N/A')}",
                '1_day_before': f"💼 Mañana: Entrevista con {event_data.get('company', 'N/A')}",
                '1_hour_before': f"⏰ En 1 hora - Entrevista con {event_data.get('company', 'N/A')}"
            }

            body = f"""Hola Diego,

Recordatorio de entrevista:

🏢 Empresa: {event_data.get('company', 'N/A')}
👔 Posición: {event_data.get('position', 'N/A')}
📅 Fecha: {event_data.get('date', 'N/A')}
🕒 Hora: {event_data.get('time', 'N/A')}
👤 Entrevistador: {event_data.get('interviewer', 'N/A')}
📊 Etapa: {event_data.get('stage', 'N/A')}

{event_data.get('prep_notes', '')}

¡Mucha suerte! 💪
"""

        else:  # study
            subjects = {
                '1_day_before_6pm': f"📚 Recordatorio de estudio - {event_data.get('course', 'N/A')}"
            }

            body = f"""Hola Diego,

Recordatorio de sesión de estudio:

📖 Curso: {event_data.get('course', 'N/A')}
📝 Tema: {event_data.get('topic', 'N/A')}
📅 Fecha: {event_data.get('date', 'N/A')}
⏱️ Duración: {event_data.get('duration', 'N/A')}
⭐ Prioridad: {event_data.get('priority', 'N/A')}

{event_data.get('resources', '')}

¡A aprender! 🚀
"""

        return {
            'subject': subjects.get(notification_label, 'Recordatorio'),
            'body': body
        }

    def _format_discord_message(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_label: str
    ) -> Dict[str, Any]:
        """Format Discord embed message based on event type."""

        colors = {
            'concerts': 0xFF0000,
            'interviews': 0x0099FF,
            'study': 0x00FF00
        }

        emojis = {
            'concerts': {'2_weeks_before': '🎸', '1_day_before': '🎉', '4_hours_before': '⏰'},
            'interviews': {'1_week_before': '💼', '1_day_before': '🎯', '1_hour_before': '⚡'},
            'study': {'1_day_before_6pm': '📚'}
        }

        emoji = emojis.get(event_type, {}).get(notification_label, '🔔')

        if event_type == 'concerts':
            title = f"{emoji} Recordatorio de Concierto"
            fields = [
                {'name': '🎤 Artista', 'value': event_data.get('band', 'N/A'), 'inline': True},
                {'name': '📍 Venue', 'value': event_data.get('venue', 'N/A'), 'inline': True},
                {'name': '📅 Fecha', 'value': event_data.get('date', 'N/A'), 'inline': True},
                {'name': '🕒 Hora', 'value': event_data.get('time', 'N/A'), 'inline': True},
            ]

        elif event_type == 'interviews':
            title = f"{emoji} Recordatorio de Entrevista"
            fields = [
                {'name': '🏢 Empresa', 'value': event_data.get('company', 'N/A'), 'inline': True},
                {'name': '👔 Posición', 'value': event_data.get('position', 'N/A'), 'inline': True},
                {'name': '📅 Fecha', 'value': event_data.get('date', 'N/A'), 'inline': True},
                {'name': '🕒 Hora', 'value': event_data.get('time', 'N/A'), 'inline': True},
            ]

        else:  # study
            title = f"{emoji} Recordatorio de Estudio"
            fields = [
                {'name': '📖 Curso', 'value': event_data.get('course', 'N/A'), 'inline': True},
                {'name': '📝 Tema', 'value': event_data.get('topic', 'N/A'), 'inline': True},
                {'name': '📅 Fecha', 'value': event_data.get('date', 'N/A'), 'inline': True},
            ]

        return {
            'embeds': [{
                'title': title,
                'color': colors.get(event_type, 0x808080),
                'fields': fields,
                'footer': {
                    'text': f"Event ID: {event_data.get('event_id', 'N/A')}"
                },
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
