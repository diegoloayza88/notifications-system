#!/bin/bash

set -e

echo "🚀 Event Notifications - Initial Setup"
echo "======================================"

# 1. Check prerequisites
echo "
📋 Checking prerequisites..."
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "❌ zip required"; exit 1; }

# 2. Create initial Lambda package
echo "
📦 Creating initial Lambda package..."
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
mkdir -p terraform/environments/prod
cp lambda-initial.zip terraform/environments/prod/lambda.zip

# Cleanup
rm -rf temp-lambda lambda-initial.zip

echo "✅ Lambda packages created"

# 3. Initialize Terraform for prod
echo "
🏗️  Initializing Terraform (prod)..."
cd ../prod
terraform init
echo "✅ Prod environment initialized"

cd ../../..

# 5. Summary
echo "
✅ Initial setup complete!

Next steps:
1. Review Terraform plan:
   cd terraform/environments/prod && terraform plan

2. Deploy infrastructure:
   cd terraform/environments/prod && terraform apply

3. Push to GitHub to deploy real Lambda code:
   git add .
   git commit -m 'Initial infrastructure'
   git push origin main

4. GitHub Actions will automatically update Lambda with real code
"
