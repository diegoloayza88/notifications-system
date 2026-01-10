# Deployment Guide

## Automatic Deployment (GitHub Actions)

### Lambda Function

Push cambios al código Python:
```bash
# Hacer cambios en src/lambda/
git add src/
git commit -m "Update Lambda logic"
git push origin main

# GitHub Actions desplegará automáticamente a DEV
```

Deploy manual a PROD:
```bash
# Via GitHub UI:
# Actions → Deploy Lambda Function → Run workflow
# Seleccionar environment: prod
```

### Infraestructura (Terraform)

Para cambios de infraestructura:
```bash
# Hacer cambios en terraform/
git add terraform/
git commit -m "Update infrastructure"
git push origin main

# Ir a Terraform Cloud UI
# → Workspace → Confirm & Apply
```

## Manual Deployment (Local)

### Desplegar Lambda
```bash
# Desplegar a DEV
./scripts/deploy-lambda.sh dev

# Desplegar a PROD
./scripts/deploy-lambda.sh prod
```

### Desplegar Infraestructura
```bash
# DEV
cd terraform/environments/dev
aws sso login
terraform apply

# PROD
cd terraform/environments/prod
aws sso login
terraform apply
```

## Testing Lambda Locally
```bash
# Invocar Lambda directamente
aws lambda invoke \
  --function-name event-notifications-dev-processor \
  --payload '{"trigger_type":"manual"}' \
  response.json

cat response.json
```

## Rollback

### Rollback Lambda Code
```bash
# Listar versiones
aws lambda list-versions-by-function \
  --function-name event-notifications-prod-processor

# Actualizar alias a versión anterior
aws lambda update-alias \
  --function-name event-notifications-prod-processor \
  --name PROD \
  --function-version 5
```

### Rollback Infraestructura
```bash
# En Terraform Cloud:
# Workspace → States → Seleccionar state anterior → Rollback
```

## Monitoring

### Ver logs
```bash
# Logs en tiempo real
aws logs tail /aws/lambda/event-notifications-prod-processor --follow

# Logs de las últimas 2 horas
aws logs tail /aws/lambda/event-notifications-prod-processor --since 2h
```

### Ver métricas
```bash
# Invocaciones
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=event-notifications-prod-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting

### Lambda no se actualiza
```bash
# Verificar que GitHub Actions tiene permisos
# Settings → Secrets → Verificar AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY

# Verificar que la función existe
aws lambda get-function --function-name event-notifications-dev-processor
```

### Errores en Terraform
```bash
# Verificar variables en Terraform Cloud
# Workspace → Variables → Verificar todas las variables requeridas

# Ver estado actual
terraform show
```
