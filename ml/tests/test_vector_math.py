import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.cosine_distance_func import cosine_distance
from services.matching import find_best_match
from services.vector_utils import create_profile_vector_from_embeddings


class VectorMathTests(unittest.TestCase):
    def test_profile_vector_keeps_embedding_dimension(self):
        embeddings = [[1.0] + [0.0] * 767, [0.0, 1.0] + [0.0] * 766]
        vector = create_profile_vector_from_embeddings(embeddings)
        self.assertEqual(len(vector), 768)

    def test_cosine_distance_handles_zero_vector(self):
        distance = cosine_distance([0.0, 0.0], [1.0, 0.0])
        self.assertEqual(distance, 1.0)

    def test_find_best_match_respects_threshold(self):
        match_id = find_best_match(
            user_vector=[1.0, 0.0],
            user_id=1,
            other_users=[
                {"id": 2, "profile_vector": [0.0, 1.0]},
                {"id": 3, "profile_vector": [1.0, 0.0]},
            ],
            threshold=0.9,
        )
        self.assertEqual(match_id, 3)


if __name__ == "__main__":
    unittest.main()
