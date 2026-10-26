# PaterTap Cloud-Native AI Application

PaterTap is a student housing and roommate matching prototype. It keeps the same user interface and routes while adding a lightweight cloud deployment pattern based on AWS Lambda, API Gateway, DynamoDB, S3, CloudWatch, and IAM.

## Features

- browse sample housing listings
- filter listings by city and maximum price
- calculate illustrative roommate compatibility scores
- optional AI housing assistant via Gemini
- health endpoint for deployment checks
- Terraform configuration for AWS deployment
- GitHub Actions validation and deployment workflow

## Local run

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## API endpoints

- GET /healthz
- GET /api/listings
- GET /api/matches
- POST /api/ai

## AWS deployment overview

The project is designed for a lightweight AWS architecture:

- API Gateway receives HTTP requests
- Lambda runs Flask through aws_lambda_wsgi
- DynamoDB stores listing data when running in AWS mode
- private S3 bucket is kept isolated from public access
- CloudWatch logs capture Lambda execution details
- IAM roles grant minimal permissions

## Required secrets

Create the following in GitHub Actions secrets and AWS runtime environment:

- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_SESSION_TOKEN when using temporary credentials
- AWS_REGION (recommended)
- GEMINI_API_KEY

Do not place these values in the repository.

## Terraform

```bash
cd terraform
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
```

The packaging script builds the Lambda ZIP before deployment:

```bash
bash scripts/package_lambda.sh
```

## GitHub Actions

The workflow in `.github/workflows/terraform.yml` validates the project on pull requests and deploys to AWS on pushes to `main` after secrets are configured.

## Documentation

- docs/architecture.md
- docs/aws-setup.md
- docs/security.md
- docs/setup-guide.md
- docs/operations.md
- docs/costs.md
- docs/demo.md

## Security notes

- Never commit GEMINI_API_KEY, AWS credentials, or environment files.
- Keep the S3 bucket private.
- Use least-privilege IAM permissions.
- Validate all user input before relying on external services.

## Limitations

This is a demo prototype. Listings and roommate profiles are illustrative and should not be treated as verified market data. Production use should add authentication, stronger persistence, and more explicit business validation.
