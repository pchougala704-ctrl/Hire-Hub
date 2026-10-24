from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    collection_name = "users"

    def by_email(self, email):
        return self.collection.find_one({"email": email})

    def by_id(self, user_id):
        return self.collection.find_one({"_id": user_id})

    def create(self, document):
        return self.collection.insert_one(document).inserted_id

    def update(self, user_id, values):
        return self.collection.update_one({"_id": user_id}, {"$set": values})
