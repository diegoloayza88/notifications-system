#!/bin/bash

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-us-east-1}

echo "🚀 Deploying Lambda to $ENVIRONMENT environment..."

# Create package directory
rm -rf package
mkdir package

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r src/requirements.txt -t package/ --quiet

# Copy source files
echo "📋 Copying source files..."
cp -r src/lambda/* package/

# Create zip
echo "🗜️  Creating deployment package..."
cd package
zip -q -r ../lambda-deploy.zip .
cd ..

# Get function name
FUNCTION_NAME=$(aws lambda list-functions \
  --region $AWS_REGION \
  --query "Functions[?contains(FunctionName, 'event-notifications-$ENVIRONMENT')].FunctionName" \
  --output text)

if [ -z "$FUNCTION_NAME" ]; then
  echo "❌ Lambda function not found for environment: $ENVIRONMENT"
  exit 1
fi

echo "📍 Found Lambda function: $FUNCTION_NAME"

# Update function code
echo "⬆️  Updating Lambda function code..."
aws lambda update-function-code \
  --region $AWS_REGION \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://lambda-deploy.zip \
  --no-cli-pager

# Wait for update
echo "⏳ Waiting for update to complete..."
aws lambda wait function-updated \
  --region $AWS_REGION \
  --function-name $FUNCTION_NAME

# Publish version
echo "📌 Publishing new version..."
VERSION=$(aws lambda publish-version \
  --region $AWS_REGION \
  --function-name $FUNCTION_NAME \
  --description "Manual deployment at $(date)" \
  --query 'Version' \
  --output text)

# Test function
echo "🧪 Testing Lambda function..."
aws lambda invoke \
  --region $AWS_REGION \
  --function-name $FUNCTION_NAME \
  --payload '{"trigger_type":"manual","test":true}' \
  --no-cli-pager \
  response.json

echo ""
echo "📊 Response:"
cat response.json | python3 -m json.tool

# Cleanup
rm -rf package lambda-deploy.zip response.json

echo ""
echo "✅ Deployment complete!"
echo "Function: $FUNCTION_NAME"
echo "Version: $VERSION"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
EOF
