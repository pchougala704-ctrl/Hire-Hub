from app.extensions import get_db


class BaseRepository:
    collection_name = ""

    def __init__(self, db=None):
        self.db = db if db is not None else get_db()
        self.collection = self.db[self.collection_name]
