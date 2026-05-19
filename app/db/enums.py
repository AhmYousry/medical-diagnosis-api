from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    USER = "user"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class DoctorVerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class UploadedFileStatus(StrEnum):
    PENDING = "pending"
    STORED = "stored"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class PredictionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PredictionLogEvent(StrEnum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    MODEL_INVOKED = "model_invoked"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class NotificationType(StrEnum):
    SYSTEM = "system"
    PREDICTION_COMPLETED = "prediction_completed"
    PREDICTION_FAILED = "prediction_failed"
