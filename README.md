# HireHub

HireHub is a modular Flask and MongoDB job portal for candidates, recruiters, and administrators. It includes server-rendered responsive pages and a JSON API for authentication, jobs, applications, interviews, and analytics.

## Run locally

1. Install Python 3.12 or newer and MongoDB.
2. Create a virtual environment and install the dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`, set a strong `SECRET_KEY`, and configure `MONGO_URI` if MongoDB is not available at its local default.
4. Start MongoDB, then run:

   ```powershell
   python run.py
   ```

   Open <http://127.0.0.1:5000>.

The first administrator is created through the Flask shell or a trusted database provisioning process; public registration only allows candidate and recruiter accounts. Never expose a production admin-creation endpoint.

## Architecture

`app/routes` handles HTTP and page rendering, `app/services` owns business rules, `app/repositories` owns MongoDB access, and `app/models` contains domain objects. The application factory in `app/__init__.py` configures the database, session cookies, blueprints, and error handling. See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md), and [docs/database.md](docs/database.md).

## Configuration and security

Configuration is read from environment variables. `.env` is ignored by Git. Passwords are stored as Werkzeug hashes; authenticated routes enforce roles and ownership. Resume uploads are stored under the configured upload folder with generated names and are served only to authorized users. Set `COOKIE_SECURE=true` behind HTTPS.

## Tests and data

Run tests with `python -m pytest`. Create indexes with `python scripts/create_indexes.py` after configuring `.env`. `python scripts/seed_data.py` inserts 20 candidates, 10 recruiters, 5 companies, 30 jobs, 50 applications, and 15 interviews; its shared demo password is printed by the script. Both scripts are intended for development databases only.

Candidates can manage profiles and private resumes, save and apply to jobs, track application statuses and interviews, and view skills-based recommendations. Recruiters can manage company profiles and jobs, search candidates, review applications, and schedule interviews. Administrators can manage accounts and company verification, moderate jobs, review audit activity, and export CSV reports.

## API

API endpoints are rooted at `/api`. Responses use a consistent `success`, `message`, and `data` or `error_code` envelope. An endpoint overview and example requests are in [docs/api.md](docs/api.md).
