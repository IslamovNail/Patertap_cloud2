
# PaterTap Cloud-Native AI Application

PaterTap is a student housing and roommate matching prototype.

## Features

- Browse sample housing listings
- Filter listings by city and maximum price
- Calculate illustrative roommate compatibility scores
- Optional AI housing assistant through Gemini
- Health endpoint for deployment checks

## Technology

- Python and Flask
- SQLite demo database
- HTML, CSS and JavaScript
- Gunicorn for production serving
- Render for web deployment
- Terraform scaffold for future infrastructure automation

## Run locally

Install dependencies:

    pip install -r requirements.txt

Start the app:

    python app.py

Open http://127.0.0.1:5000

## API endpoints

- `GET /healthz` — health check
- `GET /api/listings` — housing listings
- `GET /api/matches` — sample compatibility results
- `POST /api/ai` — optional AI assistant

Examples:

    /api/listings?city=Almaty&max_price=80000
    /api/matches?budget=80000&sleep=early&cleanliness=tidy&social=quiet

## Deployment on Render

Create a Web Service connected to this GitHub repository.

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Set `GEMINI_API_KEY` as a secret environment variable only if enabling the AI endpoint. Never commit API keys.

## Limitations

This is a demonstration prototype. Listings and roommate profiles are sample data, not verified real offers. The app does not yet implement user accounts, real booking, or production-grade persistent storage. Terraform files are a scaffold and do not by themselves provision cloud resources.
