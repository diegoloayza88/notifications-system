import os
import logging
from typing import Dict, Any
from datetime import datetime
import boto3
import requests

logger = logging.getLogger()


class NotificationManager:
    """Manager for sending notifications via email and Discord."""

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
            notification_label: str
    ) -> Dict[str, bool]:
        """
        Send notification via email and Discord.

        Args:
            event_data: Event information
            event_type: Type of event (concerts, interviews, study)
            notification_label: Label for this notification timing

        Returns:
            Dictionary with success status for each channel
        """
        results = {
            'email': False,
            'discord': False
        }

        try:
            # Format messages
            email_message = self._format_email_message(
                event_data, event_type, notification_label
            )
            discord_message = self._format_discord_message(
                event_data, event_type, notification_label
            )

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

        templates = {
            'concerts': {
                '2_weeks_before': {
                    'subject': '🎸 Concierto en 2 semanas - {band}',
                    'body': '''¡Hola Diego!

Te recuerdo que tienes un concierto próximo:

🎤 Artista: {band}
📍 Lugar: {venue}
📅 Fecha: {date}
🕒 Hora: {time}
🌎 Ubicación: {location}

{notes}

¡Prepara todo con anticipación!
'''
                },
                '1_day_before': {
                    'subject': '🎸 ¡Mañana es el concierto de {band}!',
                    'body': '''¡Hola Diego!

¡Mañana es el gran día!

🎤 Artista: {band}
📍 Lugar: {venue}
🕒 Hora: {time}
🌎 Ubicación: {location}

Revisa:
- Entradas impresas o descargadas
- Transporte al venue
- Horario de llegada

{notes}

¡A disfrutar! 🎉
'''
                },
                '4_hours_before': {
                    'subject': '⏰ En 4 horas - Concierto de {band}',
                    'body': '''¡Diego!

¡Ya casi es hora! El concierto de {band} comienza en 4 horas.

🕒 Hora de inicio: {time}
📍 Lugar: {venue}

Verifica:
- Tienes tus entradas
- Sal con tiempo suficiente
- Carga tu celular

¡Disfrútalo! 🤘
'''
                }
            },
            'interviews': {
                '1_week_before': {
                    'subject': '💼 Entrevista en 1 semana - {company}',
                    'body': '''Hola Diego,

Tienes una entrevista programada para dentro de 1 semana:

🏢 Empresa: {company}
👔 Posición: {position}
📅 Fecha: {date}
🕒 Hora: {time}
👤 Entrevistador: {interviewer}
📊 Etapa: {stage}

Tiempo para preparar:
{prep_notes}

¡Éxito! 💪
'''
                },
                '1_day_before': {
                    'subject': '💼 Mañana: Entrevista con {company}',
                    'body': '''Hola Diego,

¡Mañana es tu entrevista!

🏢 Empresa: {company}
👔 Posición: {position}
🕒 Hora: {time}
👤 Entrevistador: {interviewer}
📊 Etapa: {stage}

Últimos preparativos:
{prep_notes}

Revisa:
- Link de la reunión (si es virtual)
- Documentos necesarios
- Preguntas que quieres hacer

¡Mucha suerte! 🍀
'''
                },
                '1_hour_before': {
                    'subject': '⏰ En 1 hora - Entrevista con {company}',
                    'body': '''¡Diego!

Tu entrevista con {company} es en 1 HORA.

🕒 Hora: {time}
👤 Entrevistador: {interviewer}
📊 Etapa: {stage}

Checklist final:
✅ Ambiente listo (si es virtual)
✅ Agua a mano
✅ Notas de repaso
✅ Actitud positiva

¡Tú puedes! 💪
'''
                }
            },
            'study': {
                '1_day_before_6pm': {
                    'subject': '📚 Recordatorio de estudio - {course}',
                    'body': '''Hola Diego,

Recuerda tu sesión de estudio programada para mañana:

📖 Curso: {course}
📝 Tema: {topic}
📅 Fecha: {date}
⏱️ Duración: {duration}
⭐ Prioridad: {priority}

Recursos:
{resources}

¡A aprender! 🚀
'''
                }
            }
        }

        template = templates.get(event_type, {}).get(notification_label, {})

        if event_type == 'concerts':
            return {
                'subject': template['subject'].format(band=event_data.get('band', 'N/A')),
                'body': template['body'].format(
                    band=event_data.get('band', 'N/A'),
                    venue=event_data.get('venue', 'N/A'),
                    date=event_data.get('date', 'N/A'),
                    time=event_data.get('time', 'N/A'),
                    location=event_data.get('location', 'N/A'),
                    notes=event_data.get('notes', '')
                )
            }
        elif event_type == 'interviews':
            return {
                'subject': template['subject'].format(company=event_data.get('company', 'N/A')),
                'body': template['body'].format(
                    company=event_data.get('company', 'N/A'),
                    position=event_data.get('position', 'N/A'),
                    date=event_data.get('date', 'N/A'),
                    time=event_data.get('time', 'N/A'),
                    interviewer=event_data.get('interviewer', 'N/A'),
                    stage=event_data.get('stage', 'N/A'),
                    prep_notes=event_data.get('prep_notes', '')
                )
            }
        else:  # study
            return {
                'subject': template['subject'].format(course=event_data.get('course', 'N/A')),
                'body': template['body'].format(
                    course=event_data.get('course', 'N/A'),
                    topic=event_data.get('topic', 'N/A'),
                    date=event_data.get('date', 'N/A'),
                    duration=event_data.get('duration', 'N/A'),
                    priority=event_data.get('priority', 'N/A'),
                    resources=event_data.get('resources', '')
                )
            }

    def _format_discord_message(
            self,
            event_data: Dict[str, Any],
            event_type: str,
            notification_label: str
    ) -> Dict[str, Any]:
        """Format Discord embed message based on event type."""

        # Color codes
        colors = {
            'concerts': 0xFF0000,  # Red
            'interviews': 0x0099FF,  # Blue
            'study': 0x00FF00  # Green
        }

        # Emoji mapping
        emojis = {
            'concerts': {
                '2_weeks_before': '🎸',
                '1_day_before': '🎉',
                '4_hours_before': '⏰'
            },
            'interviews': {
                '1_week_before': '💼',
                '1_day_before': '🎯',
                '1_hour_before': '⚡'
            },
            'study': {
                '1_day_before_6pm': '📚'
            }
        }

        emoji = emojis.get(event_type, {}).get(notification_label, '🔔')

        if event_type == 'concerts':
            title = f"{emoji} Recordatorio de Concierto"
            fields = [
                {'name': '🎤 Artista', 'value': event_data.get('band', 'N/A'), 'inline': True},
                {'name': '📍 Venue', 'value': event_data.get('venue', 'N/A'), 'inline': True},
                {'name': '📅 Fecha', 'value': event_data.get('date', 'N/A'), 'inline': True},
                {'name': '🕒 Hora', 'value': event_data.get('time', 'N/A'), 'inline': True},
                {'name': '🌎 Ubicación', 'value': event_data.get('location', 'N/A'), 'inline': False},
            ]
            if event_data.get('notes'):
                fields.append({'name': '📝 Notas', 'value': event_data['notes'], 'inline': False})

        elif event_type == 'interviews':
            title = f"{emoji} Recordatorio de Entrevista"
            fields = [
                {'name': '🏢 Empresa', 'value': event_data.get('company', 'N/A'), 'inline': True},
                {'name': '👔 Posición', 'value': event_data.get('position', 'N/A'), 'inline': True},
                {'name': '📅 Fecha', 'value': event_data.get('date', 'N/A'), 'inline': True},
                {'name': '🕒 Hora', 'value': event_data.get('time', 'N/A'), 'inline': True},
                {'name': '👤 Entrevistador', 'value': event_data.get('interviewer', 'N/A'), 'inline': True},
                {'name': '📊 Etapa', 'value': event_data.get('stage', 'N/A'), 'inline': True},
            ]
            if event_data.get('prep_notes'):
                fields.append({'name': '📝 Preparación', 'value': event_data['prep_notes'], 'inline': False})

        else:  # study
            title = f"{emoji} Recordatorio de Estudio"
            fields = [
                {'name': '📖 Curso', 'value': event_data.get('course', 'N/A'), 'inline': True},
                {'name': '📝 Tema', 'value': event_data.get('topic', 'N/A'), 'inline': True},
                {'name': '📅 Fecha', 'value': event_data.get('date', 'N/A'), 'inline': True},
                {'name': '⏱️ Duración', 'value': event_data.get('duration', 'N/A'), 'inline': True},
                {'name': '⭐ Prioridad', 'value': event_data.get('priority', 'N/A'), 'inline': True},
            ]
            if event_data.get('resources'):
                fields.append({'name': '🔗 Recursos', 'value': event_data['resources'], 'inline': False})

        return {
            'embeds': [{
                'title': title,
                'color': colors.get(event_type, 0x808080),
                'fields': fields,
                'footer': {
                    'text': f"Event ID: {event_data.get('event_id', 'N/A')} | {notification_label.replace('_', ' ').title()}"
                },
                'timestamp': datetime.utcnow().isoformat()
            }]
        }

    def send_summary_notification(
            self,
            summary: Dict[str, Any]
    ) -> None:
        """Send a daily summary notification."""
        try:
            # Email summary
            subject = f"📊 Resumen Diario - {summary.get('date', 'N/A')}"
            body = f"""Resumen de eventos procesados:

📅 Fecha: {summary.get('date', 'N/A')}
🔔 Total notificaciones enviadas: {summary.get('total_notifications', 0)}
📝 Eventos procesados: {summary.get('total_events', 0)}

Desglose:
- 🎸 Conciertos: {summary.get('concerts', 0)} notificaciones
- 💼 Entrevistas: {summary.get('interviews', 0)} notificaciones
- 📚 Estudio: {summary.get('study', 0)} notificaciones

¡Que tengas un excelente día!
"""

            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=body
            )

            logger.info("Summary notification sent")

        except Exception as e:
            logger.error(f"Error sending summary notification: {str(e)}")