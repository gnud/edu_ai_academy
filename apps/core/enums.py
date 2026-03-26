from django.db import models


class Role(models.TextChoices):
    PROFESSOR = "professor", "Professor"
    AI_PROFESSOR = "ai_professor", "AI Professor"
    STUDENT = "student", "Student"
    MODERATOR = "moderator", "Moderator"
    DEMONSTRATOR = "demonstrator", "Demonstrator"


class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    INVITED = "invited", "Invited"
    SUSPENDED = "suspended", "Suspended"
    REMOVED = "removed", "Removed"
    COMPLETED = "completed", "Completed"
    DROPPED = "dropped", "Dropped"


class AudienceType(models.TextChoices):
    ADULTS_ONLY = "adults_only", "Adults only"
    CHILDREN_ONLY = "children_only", "Children only"
    MIXED = "mixed", "Mixed"


class AttendanceStatus(models.TextChoices):
    INVITED = "invited", "Invited"
    JOINED = "joined", "Joined"
    LEFT = "left", "Left"
    ABSENT = "absent", "Absent"


class SubmissionType(models.TextChoices):
    FILE = "file", "File"
    LINK = "link", "Link"
    TEXT = "text", "Text"


class ReportType(models.TextChoices):
    COURSE = "course", "Course"
    MESSAGE = "message", "Message"
    USER = "user", "User"
    SESSION = "session", "Session"
    SUBMISSION = "submission", "Submission"


class ReportStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_REVIEW = "in_review", "In Review"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"


class ThreadType(models.TextChoices):
    COURSE  = "course",  "Course Message"
    PM      = "pm",      "Private Message"
    AI      = "ai",      "AI Conversation"
    SYSTEM  = "system",  "System"
    SUPPORT = "support", "Support"


class ParticipantFolder(models.TextChoices):
    INBOX    = "inbox",    "Inbox"
    ARCHIVED = "archived", "Archived"
    SPAM     = "spam",     "Spam"
    DRAFTS   = "drafts",   "Drafts"


class GroupType(models.TextChoices):
    PAIR = "pair", "Pair"
    TEAM = "team", "Team"


class ClassSessionStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    LIVE = "live", "Live"
    ENDED = "ended", "Ended"
    CANCELED = "canceled", "Canceled"


class SemesterStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
