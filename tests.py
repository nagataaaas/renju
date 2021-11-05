import unittest
import sys

from datetime import date, datetime

from main import (Table, Move, Point, load_data, write_data)
from config import (RAISE_ON_CSV_COUNT_ERROR, TABLE_SIZE, TABLE_STARTS_WITH_ONE)


class Test(unittest.TestCase):

    def test_read_file_success_single(self):
        with open('tmp', 'w') as f:
            f.write('1,1;8;8')
        actual = load_data('tmp')
        self.assertEqual((1, [Move(1, Point(8-TABLE_STARTS_WITH_ONE, 8-TABLE_STARTS_WITH_ONE))]), actual)

    def test_read_file_success_multiple(self):
        with open('tmp', 'w') as f:
            f.write('2,1;8;8,2;7;7')
        actual = load_data('tmp')
        self.assertEqual((2, [Move(1, Point(8-TABLE_STARTS_WITH_ONE, 8-TABLE_STARTS_WITH_ONE)),
                                Move(2, Point(7-TABLE_STARTS_WITH_ONE, 7-TABLE_STARTS_WITH_ONE))
                                ]), actual)

    def test_read_file_not_exist(self):
        actual = load_data('tmp2')
        self.assertEqual((0, []), actual)

    def test_read_file_empty(self):
        with open('tmp', 'w') as f:
            pass
        actual = load_data('tmp')
        self.assertEqual((0, []), actual)

    def test_read_file_fail_wrong_count(self):
        with open('tmp', 'w') as f:
            f.write('1,1;8;8,2;7;7')
        self.assertRaises(ValueError, load_data, 'tmp')

    def test_table_compute_success(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6))]
        table = Table(len(moves), moves)
        actual = table.compute()
        self.assertEqual((None, None), actual)

    def test_table_compute_fail_not_alternate_player(self):
        moves = [Move(1, Point(7, 7)), Move(1, Point(6, 7)), Move(1, Point(7, 6)), Move(1, Point(6, 6))]
        table = Table(len(moves), moves)
        actual = table.compute()
        self.assertEqual((Move(1, Point(6, 7)), False), actual)

    def test_table_compute_fail_not_alternate_player2(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(1, Point(6, 6))]
        table = Table(len(moves), moves)
        actual = table.compute()
        self.assertEqual((Move(1, Point(6, 6)), False), actual)

    def test_table_compute_fail_same_place(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(7, 7)), Move(1, Point(7, 6)), Move(1, Point(6, 6))]
        table = Table(len(moves), moves)
        actual = table.compute()
        self.assertEqual((Move(2, Point(7, 7)), False), actual)

    def test_table_compute_success_win(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
        Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4)),
        Move(1, Point(7, 3)), Move(2, Point(6, 3))]
        table = Table(len(moves), moves)
        actual = table.compute()
        self.assertEqual((Move(1, Point(7, 3)), True), actual)

    def test_table_stop_opponent_win(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
        Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4))]
        table = Table(len(moves), moves)
        table.compute()
        actual = table.choose_next_move(2)
        self.assertIn(actual[0], [Move(2, Point(7, 3)), Move(2, Point(7, 8))])

    def test_table_win_aggressive(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
        Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4))]
        table = Table(len(moves), moves)
        table.compute()
        actual = table.choose_next_move(1)
        self.assertIn(actual[0], [Move(1, Point(7, 3)), Move(1, Point(7, 8))])



if __name__ == "__main__":

    unittest.main()