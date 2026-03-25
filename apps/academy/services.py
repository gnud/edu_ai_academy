from .models import Course


def save_course(obj: Course, user, change: bool) -> Course:
    if not change:
        obj.created_by = user
    obj.save()
    return obj
