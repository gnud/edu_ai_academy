import datetime

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academy.models import Course, Semester, CourseMembership
from apps.core.enums import AttendanceStatus, ClassSessionStatus, Role, SemesterStatus
from .models import Classroom, ClassSession, SessionParticipant


def make_user(username='student', password='pass'):
    return User.objects.create_user(username=username, password=password)


def make_session(professor=None):
    creator = professor or make_user('creator')
    course = Course.objects.create(
        title='Test Course', slug='test-course', created_by=creator,
    )
    semester = Semester.objects.create(
        course=course, name='S1',
        starts_on=datetime.date.today(),
        status=SemesterStatus.ACTIVE,
    )
    classroom = Classroom.objects.create(name='Room 1', slug='room-1')
    session = ClassSession.objects.create(
        semester=semester,
        classroom=classroom,
        title='Lecture 1',
        starts_at=timezone.now(),
        status=ClassSessionStatus.LIVE,
        professor=professor,
        created_by=creator,
    )
    return session, semester


class JoinLeaveSessionTests(APITestCase):

    def setUp(self):
        self.student = make_user('student')
        self.professor = make_user('professor')
        self.session, self.semester = make_session(professor=self.professor)
        self.client.force_authenticate(user=self.student)

    def test_join_creates_participant(self):
        url = reverse('class-session-join', kwargs={'pk': self.session.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        participant = SessionParticipant.objects.get(session=self.session, user=self.student)
        self.assertEqual(participant.attendance_status, AttendanceStatus.JOINED)
        self.assertIsNotNone(participant.joined_at)

    def test_join_twice_updates_existing(self):
        url = reverse('class-session-join', kwargs={'pk': self.session.pk})
        self.client.post(url)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(SessionParticipant.objects.filter(session=self.session, user=self.student).count(), 1)

    def test_join_role_from_membership(self):
        CourseMembership.objects.create(
            semester=self.semester, user=self.student, role=Role.STUDENT,
        )
        url = reverse('class-session-join', kwargs={'pk': self.session.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.data['role'], Role.STUDENT)

    def test_leave_updates_status(self):
        SessionParticipant.objects.create(
            session=self.session, user=self.student,
            role=Role.STUDENT, attendance_status=AttendanceStatus.JOINED,
        )
        url = reverse('class-session-leave', kwargs={'pk': self.session.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        participant = SessionParticipant.objects.get(session=self.session, user=self.student)
        self.assertEqual(participant.attendance_status, AttendanceStatus.LEFT)
        self.assertIsNotNone(participant.left_at)

    def test_leave_not_participant_returns_404(self):
        url = reverse('class-session-leave', kwargs={'pk': self.session.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class SessionDetailTests(APITestCase):

    def setUp(self):
        self.user = make_user('viewer')
        self.session, _ = make_session()
        self.client.force_authenticate(user=self.user)

    def test_detail_returns_participants(self):
        student = make_user('student2')
        SessionParticipant.objects.create(
            session=self.session, user=student,
            role=Role.STUDENT, attendance_status=AttendanceStatus.JOINED,
        )
        url = reverse('class-session-detail', kwargs={'pk': self.session.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['participants']), 1)
        self.assertEqual(resp.data['participants'][0]['username'], 'student2')

    def test_detail_404_for_unknown_session(self):
        url = reverse('class-session-detail', kwargs={'pk': 9999})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ParticipantListTests(APITestCase):

    def setUp(self):
        self.user = make_user('viewer3')
        self.session, _ = make_session()
        self.client.force_authenticate(user=self.user)

    def test_participant_list_returns_all(self):
        for i in range(3):
            u = make_user(f'stud{i}')
            SessionParticipant.objects.create(
                session=self.session, user=u, role=Role.STUDENT,
                attendance_status=AttendanceStatus.JOINED,
            )
        url = reverse('class-session-participants', kwargs={'pk': self.session.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)

    def test_participant_avatar_color_is_deterministic(self):
        u = make_user('colorstud')
        SessionParticipant.objects.create(
            session=self.session, user=u, role=Role.STUDENT,
        )
        url = reverse('class-session-participants', kwargs={'pk': self.session.pk})
        resp1 = self.client.get(url)
        resp2 = self.client.get(url)
        self.assertEqual(resp1.data[0]['avatar_color'], resp2.data[0]['avatar_color'])
