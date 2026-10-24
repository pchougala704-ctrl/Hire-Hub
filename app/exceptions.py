class HireHubError(Exception):
    code = "HIREHUB_ERROR"
    status_code = 400


class ValidationError(HireHubError):
    code = "VALIDATION_ERROR"


class UserAlreadyExistsError(HireHubError):
    code = "USER_ALREADY_EXISTS"
    status_code = 409


class InvalidCredentialsError(HireHubError):
    code = "INVALID_CREDENTIALS"
    status_code = 401


class AuthenticationRequiredError(HireHubError):
    code = "AUTHENTICATION_REQUIRED"
    status_code = 401


class UserNotFoundError(HireHubError):
    code = "USER_NOT_FOUND"
    status_code = 404


class UnauthorizedError(HireHubError):
    code = "UNAUTHORIZED"
    status_code = 403


class JobNotFoundError(HireHubError):
    code = "JOB_NOT_FOUND"
    status_code = 404


class JobClosedError(HireHubError):
    code = "JOB_CLOSED"
    status_code = 409


class DuplicateApplicationError(HireHubError):
    code = "DUPLICATE_APPLICATION"
    status_code = 409


class ApplicationNotFoundError(HireHubError):
    code = "APPLICATION_NOT_FOUND"
    status_code = 404


class InvalidApplicationStatusError(HireHubError):
    code = "INVALID_APPLICATION_STATUS"


class ResumeUploadError(HireHubError):
    code = "RESUME_UPLOAD_ERROR"
