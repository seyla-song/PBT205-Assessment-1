"""
Unit tests for the contact tracing logic. These don't need RabbitMQ.

Run with:
    python -m unittest -v
"""

import unittest

from person import next_square
from tracker import ContactTracker


class ContactTrackerTest(unittest.TestCase):

    def test_no_contact_on_different_squares(self):
        t = ContactTracker(10)
        t.move("alice", 1, 1, timestamp=1)
        self.assertEqual(t.move("bob", 2, 2, timestamp=2), [])
        self.assertEqual(t.query("alice"), [])

    def test_contact_is_logged_for_both_people(self):
        t = ContactTracker(10)
        t.move("alice", 3, 3, timestamp=1)
        self.assertEqual(t.move("bob", 3, 3, timestamp=2), ["alice"])
        self.assertEqual([c["name"] for c in t.query("alice")], ["bob"])
        self.assertEqual([c["name"] for c in t.query("bob")], ["alice"])

    def test_three_people_on_one_square(self):
        t = ContactTracker(10)
        t.move("alice", 0, 0, timestamp=1)
        t.move("bob", 0, 0, timestamp=2)
        self.assertEqual(t.move("carol", 0, 0, timestamp=3), ["alice", "bob"])
        self.assertEqual({c["name"] for c in t.query("carol")}, {"alice", "bob"})

    def test_query_is_reverse_chronological(self):
        t = ContactTracker(10)
        t.move("alice", 5, 5, timestamp=0)
        t.move("bob", 5, 5, timestamp=1)
        t.move("bob", 9, 9, timestamp=2)
        t.move("carol", 5, 5, timestamp=3)
        self.assertEqual([c["name"] for c in t.query("alice")], ["carol", "bob"])

    def test_repeat_contact_listed_once_with_latest_time(self):
        t = ContactTracker(10)
        t.move("alice", 5, 5, timestamp=0)
        t.move("bob", 5, 5, timestamp=1)
        t.move("carol", 5, 5, timestamp=2)
        t.move("bob", 6, 6, timestamp=3)
        t.move("bob", 5, 5, timestamp=4)   # meets alice and carol again
        contacts = t.query("alice")
        self.assertEqual([c["name"] for c in contacts], ["bob", "carol"])
        self.assertEqual(contacts[0]["count"], 2)
        self.assertEqual(contacts[0]["timestamp"], 4)

    def test_staying_on_same_square_is_not_a_new_contact(self):
        t = ContactTracker(10)
        t.move("alice", 1, 1, timestamp=0)
        t.move("bob", 1, 1, timestamp=1)
        self.assertEqual(t.move("bob", 1, 1, timestamp=2), [])
        self.assertEqual(t.query("alice")[0]["count"], 1)

    def test_no_contact_after_moving_away(self):
        t = ContactTracker(10)
        t.move("alice", 1, 1, timestamp=0)
        t.move("alice", 2, 2, timestamp=1)
        self.assertEqual(t.move("bob", 1, 1, timestamp=2), [])

    def test_leave_removes_person_but_keeps_history(self):
        t = ContactTracker(10)
        t.move("alice", 4, 4, timestamp=0)
        t.move("bob", 4, 4, timestamp=1)
        t.leave("alice")
        self.assertNotIn("alice", t.positions)
        self.assertEqual(t.move("carol", 4, 4, timestamp=2), ["bob"])
        self.assertEqual([c["name"] for c in t.query("alice")], ["bob"])

    def test_off_board_move_is_rejected(self):
        t = ContactTracker(10)
        for x, y in [(-1, 0), (0, -1), (10, 0), (0, 10)]:
            with self.assertRaises(ValueError):
                t.move("alice", x, y)
        self.assertNotIn("alice", t.positions)

    def test_large_board(self):
        t = ContactTracker(1000)
        t.move("alice", 999, 999, timestamp=0)
        self.assertEqual(t.move("bob", 999, 999, timestamp=1), ["alice"])
        with self.assertRaises(ValueError):
            t.move("bob", 1000, 999)


class NextSquareTest(unittest.TestCase):

    def test_always_one_king_move_away(self):
        for _ in range(200):
            x, y = next_square(5, 5, 10)
            self.assertLessEqual(max(abs(x - 5), abs(y - 5)), 1)
            self.assertNotEqual((x, y), (5, 5))

    def test_never_leaves_the_board_from_corners(self):
        for size in (2, 10, 1000):
            for start in [(0, 0), (0, size - 1), (size - 1, 0), (size - 1, size - 1)]:
                for _ in range(100):
                    x, y = next_square(*start, size)
                    self.assertTrue(0 <= x < size and 0 <= y < size)

    def test_one_by_one_board_stays_put(self):
        self.assertEqual(next_square(0, 0, 1), (0, 0))


if __name__ == "__main__":
    unittest.main()
