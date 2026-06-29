from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.crud.psychological import get_next_question_for_user


class FakeResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values

    def scalar_one_or_none(self):
        return self._values


class FakeSession:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def execute(self, statement):
        return next(self._responses)


class PsychologicalSeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_next_question_returns_first_question_from_seeded_category(self):
        categories = [SimpleNamespace(id=1, name="Самоопределение", order=1)]
        questions = [SimpleNamespace(id=101, category_id=1, text="Что в себе вы считаете самой сильной стороной?")]
        session = FakeSession(
            [
                FakeResult(categories),
                FakeResult([]),
                FakeResult(questions),
            ]
        )

        result = await get_next_question_for_user(session, user_id=42)

        self.assertIsNotNone(result)
        question, current_number, total_questions = result
        self.assertEqual(question.id, 101)
        self.assertEqual(current_number, 1)
        self.assertEqual(total_questions, 10)


if __name__ == "__main__":
    unittest.main()
