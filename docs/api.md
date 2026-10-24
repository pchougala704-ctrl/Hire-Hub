# REST API

All endpoints are prefixed with `/api` and return JSON containing `success`, `message`, and `data`; errors contain `success`, `message`, and `error_code`. Authentication uses the same session cookie as the web app. Fetch the CSRF token from `GET /api/auth/csrf` and send it as `X-CSRF-Token` on state-changing requests.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/auth/register`, `/auth/login`, `/auth/logout` | Public / authenticated |
| GET | `/auth/me`, `/auth/csrf` | Authenticated / public |
| GET | `/jobs`, `/jobs/<id>` | Public |
| POST | `/jobs` | Recruiter |
| PUT, DELETE | `/jobs/<id>` | Owning recruiter or admin |
| POST | `/jobs/<id>/apply` | Candidate |
| GET, PUT | `/candidates/<id>` | Owner, related recruiter, or admin / owner |
| GET | `/candidates?skill=python&location=remote` | Recruiter |
| GET | `/saved-jobs` | Candidate |
| GET, PUT | `/company` | Recruiter |
| GET | `/applications`, `/applications/<id>` | Authenticated and scoped |
| PUT | `/applications/<id>/status` | Owning recruiter, candidate withdrawal, or admin |
| POST, GET | `/interviews` | Recruiter / authenticated |
| PUT | `/interviews/<id>` | Owning recruiter or admin |
| POST, GET, DELETE | `/resumes`, `/resumes/<id>` | Candidate / authorized download |
| GET | `/recommendations` | Candidate |
| GET | `/analytics/<candidate\|recruiter\|admin>` | Matching role or admin |
| GET | `/admin/users`, `/admin/companies`, `/admin/audit-logs` | Admin |
| PUT | `/admin/users/<id>/active`, `/admin/companies/<id>/verification` | Admin |
| PUT | `/admin/jobs/<id>/status` | Admin |
| GET | `/admin/audit-logs` | Admin |

Job search accepts `keyword`, `skill`, `location`, `work_mode`, `employment_type`, `company_id`, `salary_min`, `experience_min`, and `page`.

Administrator CSV reports are available from `/admin/reports`; application reports accept `date_from`, `date_to`, `status`, `company_id`, and `location`. Job and skill-demand reports accept date, company, and location filters. CSV fields are escaped for spreadsheet formula safety.

Example:

```javascript
const { data: tokenResponse } = await fetch("/api/auth/csrf").then(r => r.json());
const response = await fetch("/api/jobs", { credentials: "same-origin" });
```
