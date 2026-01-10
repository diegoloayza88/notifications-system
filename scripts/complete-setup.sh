#!/bin/bash

set -e

echo "🚀 Event Notifications - Complete Setup"
echo "========================================"

# 1. Check prerequisites
echo ""
echo "📋 Checking prerequisites..."
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "❌ zip required"; exit 1; }

echo "✅ All prerequisites found"

# 2. Create directory structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p terraform/modules/{lambda,eventbridge,dynamodb,sns,secrets}
mkdir -p terraform/environments/{prod}
mkdir -p src/lambda
mkdir -p .github/workflows

echo "✅ Directories created"

# 3. Create backend.tf files
echo ""
echo "📝 Creating Terraform backend configurations..."

cat > terraform/environments/prod/backend.tf << 'BACKEND_PROD'
terraform {
  cloud {
    organization = "portfolio-diego"

    workspaces {
      name = "event-notifications-prod"
    }
  }
}
BACKEND_PROD

echo "✅ Backend configs created"

# 4. Create outputs.tf files
echo ""
echo "📝 Creating Terraform outputs..."

cat > terraform/environments/prod/outputs.tf << 'OUTPUTS'
output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = module.lambda.function_arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = module.lambda.function_name
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = module.dynamodb.table_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic"
  value       = module.sns.topic_arn
}
OUTPUTS

echo "✅ Outputs created"

# 5. Create initial Lambda package
echo ""
echo "📦 Creating initial Lambda package..."
mkdir -p temp-lambda

cat > temp-lambda/handler.py << 'HANDLER'
def main(event, context):
    print("Initial placeholder Lambda - will be updated by CI/CD")
    return {
        'statusCode': 200,
        'body': 'Placeholder function'
    }
HANDLER

cd temp-lambda
zip -q -r ../lambda-initial.zip .
cd ..

# Copy to environment directories
cp lambda-initial.zip terraform/environments/prod/lambda.zip

# Cleanup
rm -rf temp-lambda lambda-initial.zip

echo "✅ Lambda packages created"

# 6. Create .gitignore
echo ""
echo "📝 Creating .gitignore..."

cat > .gitignore << 'GITIGNORE'
# Terraform
**/.terraform/*
*.tfstate
*.tfstate.*
*.tfvars
.terraformrc
terraform.rc

# Lambda packages
terraform/environments/*/lambda.zip
lambda*.zip

# Python
__pycache__/
*.py[cod]
*$py.class
.Python
build/
dist/
*.egg-info/
venv/
.venv/
ENV/
env/

# Secrets
google-credentials.json
secrets.json
*.pem
*.key

# IDEs
.vscode/
.idea/
*.swp
.DS_Store

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# Logs
*.log
GITIGNORE

echo "✅ .gitignore created"

# 7. Summary
echo ""
echo "✅ Setup complete!"
echo ""
echo "⚠️  IMPORTANT: Before proceeding, you need to:"
echo ""
echo "1. Edit backend.tf files and change 'TU_ORGANIZACION':"
echo "   - terraform/environments/prod/backend.tf"
echo ""
echo "2. Create the main Terraform files with the modules I provided earlier"
echo ""
echo "3. Then initialize Terraform:"
echo "   cd terraform/environments/prod"
echo "   terraform init"
echo ""
echo "Files created:"
echo "  ✓ Directory structure"
echo "  ✓ backend.tf (prod)"
echo "  ✓ outputs.tf (prod)"
echo "  ✓ lambda.zip (prod)"
echo "  ✓ .gitignore"
echo ""
echo "Still needed:"
echo "  ⚠ main.tf (prod) - with module calls"
echo "  ⚠ variables.tf (prod)"
echo "  ⚠ All module files in terraform/modules/"
echo ""
