"""
Management command: seed_classes

Creates realistic ClassSession data for E2E and UI testing.

Schedule
--------
  2 sessions  — status=live,      starts_at ≈ now  (one per classroom)
  5 sessions  — status=scheduled, one per day for the next 5 days

Each session gets all users (or a restricted set) enrolled as participants
with role derived from their CourseMembership where available.

Usage
-----
    python manage.py seed_classes
    python manage.py seed_classes --users alice bob      # always include these users
    python manage.py seed_classes --flush               # wipe all sessions first
    python manage.py seed_classes --seed-users          # run seed_users first
    python manage.py seed_classes --seed-courses        # run seed_courses first

What gets created
-----------------
  2 Classrooms        (get-or-create by slug)
  1 Course + Semester (reused if active ones exist)
  2 live ClassSessions
  5 scheduled ClassSessions
  CourseMemberships   (student role) for every participant
  SessionParticipants (invited status) — joined status set only for live sessions
"""

import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from apps.academy.models import Course, CourseMembership, Semester
from apps.core.enums import (
    AttendanceStatus, ClassSessionStatus, Role, SemesterStatus, Status,
)
from apps.liveclasses.models import Classroom, ClassSession, SessionParticipant

User = get_user_model()
fake = Faker()

TODAY = timezone.now().date()

CLASSROOM_NAMES = ['Lecture Hall A', 'Seminar Room B']

SESSION_TITLES = [
    'Introduction & Course Overview',
    'Core Concepts — Part 1',
    'Core Concepts — Part 2',
    'Hands-on Workshop',
    'Guest Speaker Session',
    'Mid-term Review',
    'Advanced Topics',
]

SESSION_DESCRIPTIONS = [
    'An interactive session covering the fundamentals.',
    'Deep dive into the week\'s material with live examples.',
    'Practical exercises and Q&A with the instructor.',
    'Guest lecturer shares industry insights and case studies.',
    'Reviewing key concepts before the assessment.',
]


# ── Helpers ────────────────────────────────────────────────────────────────

def get_or_create_classroom(name: str) -> Classroom:
    slug = slugify(name)
    classroom, _ = Classroom.objects.get_or_create(
        slug=slug,
        defaults={'name': name, 'description': f'{name} — seeded by seed_classes'},
    )
    return classroom


def ensure_active_semester(creator: User) -> Semester:
    """Return the first active semester, creating one if needed."""
    semester = (
        Semester.objects
        .select_related('course')
        .filter(status=SemesterStatus.ACTIVE)
        .first()
    )
    if semester:
        return semester

    course, _ = Course.objects.get_or_create(
        slug='seed-live-classes-course',
        defaults={
            'title': 'Live Classes Demo Course',
            'description': 'Auto-created by seed_classes for E2E testing.',
            'is_active': True,
            'is_published': True,
            'created_by': creator,
        },
    )
    semester, _ = Semester.objects.get_or_create(
        course=course,
        name='Demo Semester',
        defaults={
            'starts_on': TODAY,
            'status': SemesterStatus.ACTIVE,
            'enrollment_open': True,
        },
    )
    return semester


def enroll_user(semester: Semester, user: User, role: str = Role.STUDENT) -> CourseMembership:
    membership, _ = CourseMembership.objects.get_or_create(
        semester=semester,
        user=user,
        role=role,
        defaults={'status': Status.ACTIVE},
    )
    return membership


def add_participant(
    session: ClassSession,
    user: User,
    role: str,
    attendance_status: str,
) -> SessionParticipant:
    participant, _ = SessionParticipant.objects.get_or_create(
        session=session,
        user=user,
        defaults={
            'role': role,
            'attendance_status': attendance_status,
            'joined_at': timezone.now() if attendance_status == AttendanceStatus.JOINED else None,
        },
    )
    return participant


def make_session(
    semester: Semester,
    classroom: Classroom,
    professor: User,
    title: str,
    starts_at: datetime.datetime,
    session_status: str,
) -> ClassSession:
    ends_at = starts_at + datetime.timedelta(hours=1, minutes=30)
    session, _ = ClassSession.objects.get_or_create(
        semester=semester,
        classroom=classroom,
        title=title,
        defaults={
            'description': random.choice(SESSION_DESCRIPTIONS),
            'starts_at': starts_at,
            'ends_at': ends_at,
            'status': session_status,
            'professor': professor,
            'created_by': professor,
        },
    )
    return session


# ── Core seed logic ────────────────────────────────────────────────────────

