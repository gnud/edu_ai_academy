"""
Management command: seed_courses

Generates N courses (with semesters and memberships) using Faker
so the React frontend can be tested end-to-end with realistic data.

Usage
-----
    python manage.py seed_courses                     # 10 courses, enrol 'student'
    python manage.py seed_courses --no_records 25     # 25 courses
    python manage.py seed_courses --user alice        # enrol a different user
    python manage.py seed_courses --flush             # wipe seed data first

What gets created
-----------------
* N courses (is_active=True, is_published=True) with Faker-generated titles
* Each course gets one Semester whose status cycles through:
    active → scheduled → completed → cancelled  (repeats)
* The target user is enrolled in every semester.
  Membership status is varied so all hub stat buckets are exercised:
    active sem   → membership active   (in_the_mix)
    scheduled    → membership active   (on_deck)
    completed    → membership active   (graduated)
    cancelled    → membership active   (dropped)
* One extra course is created and given to 'alice' only (isolation check).
"""

import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from apps.academy.models import Course, CourseMembership, Semester
from apps.core.enums import AudienceType, Role, SemesterStatus, Status

User = get_user_model()
fake = Faker()

TODAY = timezone.now().date()

# Semester statuses cycle in this order so every bucket is represented.
SEM_STATUSES = [
    SemesterStatus.ACTIVE,
    SemesterStatus.SCHEDULED,
    SemesterStatus.COMPLETED,
    SemesterStatus.CANCELLED,
]

AUDIENCE_CHOICES = list(AudienceType.values)

TECH_PREFIXES = [
    'Introduction to', 'Advanced', 'Practical', 'Mastering',
    'Foundations of', 'Deep Dive into', 'Applied', 'Modern',
]
TECH_TOPICS = [
    'Machine Learning', 'Python Programming', 'React & TypeScript',
    'Data Structures', 'Web Security', 'Deep Learning', 'UX Design',
    'Cloud Architecture', 'Django REST Framework', 'SQL & Databases',
    'DevOps & CI/CD', 'GraphQL APIs', 'NLP', 'Computer Vision',
    'Microservices', 'Kubernetes', 'System Design', 'Rust Programming',
    'Go for Backends', 'iOS Development', 'Android Development',
    'Blockchain Basics', 'Ethical Hacking', 'Data Engineering',
    'Statistics for ML', 'Product Management', 'Agile & Scrum',
    'UI Animation', 'Accessibility', 'Open Source Contribution',
]


def days(n: int) -> datetime.date:
    return TODAY + datetime.timedelta(days=n)


def get_or_create_user(username: str, **kwargs) -> object:
    user, created = User.objects.get_or_create(username=username, defaults=kwargs)
    if created:
        user.set_password('pass')
        user.save()
    return user


def unique_title(used: set) -> str:
    """Return a unique course title that hasn't been used in this run."""
    random.shuffle(TECH_TOPICS)
    for topic in TECH_TOPICS:
        for prefix in TECH_PREFIXES:
            title = f'{prefix} {topic}'
            if title not in used:
                used.add(title)
                return title
    # Fall back to Faker if we exhaust the matrix
    while True:
        title = f'{fake.bs().title()} {fake.word().title()}'
        if title not in used:
            used.add(title)
            return title


def unique_slug(title: str, used: set) -> str:
    base = slugify(title)[:40]
    slug = base
    counter = 1
    while slug in used or Course.objects.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    used.add(slug)
    return slug


def make_semester_dates(status: str) -> tuple[datetime.date, datetime.date | None]:
    if status == SemesterStatus.ACTIVE:
        return days(random.randint(-60, -7)), days(random.randint(30, 120))
    if status == SemesterStatus.SCHEDULED:
        start = days(random.randint(14, 90))
        return start, start + datetime.timedelta(days=random.randint(60, 120))
    if status == SemesterStatus.COMPLETED:
        end = days(random.randint(-30, -1))
        return end - datetime.timedelta(days=random.randint(60, 180)), end
    # CANCELLED
    start = days(random.randint(-90, 30))
    return start, start + datetime.timedelta(days=random.randint(30, 90))


