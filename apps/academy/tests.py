from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.test import TestCase

from apps.core.enums import SemesterStatus, AudienceType
from .admin import SemesterInlineFormset
from .models import Course, Semester


class SemesterTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            audience_type=AudienceType.MIXED,
            created_by=self.user,
        )

    def make_semester(self, starts_on, ends_on, status=SemesterStatus.SCHEDULED, name="Sem", save=False):
        sem = Semester(
            course=self.course,
            name=name,
            starts_on=starts_on,
            ends_on=ends_on,
            status=status,
        )
        if save:
            sem.save()
        return sem


# ---------------------------------------------------------------------------
# Date range validation (model level)
# ---------------------------------------------------------------------------

class SemesterDateRangeTest(SemesterTestBase):

    def test_ends_before_starts_raises(self):
        sem = self.make_semester(date(2026, 3, 10), date(2026, 3, 5))
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("ends_on", ctx.exception.message_dict)

    def test_ends_same_as_starts_raises(self):
        sem = self.make_semester(date(2026, 3, 10), date(2026, 3, 10))
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("ends_on", ctx.exception.message_dict)

    def test_valid_date_range_passes(self):
        sem = self.make_semester(date(2026, 3, 10), date(2026, 6, 30))
        sem.clean()  # must not raise

    def test_open_ended_passes(self):
        sem = self.make_semester(date(2026, 3, 10), None)
        sem.clean()  # must not raise


# ---------------------------------------------------------------------------
# Active uniqueness (model level)
# ---------------------------------------------------------------------------

class SemesterActiveUniquenessTest(SemesterTestBase):

    def setUp(self):
        super().setUp()
        self.active = self.make_semester(
            date(2026, 1, 1), date(2026, 6, 30),
            status=SemesterStatus.ACTIVE, name="Active", save=True,
        )

    def test_second_active_raises(self):
        sem = self.make_semester(
            date(2026, 7, 1), date(2026, 12, 31),
            status=SemesterStatus.ACTIVE,
        )
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("status", ctx.exception.message_dict)

    def test_editing_existing_active_passes(self):
        self.active.name = "Updated"
        self.active.clean()  # must not raise

    def test_completed_does_not_block_new_active(self):
        self.active.status = SemesterStatus.COMPLETED
        self.active.save()
        sem = self.make_semester(
            date(2026, 7, 1), date(2026, 12, 31),
            status=SemesterStatus.ACTIVE,
        )
        sem.clean()  # must not raise

    def test_cancelled_does_not_block_new_active(self):
        self.active.status = SemesterStatus.CANCELLED
        self.active.save()
        sem = self.make_semester(
            date(2026, 7, 1), date(2026, 12, 31),
            status=SemesterStatus.ACTIVE,
        )
        sem.clean()  # must not raise


# ---------------------------------------------------------------------------
# Overlap validation (model level)
# ---------------------------------------------------------------------------

class SemesterOverlapTest(SemesterTestBase):

    def setUp(self):
        super().setUp()
        self.existing = self.make_semester(
            date(2026, 1, 1), date(2026, 6, 30),
            status=SemesterStatus.ACTIVE, name="Existing", save=True,
        )

    def test_scheduled_overlapping_active_raises(self):
        sem = self.make_semester(date(2026, 4, 1), date(2026, 9, 30))
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("starts_on", ctx.exception.message_dict)

    def test_scheduled_starting_same_day_active_ends_raises(self):
        # starts_on == existing ends_on → overlap (not strictly after)
        sem = self.make_semester(date(2026, 6, 30), date(2026, 12, 31))
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("starts_on", ctx.exception.message_dict)

    def test_scheduled_after_active_passes(self):
        sem = self.make_semester(date(2026, 7, 1), date(2026, 12, 31))
        sem.clean()  # must not raise

    def test_scheduled_before_active_passes(self):
        # ends strictly before existing starts
        sem = self.make_semester(date(2025, 1, 1), date(2025, 12, 31))
        sem.clean()  # must not raise

    def test_two_scheduled_overlapping_raises(self):
        self.make_semester(
            date(2026, 7, 1), date(2026, 12, 31),
            status=SemesterStatus.SCHEDULED, name="Sched A", save=True,
        )
        sem = self.make_semester(
            date(2026, 10, 1), date(2027, 3, 31),
            status=SemesterStatus.SCHEDULED, name="Sched B",
        )
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("starts_on", ctx.exception.message_dict)

    def test_two_scheduled_non_overlapping_passes(self):
        self.make_semester(
            date(2026, 7, 1), date(2026, 12, 31),
            status=SemesterStatus.SCHEDULED, name="Sched A", save=True,
        )
        sem = self.make_semester(
            date(2027, 1, 1), date(2027, 6, 30),
            status=SemesterStatus.SCHEDULED, name="Sched B",
        )
        sem.clean()  # must not raise

    def test_open_ended_active_blocks_any_scheduled_after(self):
        self.existing.ends_on = None
        self.existing.save()
        sem = self.make_semester(date(2026, 7, 1), date(2026, 12, 31))
        with self.assertRaises(ValidationError) as ctx:
            sem.clean()
        self.assertIn("starts_on", ctx.exception.message_dict)

    def test_completed_overlap_does_not_block(self):
        self.existing.status = SemesterStatus.COMPLETED
        self.existing.save()
        sem = self.make_semester(date(2026, 4, 1), date(2026, 9, 30))
        sem.clean()  # must not raise

    def test_cancelled_overlap_does_not_block(self):
        self.existing.status = SemesterStatus.CANCELLED
        self.existing.save()
        sem = self.make_semester(date(2026, 4, 1), date(2026, 9, 30))
        sem.clean()  # must not raise

    def test_no_course_id_skips_db_checks(self):
        sem = Semester(
            name="No Course",
            starts_on=date(2026, 4, 1),
            ends_on=date(2026, 9, 30),
            status=SemesterStatus.ACTIVE,
        )
        sem.clean()  # must not raise — course_id is None


