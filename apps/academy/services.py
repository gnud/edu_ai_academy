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
