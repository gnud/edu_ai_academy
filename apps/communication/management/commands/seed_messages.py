"""
Management command: seed_messages

Creates N fake Threads with Messages across all thread types
(course, pm, ai, system, support).

Usage
-----
    python manage.py seed_messages                        # 20 threads
    python manage.py seed_messages --no_records 50        # 50 threads
    python manage.py seed_messages --seed-users           # seed 10 users first
    python manage.py seed_messages --seed-users --seed-users-count 15
    python manage.py seed_messages --flush                # wipe seed data first

What gets created
-----------------
Threads are distributed across types in proportion:
  pm      40 %   private conversations between two random users
  course  25 %   discussions tied to a seeded course (if any exist)
  ai      15 %   user ↔ AI back-and-forth
  system  10 %   automated notifications (single message, no reply)
  support 10 %   help-desk tickets with a staff reply

Each thread gets 1–5 messages. The 'student' user is always a
participant so their inbox is populated for E2E testing.
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from apps.academy.models import Course
from apps.communication.models import Message, Thread, ThreadParticipant
from apps.core.enums import ParticipantFolder, ThreadType

User = get_user_model()
fake = Faker()

# Thread type distribution weights
TYPE_WEIGHTS = [
    (ThreadType.PM,      40),
    (ThreadType.COURSE,  25),
    (ThreadType.AI,      15),
    (ThreadType.SYSTEM,  10),
    (ThreadType.SUPPORT, 10),
]
TYPES, WEIGHTS = zip(*TYPE_WEIGHTS)

# ── Body templates ─────────────────────────────────────────────────────────

PM_SUBJECTS = [
    'Quick question about the assignment',
    'Study session this weekend?',
    'Notes from last lecture',
    'Re: Project collaboration',
    'Available for office hours tomorrow?',
    'Feedback on my submission',
    'Can you share your solution approach?',
    'Group project — team update',
]

COURSE_SUBJECTS = [
    'Question about Week {week} material',
    'Clarification on assignment {n}',
    'Live session recap — {topic}',
    'Resource recommendation for {topic}',
    'Exam preparation tips',
    'Bug in the starter code?',
]

AI_SUBJECTS = [
    'Help me understand {topic}',
    'Explain {topic} like I\'m five',
    'Code review request',
    'What\'s the difference between {a} and {b}?',
    'Best practices for {topic}',
]

SYSTEM_SUBJECTS = [
    'Welcome to {course}!',
    'Your enrollment in {course} is confirmed',
    'Assignment deadline reminder',
    'New course material available',
    'Your certificate is ready',
    'Scheduled maintenance — {date}',
]

SUPPORT_SUBJECTS = [
    'Cannot access course videos',
    'Payment issue with subscription',
    'Certificate not generated',
    'Account merge request',
    'Technical issue with live session',
]

TOPICS = [
    'recursion', 'async/await', 'REST APIs', 'neural networks',
    'SQL joins', 'Docker containers', 'JWT authentication',
    'React hooks', 'Python decorators', 'Git branching',
]


def pick_subject(thread_type: str, course=None) -> str:
    if thread_type == ThreadType.PM:
        return random.choice(PM_SUBJECTS)
    if thread_type == ThreadType.COURSE:
        tpl = random.choice(COURSE_SUBJECTS)
        return tpl.format(week=random.randint(1, 8), n=random.randint(1, 5), topic=random.choice(TOPICS))
    if thread_type == ThreadType.AI:
        tpl = random.choice(AI_SUBJECTS)
        return tpl.format(topic=random.choice(TOPICS), a=random.choice(TOPICS), b=random.choice(TOPICS))
    if thread_type == ThreadType.SYSTEM:
        tpl = random.choice(SYSTEM_SUBJECTS)
        name = course.title if course else fake.bs().title()
        return tpl.format(course=name, date=fake.date_this_month().strftime('%b %d'))
    return random.choice(SUPPORT_SUBJECTS)


def make_body(thread_type: str, sender_name: str, is_reply: bool = False) -> str:
    if thread_type == ThreadType.AI and is_reply:
        return (
            f"Great question! {fake.sentence(nb_words=15)}\n\n"
            f"{fake.paragraph(nb_sentences=3)}\n\n"
            f"Here's a quick example:\n\n"
            f"```python\n{fake.bs()}\n```\n\n"
            f"Does that help clarify things?"
        )
    if thread_type == ThreadType.SYSTEM:
        return (
            f"Hi there,\n\n"
            f"{fake.paragraph(nb_sentences=2)}\n\n"
            f"If you have any questions, please contact support.\n\n"
            f"— The AI Academy Team"
        )
    if thread_type == ThreadType.SUPPORT and is_reply:
        return (
            f"Hi,\n\nThank you for reaching out. {fake.paragraph(nb_sentences=2)}\n\n"
            f"We've escalated your ticket and will follow up within 24 hours.\n\n"
            f"Best,\nSupport Team"
        )
    greeting = random.choice(['Hi', 'Hey', 'Hello'])
    sign_off = random.choice(['Best,', 'Thanks,', 'Cheers,', 'See you,'])
    return (
        f"{greeting},\n\n"
        f"{fake.paragraph(nb_sentences=random.randint(2, 4))}\n\n"
        f"{sign_off}\n{sender_name}"
    )


# ── Core seed logic ────────────────────────────────────────────────────────

def seed_messages(n: int, all_users: list, stdout=None) -> int:
    student = next((u for u in all_users if u.username == 'student'), all_users[0])
    staff   = [u for u in all_users if u.is_staff] or [all_users[0]]
    courses = list(Course.objects.filter(is_published=True, is_active=True)[:20])

    created = 0
    base_time = timezone.now() - timedelta(days=30)

    for i in range(n):
        thread_type = random.choices(TYPES, WEIGHTS)[0]

        # Pick course for course-type threads
        course = random.choice(courses) if thread_type == ThreadType.COURSE and courses else None

        subject = pick_subject(thread_type, course)

        # Determine participants
        if thread_type == ThreadType.PM:
            other = random.choice([u for u in all_users if u != student] or all_users)
            participants = [student, other]
        elif thread_type == ThreadType.COURSE:
            instructor = random.choice(staff)
            others = random.sample(
                [u for u in all_users if u != student],
                k=min(random.randint(0, 3), len(all_users) - 1),
            )
            participants = list({student, instructor, *others})
        elif thread_type == ThreadType.AI:
            participants = [student]
        elif thread_type == ThreadType.SYSTEM:
            participants = [student]
        else:  # support
            participants = [student, random.choice(staff)]

        thread_time = base_time + timedelta(minutes=i * random.randint(20, 120))

        thread = Thread.objects.create(
            thread_type=thread_type,
            subject=subject,
            course=course,
            created_by=student,
            last_message_at=thread_time,
        )

        for user in participants:
            folder = ParticipantFolder.INBOX
            if thread_type == ThreadType.SYSTEM:
                # Randomly archive some system notifications
                folder = random.choice([ParticipantFolder.INBOX, ParticipantFolder.ARCHIVED])
            ThreadParticipant.objects.create(
                thread=thread,
                user=user,
                folder=folder,
                is_starred=random.random() < 0.15,
                last_read_at=thread_time if random.random() < 0.6 else None,
            )

        # Create messages
        num_messages = 1 if thread_type == ThreadType.SYSTEM else random.randint(1, 5)
        senders = (
            [None] if thread_type == ThreadType.SYSTEM     # system = no sender
            else participants if thread_type != ThreadType.AI
            else [student, None]  # AI: student asks, None = AI responds
        )

        msg_time = thread_time - timedelta(minutes=num_messages * 10)
        for j in range(num_messages):
            is_reply = j > 0
            if thread_type == ThreadType.AI:
                sender = student if j % 2 == 0 else None
            elif thread_type == ThreadType.SYSTEM:
                sender = None
            else:
                sender = senders[j % len(senders)]

            sender_name = sender.get_full_name() or sender.username if sender else 'AI Academy'
            meta: dict = {}
            if thread_type == ThreadType.COURSE and course:
                meta = {'course_id': course.id, 'course_slug': course.slug}
            elif thread_type == ThreadType.AI:
                meta = {'model': 'claude-sonnet-4-6', 'turn': j + 1}
            elif thread_type == ThreadType.SYSTEM:
                meta = {'event': fake.slug(), 'automated': True}
            elif thread_type == ThreadType.SUPPORT:
                meta = {'ticket_ref': f'TKT-{1000 + i:04d}', 'priority': random.choice(['low', 'normal', 'high'])}

            Message.objects.create(
                thread=thread,
                sender=sender,
                body=make_body(thread_type, sender_name, is_reply),
                message_type=thread_type,
                metadata=meta,
                sent_at=msg_time,
            )
            msg_time += timedelta(minutes=random.randint(5, 60))

        created += 1

    return created


# ── Command ────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed fake threads and messages for E2E testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no_records',
            type=int,
            default=20,
            metavar='N',
            help='Number of threads to create (default: 20)',
        )
        parser.add_argument(
            '--seed-users',
            action='store_true',
            help='Run seed_users before seeding messages',
        )
        parser.add_argument(
            '--seed-users-count',
            type=int,
            default=10,
            metavar='N',
            help='Number of fake users to create when --seed-users is set (default: 10)',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all seeded threads before re-seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        n = options['no_records']
        if n < 1:
            self.stderr.write(self.style.ERROR('--no_records must be at least 1'))
            return

        # ── Optionally seed users first ────────────────────────────────────
        if options['seed_users']:
            from apps.accounts.management.commands.seed_users import run as seed_users_run
            self.stdout.write(f'Seeding {options["seed_users_count"]} user(s) first…')
            all_users = seed_users_run(
                n=options['seed_users_count'],
                flush=options['flush'],
                stdout=self.stdout,
            )
            self.stdout.write('')
        else:
            all_users = list(User.objects.all())
            if not all_users:
                self.stderr.write(self.style.ERROR(
                    'No users found. Run seed_users first or pass --seed-users.'
                ))
                return

        # ── Flush existing seed threads ────────────────────────────────────
        if options['flush']:
            deleted, _ = Thread.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Flushed {deleted} thread(s).'))

        # ── Seed threads + messages ────────────────────────────────────────
        self.stdout.write(f'Creating {n} thread(s)…')
        created = seed_messages(n=n, all_users=all_users, stdout=self.stdout)

        # ── Summary ────────────────────────────────────────────────────────
        from apps.communication.models import Thread as T, Message as M
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} thread(s).'))
        self.stdout.write('')
        for ttype in ['pm', 'course', 'ai', 'system', 'support']:
            count = T.objects.filter(thread_type=ttype).count()
            self.stdout.write(f'  {ttype:<10} {count:>4} thread(s)')
        self.stdout.write(f'  {"total msgs":<10} {M.objects.count():>4}')
        self.stdout.write('')
        self.stdout.write('Endpoints:')
        self.stdout.write('  GET /api/messages/threads/              (login as student)')
        self.stdout.write('  GET /api/messages/threads/?type=pm')
        self.stdout.write('  GET /api/messages/threads/?folder=inbox')
        self.stdout.write('  GET /api/messages/threads/?starred=true')