class NotificationService:
    def __init__(self, db):
        self.notifications = db["notifications"]

    def list_for_user(self, user, limit=100):
        return list(
            self.notifications.find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(limit)
        )

    def mark_all_read(self, user):
        self.notifications.update_many(
            {"user_id": str(user["_id"])},
            {"$set": {"read": True}},
        )
