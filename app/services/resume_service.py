import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.utils import secure_filename

from app.exceptions import ResumeUploadError, UnauthorizedError


class ResumeService:
    ALLOWED = {".pdf", ".doc", ".docx"}
    MIME_TYPES = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".doc": {"application/msword", "application/octet-stream"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    }

    def __init__(self, db, upload_folder):
        self.db = db
        self.folder = Path(upload_folder)
        self.resumes = db["resumes"]

    def upload(self, file, user):
        if not file or not file.filename:
            raise ResumeUploadError("Choose a resume file to upload.")
        original = secure_filename(file.filename)
        extension = Path(original).suffix.lower()
        mime = file.mimetype or mimetypes.guess_type(original)[0] or "application/octet-stream"
        if not original or extension not in self.ALLOWED or mime not in self.MIME_TYPES[extension]:
            raise ResumeUploadError("Only valid PDF, DOC, or DOCX files are accepted.")
        header = file.stream.read(8)
        file.stream.seek(0)
        signatures = {
            ".pdf": header.startswith(b"%PDF-"),
            ".doc": header.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
            ".docx": header.startswith(b"PK"),
        }
        if not signatures[extension]:
            raise ResumeUploadError("The file content does not match its extension.")
        stored_name = f"{uuid.uuid4().hex}{extension}"
        path = self.folder / stored_name
        try:
            file.save(path)
        except OSError as exc:
            raise ResumeUploadError("The resume could not be saved.") from exc
        if path.stat().st_size == 0:
            path.unlink(missing_ok=True)
            raise ResumeUploadError("The resume file is empty.")
        previous = self.db["candidates"].find_one({"user_email": user["email"]}) or {}
        document = {
            "user_id": str(user["_id"]),
            "original_name": original,
            "stored_name": stored_name,
            "mime_type": mime,
            "size": path.stat().st_size,
            "created_at": datetime.now(timezone.utc),
        }
        resume_id = self.resumes.insert_one(document).inserted_id
        self.db["candidates"].update_one(
            {"user_email": user["email"]},
            {"$set": {"resume_id": str(resume_id)}},
            upsert=True,
        )
        previous_id = previous.get("resume_id")
        if previous_id:
            from bson import ObjectId

            if ObjectId.is_valid(previous_id):
                old = self.resumes.find_one({"_id": ObjectId(previous_id)})
                if old:
                    old_path = self.folder / old["stored_name"]
                    old_path.unlink(missing_ok=True)
                    self.resumes.delete_one({"_id": old["_id"]})
        return self.resumes.find_one({"_id": resume_id})

    def get_for_user(self, resume_id, user):
        from bson import ObjectId

        if not ObjectId.is_valid(resume_id):
            return None
        resume = self.resumes.find_one({"_id": ObjectId(resume_id)})
        if not resume:
            return None
        allowed = resume["user_id"] == str(user["_id"]) or user["role"] == "ADMIN"
        if not allowed:
            linked = self.db["applications"].find_one({
                "candidate_id": resume["user_id"],
                "recruiter_id": str(user["_id"]),
            })
            allowed = user["role"] == "RECRUITER" and linked is not None
        if not allowed:
            raise UnauthorizedError("You cannot access this resume.")
        return resume

    def delete(self, resume_id, user):
        resume = self.get_for_user(resume_id, user)
        if not resume:
            return False
        path = self.folder / resume["stored_name"]
        path.unlink(missing_ok=True)
        self.resumes.delete_one({"_id": resume["_id"]})
        self.db["candidates"].update_one(
            {"user_email": user["email"]},
            {"$unset": {"resume_id": ""}},
        )
        return True
