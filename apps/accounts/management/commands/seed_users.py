"""
Management command: seed_users

Creates N fake users (+ UserProfile) using Faker.
Always ensures the three fixture accounts exist:
  student / alice / admin  (password: pass)

Usage
-----
    python manage.py seed_users                  # 10 extra users
    python manage.py seed_users --no_records 25  # 25 extra users
    python manage.py seed_users --flush          # wipe seed users first

Returns
-------
The command prints each created username and exits with code 0.
It also exposes a helper function `run(n, flush, stdout)` so other
management commands can call it programmatically.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.accounts.models import UserProfile

User = get_user_model()
fake = Faker()

FIXTURE_USERS = [
    {'username': 'student', 'email': 'student@ai-academy.local', 'is_staff': False, 'is_superuser': False},
    {'username': 'alice',   'email': 'alice@ai-academy.local',   'is_staff': False, 'is_superuser': False},
    {'username': 'admin',   'email': 'admin@ai-academy.local',   'is_staff': True,  'is_superuser': True},
]


def _ensure_fixture_users(stdout=None) -> list:
    users = []
    for spec in FIXTURE_USERS:
        user, created = User.objects.get_or_create(
            username=spec['username'],
            defaults={
                'email':         spec['email'],
                'is_staff':      spec['is_staff'],
                'is_superuser':  spec['is_superuser'],
                'first_name':    spec['username'].capitalize(),
            },
        )
        if created:
            user.set_password('pass')
            user.save()
        elif not user.email:
            user.email = spec['email']
            user.save(update_fields=['email'])
            if stdout:
                stdout.write(f'  created fixture user: {user.username}')
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'display_name': user.username.capitalize()},
        )
        users.append(user)
    return users


def run(n: int, flush: bool = False, stdout=None) -> list[object]:
    """
    Seed N fake users. Returns the full list of seed + fixture users.

    Called by seed_messages with --seed-users flag.
    """
    if flush:
        deleted, _ = User.objects.filter(username__startswith='seed_').delete()
        if stdout:
            stdout.write(f'  flushed {deleted} seed user(s)')

    fixture_users = _ensure_fixture_users(stdout)
    created = []

    for _ in range(n):
        first = fake.first_name()
        last  = fake.last_name()
        base  = f'seed_{first.lower()}_{last.lower()}'
        username = base
        counter  = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}_{counter}'
            counter += 1

        user = User.objects.create_user(
            username=username,
            password='pass',
            first_name=first,
            last_name=last,
            email=fake.email(),
        )
        UserProfile.objects.create(
            user=user,
            display_name=f'{first} {last}',
            bio=fake.sentence(nb_words=10),
        )
        created.append(user)
        if stdout:
            stdout.write(f'  {username}  ({first} {last})')

    return fixture_users + created


class Command(BaseCommand):
    help = 'Seed N fake users with UserProfiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no_records',
            type=int,
            default=10,
            metavar='N',
            help='Number of fake users to create (default: 10)',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing seed users (username starts with seed_) before re-seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        n = options['no_records']
        if n < 0:
            self.stderr.write(self.style.ERROR('--no_records must be >= 0'))
            return

        self.stdout.write(f'Seeding {n} user(s)…')
        all_users = run(n=n, flush=options['flush'], stdout=self.stdout)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. {len(all_users)} total users available (fixture + seeded).'
        ))
        self.stdout.write('Password for all: pass')