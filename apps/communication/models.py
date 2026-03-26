from django.db import models

from apps.core.enums import ParticipantFolder, ThreadType


class Thread(models.Model):
    """
    A conversation thread.

    thread_type controls the context:
      course   — tied to a specific course (course populated)
      pm       — private message between users
      ai       — user ↔ AI assistant conversation
      system   — automated notifications / announcements
      support  — help-desk / support tickets

    Participants are tracked via ThreadParticipant so each user has
    independent folder placement, star state, and read position.
    """

    thread_type = models.CharField(
        max_length=20,
        choices=ThreadType.choices,
        default=ThreadType.PM,
    )
    subject = models.CharField(max_length=255, blank=True)

    # Populated for thread_type='course' only.
    course = models.ForeignKey(
        "academy.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="message_threads",
    )

    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_threads",
    )

    # Bumped on every new message — drives ordering in the inbox list.
    last_message_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        return f"[{self.thread_type}] {self.subject or f'Thread #{self.pk}'}"


class ThreadParticipant(models.Model):
    """
    Per-user membership in a Thread.

    Records folder, star, and the read watermark (last_read_at).
    Any message sent after last_read_at is considered unread for this user.
    """

    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="thread_participations",
    )

    folder = models.CharField(
        max_length=20,
        choices=ParticipantFolder.choices,
        default=ParticipantFolder.INBOX,
    )
    is_starred = models.BooleanField(default=False)

    # NULL = user has never opened the thread (fully unread).
    last_read_at = models.DateTimeField(null=True, blank=True)

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("thread", "user")

    def __str__(self):
        return f"{self.user} in {self.thread}"


class Message(models.Model):
    """
    A single message inside a Thread.

    sender is NULL for system / AI generated messages.

    metadata is a freeform JSON blob for per-type extra data, e.g.:
      course  → {"course_id": 3, "semester_id": 7}
      ai      → {"model": "claude-sonnet-4-6", "prompt_tokens": 120}
      system  → {"event": "enrollment_confirmed", "course_slug": "intro-ml"}
      support → {"ticket_id": "TKT-042", "priority": "high"}
    """

    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_messages",
    )

    body = models.TextField()

    # Mirrors thread.thread_type for fast per-message filtering.
    message_type = models.CharField(
        max_length=20,
        choices=ThreadType.choices,
    )

    metadata = models.JSONField(default=dict, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]

    def __str__(self):
        who = self.sender.username if self.sender else "system"
        return f"[{self.message_type}] {who} → thread #{self.thread_id}"