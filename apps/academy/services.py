from .models import Course, Semester


def save_course(obj: Course, user, change: bool) -> Course:
    if not change:
        obj.created_by = user
    obj.save()
    return obj


def save_semester(obj: Semester) -> Semester:
    obj.full_clean()
    obj.save()
    return obj


def toggle_course_published(obj: Course) -> Course:
    obj.is_published = not obj.is_published
    obj.save(update_fields=["is_published"])
    return obj


def toggle_course_active(obj: Course) -> Course:
    obj.is_active = not obj.is_active
    obj.save(update_fields=["is_active"])
    return obj
