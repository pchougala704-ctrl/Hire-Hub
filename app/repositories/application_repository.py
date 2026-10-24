from app.repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository):
    collection_name = "applications"

    def create(self, document):
        return self.collection.insert_one(document).inserted_id

    def for_candidate(self, candidate_id):
        return list(self.collection.find({"candidate_id": candidate_id}).sort("applied_at", -1))