class Command(BaseCommand):
    help = 'Seed N courses with semesters and memberships for E2E testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no_records',
            type=int,
            default=10,
            metavar='N',
            help='Number of courses to create (default: 10)',
        )
        parser.add_argument(
            '--user',
            default='student',
            help='Username of the student to enrol in all courses (default: student)',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all existing seed data (by slug prefix) before re-seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        n = options['no_records']
        username = options['user']

        if n < 1:
            self.stderr.write(self.style.ERROR('--no_records must be at least 1'))
            return

        # ── flush ──────────────────────────────────────────────────────────
        if options['flush']:
            deleted, _ = Course.objects.filter(slug__startswith='seed-').delete()
            self.stdout.write(self.style.WARNING(f'Flushed {deleted} seeded course(s).'))

        # ── users ──────────────────────────────────────────────────────────
        admin   = get_or_create_user('admin',  is_staff=True, is_superuser=True)
        student = get_or_create_user(username)
        alice   = get_or_create_user('alice')
        self.stdout.write(f'Users: admin / {username} / alice  (password: pass)')

        # ── seed N courses ─────────────────────────────────────────────────
        used_titles: set[str] = set()
        used_slugs:  set[str] = set()
        created_count = 0
        stats = {s: 0 for s in SemesterStatus.values}

        for i in range(n):
            title = unique_title(used_titles)
            slug  = 'seed-' + unique_slug(title, used_slugs)
            sem_status = SEM_STATUSES[i % len(SEM_STATUSES)]
            starts_on, ends_on = make_semester_dates(sem_status)

            course = Course.objects.create(
                title=title,
                slug=slug,
                short_description=fake.sentence(nb_words=12),
                description=fake.paragraph(nb_sentences=4),
                is_active=True,
                is_published=True,
                audience_type=random.choice(AUDIENCE_CHOICES),
                created_by=admin,
            )

            semester = Semester.objects.create(
                course=course,
                name=fake.bothify('## cohort ????').title(),
                status=sem_status,
                starts_on=starts_on,
                ends_on=ends_on,
                max_students=random.choice([None, 15, 20, 25, 30]),
                enrollment_open=sem_status in (SemesterStatus.ACTIVE, SemesterStatus.SCHEDULED),
            )

            CourseMembership.objects.create(
                semester=semester,
                user=student,
                role=Role.STUDENT,
                status=Status.ACTIVE,
            )

            stats[sem_status] += 1
            created_count += 1

        # ── isolation course for alice ─────────────────────────────────────
        alice_title = unique_title(used_titles)
        alice_slug  = 'seed-' + unique_slug(alice_title, used_slugs)
        alice_course = Course.objects.create(
            title=alice_title,
            slug=alice_slug,
            short_description=fake.sentence(nb_words=10),
            description=fake.paragraph(nb_sentences=3),
            is_active=True,
            is_published=True,
            audience_type=AudienceType.MIXED,
            created_by=admin,
        )
        alice_sem = Semester.objects.create(
            course=alice_course,
            name='01 cohort Alpha',
            status=SemesterStatus.ACTIVE,
            starts_on=days(-10),
            ends_on=days(80),
            enrollment_open=True,
        )
        CourseMembership.objects.create(
            semester=alice_sem,
            user=alice,
            role=Role.STUDENT,
            status=Status.ACTIVE,
        )

        # ── summary ────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created_count} course(s) + 1 isolation course for alice.'
        ))
        self.stdout.write('')
        self.stdout.write(f'  {"active":<12} {stats[SemesterStatus.ACTIVE]:>3}  → in_the_mix')
        self.stdout.write(f'  {"scheduled":<12} {stats[SemesterStatus.SCHEDULED]:>3}  → on_deck')
        self.stdout.write(f'  {"completed":<12} {stats[SemesterStatus.COMPLETED]:>3}  → graduated')
        self.stdout.write(f'  {"cancelled":<12} {stats[SemesterStatus.CANCELLED]:>3}  → dropped')
        self.stdout.write('')
        self.stdout.write(f'  Catalog  : /api/courses/       ({created_count + 1} total)')
        self.stdout.write(f'  My courses: /api/courses/me/   (login as {username})')
        self.stdout.write(f'  Hub      : /api/hub/')