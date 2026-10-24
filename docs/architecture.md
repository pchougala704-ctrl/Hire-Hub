# Architecture

HireHub uses a Flask application factory and separate web and API blueprints. Routes perform request parsing and response rendering; service classes enforce account, job, application, matching, resume, and audit rules; repositories encapsulate common user, job, and application queries; domain models represent role-specific users and jobs.

MongoDB is initialized once per app factory and exposed through Flask's application extensions. Collections are created by normal MongoDB writes, and `scripts/create_indexes.py` provisions the indexes used for lookup, filtering, and sorting.

Authentication uses signed Flask sessions with HttpOnly, SameSite=Lax cookies. Public registration is restricted to candidates and recruiters. Administrative users must be provisioned through a trusted process. State-changing form and API requests require a session CSRF token.

Resume files use generated storage names and metadata records. Downloads go through an authenticated endpoint rather than exposing the upload directory as static content.
