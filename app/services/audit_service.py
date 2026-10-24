from datetime import datetime, timezone


class AuditService:
    def __init__(self, db):
        self.logs = db["audit_logs"]

    def record(self, user_id, action, resource, resource_id="", metadata=None):
        self.logs.insert_one({
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "resource": resource,
            "resource_id": str(resource_id),
            "timestamp": datetime.now(timezone.utc),
            "metadata": metadata or {},
        })
