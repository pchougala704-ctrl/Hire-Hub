from app.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository):
    collection_name = "jobs"

    def find_by_id(self, job_id):
        return self.collection.find_one({"_id": job_id})

    def search(self, query, page, per_page):
        cursor = self.collection.find(query).sort("created_at", -1)
        total = self.collection.count_documents(query)
        items = list(cursor.skip((page - 1) * per_page).limit(per_page))
        return items, total

    def create(self, document):
        return self.collection.insert_one(document).inserted_id

