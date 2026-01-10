# Event Notifications System

Sistema automatizado de notificaciones para conciertos, entrevistas y sesiones de estudio usando AWS Lambda, Terraform y GitHub Actions.

## 🏗️ Arquitectura

- **AWS Lambda**: Procesamiento de eventos
- **EventBridge**: Triggers programados
- **DynamoDB**: Tracking de notificaciones
- **SNS**: Notificaciones por email
- **Secrets Manager**: Credenciales seguras
- **Google Sheets**: Fuente de datos

## 📋 Prerequisitos

- AWS CLI configurado
- Terraform >= 1.5.0
- Python 3.11
- Cuenta de Google Cloud con Sheets API habilitada
- Discord webhook (opcional)

## 🚀 Setup Inicial

### 1. Configurar Google Sheets API
```bash
# Crear proyecto en Google Cloud Console
# Habilitar Google Sheets API
# Crear Service Account
# Descargar credenciales JSON
```

### 2. Crear Google Sheets

Crear 3 sheets con las siguientes estructuras:

**Conciertos:**
```
EventID | Band/Artist | Venue | Date | Time | Location | NotifiedAt | Notes
```

**Entrevistas:**
```
EventID | Company | Position | Date | Time | Interviewer | Stage | NotifiedAt | PrepNotes
```

**Estudio:**
```
EventID | Course | Topic | Date | Duration | Priority | NotifiedAt | Resources
```

### 3. Configurar Secrets en GitHub
```bash
# GitHub Repository Settings > Secrets
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

### 4. Configurar Variables de Terraform

Editar `terraform/environments/prod/terraform.tfvars`:
```hcl
notification_emails = ["tu@email.com"]
concerts_sheet_id   = "tu-sheet-id"
interviews_sheet_id = "tu-sheet-id"
study_sheet_id      = "tu-sheet-id"
```

### 5. Desplegar Infraestructura
```bash
cd terraform/environments/prod

# Inicializar Terraform
terraform init

# Revisar plan
terraform plan

# Aplicar
terraform apply
```

### 6. Configurar Secrets en AWS
```bash
# Google Credentials
aws secretsmanager put-secret-value \
  --secret-id event-notifications-prod/google-credentials \
  --secret-string file://google-credentials.json

# Discord Webhook
aws secretsmanager put-secret-value \
  --secret-id event-notifications-prod/discord-webhook \
  --secret-string "https://discord.com/api/webhooks/..."
```

## 📅 Horarios de Notificaciones

### Conciertos
- 2 semanas antes
- 1 día antes
- 4 horas antes

### Entrevistas
- 1 semana antes
- 1 día antes
- 1 hora antes

### Estudio
- 1 día antes a las 6pm GMT-5

## 🔄 CI/CD Pipeline

El pipeline se ejecuta automáticamente en:

1. **PR**: Terraform plan + Python lint
2. **Push a main**: Deploy a Dev
3. **Manual**: Deploy a Prod (workflow_dispatch)

## 📊 Monitoreo
```bash
# Ver logs de Lambda
aws logs tail /aws/lambda/event-notifications-prod-processor --follow

# Ver métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=event-notifications-prod-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## 🧪 Testing Local
```bash
# Instalar dependencias
pip install -r src/requirements.txt

# Ejecutar tests
pytest tests/ -v

# Test de Lambda localmente
python -c "
from src.lambda.handler import main
result = main({'trigger_type': 'manual'}, None)
print(result)
"
```

## 🔧 Troubleshooting

### Lambda no encuentra credenciales
```bash
aws secretsmanager get-secret-value \
  --secret-id event-notifications-prod/google-credentials
```

### Notificaciones no se envían
```bash
# Verificar DynamoDB
aws dynamodb scan --table-name event-notifications-prod-events

# Verificar SNS
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:event-notifications-prod-notifications
```

## 📝 Mantenimiento

### Actualizar Lambda
```bash
# Via GitHub Actions (recomendado)
git commit -am "Update lambda"
git push

# Manual
./scripts/deploy-lambda.sh prod
```

### Actualizar Infraestructura
```bash
cd terraform/environments/prod
terraform plan
terraform apply
```

## 🔐 Seguridad

- Credenciales en Secrets Manager
- Encryption at rest (DynamoDB, S3)
- IAM roles con permisos mínimos
- VPC endpoints (opcional)

## 📈 Costos Estimados

- Lambda: ~$0.20/mes (100 invocaciones/día)
- DynamoDB: ~$0.25/mes (on-demand)
- SNS: ~$0.50/mes (emails)
- Secrets Manager: ~$0.40/mes
- **Total: ~$1.35/mes**

## 🤝 Contribuir

1. Fork el repo
2. Crear branch (`git checkout -b feature/amazing`)
3. Commit (`git commit -m 'Add feature'`)
4. Push (`git push origin feature/amazing`)
5. Abrir PR

## 📄 Licencia

MIT