def seed_classes(users: list[User], mandatory_usernames: list[str], stdout=None) -> dict:
    if not users:
        raise CommandError('No users found. Run seed_users first or pass --seed-users.')

    def log(msg):
        if stdout:
            stdout.write(msg)

    # Pick professor — prefer a staff user, fall back to first.
    professor = next((u for u in users if u.is_staff), users[0])

    # Participants — all users, but always include mandatory ones.
    mandatory = [u for u in users if u.username in mandatory_usernames]
    participants = list({*users, *mandatory})

    classrooms = [get_or_create_classroom(name) for name in CLASSROOM_NAMES]
    semester   = ensure_active_semester(creator=professor)

    # Enroll everyone as students (professor gets professor role).
    for u in participants:
        role = Role.PROFESSOR if u == professor else Role.STUDENT
        enroll_user(semester, u, role)

    now = timezone.now()
    sessions_created = 0

    # ── 2 live sessions (now) ──────────────────────────────────────────────
    live_titles = random.sample(SESSION_TITLES, k=min(2, len(SESSION_TITLES)))
    for i, title in enumerate(live_titles):
        classroom = classrooms[i % len(classrooms)]
        session = make_session(
            semester=semester,
            classroom=classroom,
            professor=professor,
            title=f'[LIVE] {title}',
            starts_at=now - datetime.timedelta(minutes=random.randint(5, 20)),
            session_status=ClassSessionStatus.LIVE,
        )
        # Mark everyone as joined for live sessions.
        add_participant(session, professor, Role.PROFESSOR, AttendanceStatus.JOINED)
        for u in participants:
            if u != professor:
                status = AttendanceStatus.JOINED if random.random() > 0.3 else AttendanceStatus.INVITED
                add_participant(session, u, Role.STUDENT, status)

        log(f'  [live]      {session.title} @ {classroom.name}')
        sessions_created += 1

    # ── 5 scheduled sessions (next 5 days) ────────────────────────────────
    scheduled_titles = random.sample(
        [t for t in SESSION_TITLES if t not in live_titles],
        k=min(5, len(SESSION_TITLES) - len(live_titles)),
    )
    for day_offset, title in enumerate(scheduled_titles, start=1):
        classroom = classrooms[day_offset % len(classrooms)]
        hour      = random.choice([9, 10, 11, 14, 15, 16])
        starts_at = now.replace(hour=hour, minute=0, second=0, microsecond=0) + datetime.timedelta(days=day_offset)
        session = make_session(
            semester=semester,
            classroom=classroom,
            professor=professor,
            title=title,
            starts_at=starts_at,
            session_status=ClassSessionStatus.SCHEDULED,
        )
        add_participant(session, professor, Role.PROFESSOR, AttendanceStatus.INVITED)
        for u in participants:
            if u != professor:
                add_participant(session, u, Role.STUDENT, AttendanceStatus.INVITED)

        log(f'  [scheduled] {session.title} @ {classroom.name} — {starts_at.strftime("%a %b %d %H:%M")}')
        sessions_created += 1

    return {
        'sessions': sessions_created,
        'participants': len(participants),
        'semester': semester,
    }


# ── Command ────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed live classroom sessions for E2E and UI testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            nargs='+',
            metavar='USERNAME',
            default=[],
            help='Usernames that must be included as participants regardless of other filters',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all ClassSessions (and their participants) before re-seeding',
        )
        parser.add_argument(
            '--seed-users',
            action='store_true',
            help='Run seed_users before seeding classes',
        )
        parser.add_argument(
            '--seed-courses',
            action='store_true',
            help='Run seed_courses before seeding classes',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # ── Optional upstream seeders ──────────────────────────────────────
        if options['seed_users']:
            from apps.accounts.management.commands.seed_users import run as seed_users_run
            self.stdout.write('Seeding users first…')
            seed_users_run(n=10, flush=False, stdout=self.stdout)
            self.stdout.write('')

        if options['seed_courses']:
            from django.core.management import call_command
            self.stdout.write('Seeding courses first…')
            call_command('seed_courses')
            self.stdout.write('')

        # ── Flush ──────────────────────────────────────────────────────────
        if options['flush']:
            deleted, _ = ClassSession.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Flushed {deleted} session(s).'))

        # ── Collect users ──────────────────────────────────────────────────
        all_users = list(User.objects.all())
        if not all_users:
            raise CommandError('No users found. Run seed_users first or pass --seed-users.')

        # Warn about unknown mandatory usernames.
        existing_names = {u.username for u in all_users}
        for name in options['users']:
            if name not in existing_names:
                self.stderr.write(self.style.WARNING(f'  User "{name}" not found — skipping.'))

        # ── Seed ───────────────────────────────────────────────────────────
        self.stdout.write('Creating sessions…')
        result = seed_classes(
            users=all_users,
            mandatory_usernames=options['users'],
            stdout=self.stdout,
        )

        # ── Summary ────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. {result["sessions"]} session(s) created for {result["participants"]} participant(s).'
        ))
        self.stdout.write(f'  Semester: {result["semester"]}')
        self.stdout.write('')
        self.stdout.write('Endpoints:')
        self.stdout.write('  GET /api/classes/')
        self.stdout.write('  GET /api/classes/?status=live')
        self.stdout.write('  GET /api/classes/?upcoming=true')
        self.stdout.write('  POST /api/classes/<id>/join/')
