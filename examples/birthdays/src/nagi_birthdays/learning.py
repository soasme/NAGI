"""Learning birthdays. Learners call these as birthdays.remember(...)."""

from nagi.api import Lesson

__all__ = ["remember"]


def remember(lesson: Lesson, person: str, day: str) -> None:
    lesson.state.setdefault("birthdays", {})[person] = day
