from pymongo import MongoClient


def init_database(app):
    client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=3000)
    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = client[app.config["MONGO_DATABASE"]]


def get_db():
    from flask import current_app

    if "mongo_db" not in current_app.extensions:
        raise RuntimeError("MongoDB has not been initialized.")
    return current_app.extensions["mongo_db"]
