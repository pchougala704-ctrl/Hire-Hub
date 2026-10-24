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

Public registration only allows candidate and recruiter accounts. Create the first administrator locally from the project folder after setting up `.env` and starting MongoDB:

```powershell
python -m scripts.create_admin
```

The command prompts for an administrator name, email, and password (at least 12 characters); the password is not echoed in the terminal. It stores a password hash and writes an audit event. Then sign in at <http://127.0.0.1:5000/admin/login>. Do not make this local provisioning script available as a public web endpoint.

## How to use HireHub

Keep MongoDB running and start the Flask server from the project folder:

```powershell
.\.venv\Scripts\Activate.ps1
python run.py
```

Open <http://127.0.0.1:5000> in your browser. The server must keep running in the terminal while you use the site. Press `Ctrl+C` in that terminal to stop it.

### Candidate

1. Select **Create account**, choose **Candidate**, fill out your name, email, and password, then submit the form. You can also sign in if you already have an account.
2. Open **Profile** to add your location, skills, education, experience, salary expectations, notice period, and preferred work mode. Save your changes; profile details help calculate job matches.
3. Open **Resume** to upload a PDF, DOC, or DOCX file no larger than 5 MB. Uploading another resume replaces the previous one.
4. Select **Find jobs** to browse roles. Search by keyword or location and narrow results by work mode and employment type. Open a job to see its description and, when signed in as a candidate, your match score.
5. On a job page, choose **Save job** to bookmark it or **Apply now** to submit an application. See bookmarked roles under **Saved** and application progress under **Applications**.
6. Check **Dashboard** for application counts, recommendations, and recent notifications. Scheduled interviews appear under **Interviews**.

### Recruiter

1. Create an account and choose **Recruiter**. Enter your company name during registration, then sign in.
2. Open **Company** to add or update company information. Newly registered companies need admin verification.
3. Choose **Post a job** or open **My jobs** to create, edit, and close your listings. Include a clear description, skills, work mode, employment type, and (if applicable) salary, experience, and deadline.
4. Open **Applications** to review candidates who applied to your jobs. Update an application to **Under review**, **Shortlist**, **Reject**, or **Select**. Once a candidate is shortlisted, use the date and time fields to schedule an interview.
5. Use **Candidates** to search active candidate profiles by skill or location. A candidate's resume is only available to a recruiter when that candidate has applied to one of the recruiter's jobs.
6. Use **Dashboard**, **Interviews**, and **Notifications** to follow recruitment activity.

### Administrator

Admin accounts are intentionally excluded from public registration and demo seed data. Create an administrator locally; do not expose the provisioning command as a public endpoint.

1. Configure `.env` (including `SECRET_KEY` and `MONGO_URI`) and make sure MongoDB is running.
2. From the project root, activate the virtual environment if needed and run:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m scripts.create_admin
   ```

3. Enter the administrator's email, name, and a password of at least 12 characters when prompted. The password is hidden while typing. Use an email address that is not already registered.
4. Start the app with `python run.py` (or restart an already-running server so it loads the current code).
5. Open <http://127.0.0.1:5000/admin/login>, sign in with the credentials you just created, and use the admin dashboard.

The administrator interface is available only to signed-in accounts with the `ADMIN` role. Admins can:

* View database-backed totals and application status analytics on **Dashboard**.
* Review **Candidates** and **Recruiters**, and activate or deactivate accounts.
* View all accounts under **Users**. The last active administrator cannot be deactivated, and an administrator cannot deactivate their own account.
* Review **Jobs** and moderate job statuses.
* Review **Applications** and their current statuses.
* Review **Companies** and verify or unverify recruiter companies.
* Download CSV exports from **Reports**.
* Review recorded platform activity under **Audit**.

To add another administrator, run `python -m scripts.create_admin` again from a trusted local shell. If `/admin/login` returns a 404 after starting the app, stop the old server with `Ctrl+C` in its terminal and start it again with `python run.py`.

### Optional demo data

For a fresh local development database, run `python -m scripts.create_indexes` and then `python -m scripts.seed_data` before starting the server. The seed script prints the shared demo password; candidate and recruiter emails follow the pattern `candidate01@example.test` and `recruiter01@example.test`. Seed data does **not** include an admin account. Do not run the seed script against a database containing users.

### Tips

* The top navigation changes based on your role. If a page redirects you to sign in or shows a permission error, sign in with an account that has the required role.
* Notifications are marked read when you open the **Notifications** page.
* If the site cannot connect to MongoDB, make sure MongoDB is running and that `MONGO_URI` in `.env` points to the correct server.
* For API access, obtain a session by registering or signing in through `/api/auth/register` or `/api/auth/login`, then send the returned session cookie and CSRF token with state-changing requests. See [docs/api.md](docs/api.md) for endpoints.

## Architecture

`app/routes` handles HTTP and page rendering, `app/services` owns business rules, `app/repositories` owns MongoDB access, and `app/models` contains domain objects. The application factory in `app/__init__.py` configures the database, session cookies, blueprints, and error handling. See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md), and [docs/database.md](docs/database.md).

## Configuration and security

Configuration is read from environment variables. `.env` is ignored by Git. Passwords are stored as Werkzeug hashes; authenticated routes enforce roles and ownership. Resume uploads are stored under the configured upload folder with generated names and are served only to authorized users. Set `COOKIE_SECURE=true` behind HTTPS.

## Tests and data

Run tests with `python -m pytest`. Create indexes with `python -m scripts.create_indexes` after configuring `.env`. `python -m scripts.seed_data` inserts 20 candidates, 10 recruiters, 5 companies, 30 jobs, 50 applications, and 15 interviews; its shared demo password is printed by the script. Both scripts are intended for development databases only.

Candidates can manage profiles and private resumes, save and apply to jobs, track application statuses and interviews, and view skills-based recommendations. Recruiters can manage company profiles and jobs, search candidates, review applications, and schedule interviews. Administrators can manage accounts and company verification, moderate jobs, review audit activity, and export CSV reports.

## API

API endpoints are rooted at `/api`. Responses use a consistent `success`, `message`, and `data` or `error_code` envelope. An endpoint overview and example requests are in [docs/api.md](docs/api.md).