# ---------------------------------------------------------------------------
# Formset validation (admin inline level)
# ---------------------------------------------------------------------------

class SemesterInlineFormsetTest(SemesterTestBase):

    def _make_formset(self, forms_data):
        """
        Build a bound SemesterInlineFormset from a list of field dicts.
        Each dict maps field name → value.
        """
        SemesterFormset = inlineformset_factory(
            Course, Semester,
            formset=SemesterInlineFormset,
            fields=("name", "starts_on", "ends_on", "status", "max_students", "enrollment_open"),
            extra=0,
            can_delete=True,
        )
        total = len(forms_data)
        management = {
            "semesters-TOTAL_FORMS": str(total),
            "semesters-INITIAL_FORMS": "0",
            "semesters-MIN_NUM_FORMS": "0",
            "semesters-MAX_NUM_FORMS": "1000",
        }
        post_data = dict(management)
        for i, data in enumerate(forms_data):
            for key, value in data.items():
                post_data[f"semesters-{i}-{key}"] = value
        return SemesterFormset(post_data, instance=self.course, prefix="semesters")

    def _row(self, starts_on, ends_on, status=SemesterStatus.SCHEDULED, name="Sem"):
        row = {
            "name": name,
            "starts_on": starts_on.isoformat(),
            "status": status,
            "enrollment_open": "1",
        }
        if ends_on:
            row["ends_on"] = ends_on.isoformat()
        return row

    def test_two_active_in_same_submission_raises(self):
        formset = self._make_formset([
            self._row(date(2026, 1, 1), date(2026, 6, 30), SemesterStatus.ACTIVE, "A"),
            self._row(date(2026, 7, 1), date(2026, 12, 31), SemesterStatus.ACTIVE, "B"),
        ])
        self.assertFalse(formset.is_valid())
        self.assertTrue(len(formset.non_form_errors()) > 0)

    def test_two_overlapping_scheduled_in_same_submission_raises(self):
        formset = self._make_formset([
            self._row(date(2026, 1, 1), date(2026, 6, 30), name="A"),
            self._row(date(2026, 4, 1), date(2026, 9, 30), name="B"),
        ])
        self.assertFalse(formset.is_valid())

    def test_ends_before_starts_in_formset_raises(self):
        formset = self._make_formset([
            self._row(date(2026, 6, 1), date(2026, 3, 1), name="A"),
        ])
        self.assertFalse(formset.is_valid())

    def test_ends_same_as_starts_in_formset_raises(self):
        formset = self._make_formset([
            self._row(date(2026, 3, 1), date(2026, 3, 1), name="A"),
        ])
        self.assertFalse(formset.is_valid())

    def test_valid_non_overlapping_passes(self):
        formset = self._make_formset([
            self._row(date(2026, 1, 1), date(2026, 6, 30), name="A"),
            self._row(date(2026, 7, 1), date(2026, 12, 31), name="B"),
        ])
        self.assertTrue(formset.is_valid(), formset.errors)

    def test_one_active_one_non_overlapping_scheduled_passes(self):
        formset = self._make_formset([
            self._row(date(2026, 1, 1), date(2026, 6, 30), SemesterStatus.ACTIVE, "A"),
            self._row(date(2026, 7, 1), date(2026, 12, 31), SemesterStatus.SCHEDULED, "B"),
        ])
        self.assertTrue(formset.is_valid(), formset.errors)