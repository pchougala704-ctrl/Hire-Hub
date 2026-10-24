# Database

HireHub uses these MongoDB collections:

* `users`: credentials hashes, roles, account state, and account basics.
* `candidates`, `recruiters`: role-specific profile data.
* `companies`: recruiter company affiliation and verification state.
* `jobs`: descriptions, skills, location, employment details, and ownership.
* `applications`: candidate/job relationship, status history fields, and recruiter notes.
* `interviews`: scheduled interview metadata.
* `resumes`: owner, safe generated filename, original display name, and file metadata.
* `notifications`: user-targeted messages and read state.
* `audit_logs`: security-relevant actions and non-secret metadata.

IDs in cross-collection relationship fields are stored as strings for stable JSON serialization; Mongo document `_id` fields remain BSON ObjectIds. The index script enforces unique user emails and adds common job, application, interview, and notification indexes.
