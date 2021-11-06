import unittest
import sys

from datetime import date, datetime

from main import (Table, Move, Point, load_data, write_data, Line, Direction)
import config


class TestIO(unittest.TestCase):

    def test_read_file_success_single(self):
        with open('tmp', 'w') as f:
            f.write('1,1;8;8')
        actual = load_data('tmp')
        self.assertEqual((1, [Move(1, Point(8 - config.TABLE_STARTS_WITH_ONE, 8 - config.TABLE_STARTS_WITH_ONE))]),
                         actual)

    def test_read_file_success_multiple(self):
        with open('tmp', 'w') as f:
            f.write('2,1;8;8,2;7;7')
        actual = load_data('tmp')
        self.assertEqual((2, [Move(1, Point(8 - config.TABLE_STARTS_WITH_ONE, 8 - config.TABLE_STARTS_WITH_ONE)),
                              Move(2, Point(7 - config.TABLE_STARTS_WITH_ONE, 7 - config.TABLE_STARTS_WITH_ONE))
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

    def test_read_file_warn_wrong_count(self):
        config.RAISE_ON_CSV_COUNT_ERROR = False
        with open('tmp', 'w') as f:
            f.write('1,1;8;8,2;7;7')
        with self.assertWarns(Warning):
            actual = load_data('tmp')
        self.assertEqual((1, [Move(program_number=1, point=Point(y=7, x=7)),
                              Move(program_number=2, point=Point(y=6, x=6))]), actual)
        config.RAISE_ON_CSV_COUNT_ERROR = True

    def test_write_file_1(self):
        table = Table([])
        write_data('tmp', table)
        with open('tmp', 'r') as f:
            actual = f.read()
        self.assertEqual('0,', actual)

    def test_write_file_2(self):
        config.TABLE_STARTS_WITH_ONE = True
        table = Table([Move(1, Point(7, 7)), Move(2, Point(8, 8))])
        write_data('tmp', table)
        with open('tmp', 'r') as f:
            actual = f.read()
        self.assertEqual('2,1;8;8,2;9;9', actual)
        config.TABLE_STARTS_WITH_ONE = True

    def test_write_file_3(self):
        config.TABLE_STARTS_WITH_ONE = False
        table = Table([Move(1, Point(7, 7)), Move(2, Point(8, 8))])
        write_data('tmp', table)
        with open('tmp', 'r') as f:
            actual = f.read()
        self.assertEqual('2,1;7;7,2;8;8', actual)
        config.TABLE_STARTS_WITH_ONE = True

    def test_write_file_overwrite(self):
        with open('tmp', 'w') as f:
            f.write('placeholder')

        table = Table([])
        write_data('tmp', table)
        with open('tmp', 'r') as f:
            actual = f.read()
        self.assertEqual('0,', actual)


class TestLine(unittest.TestCase):

    def test_line_error_x_y_opposite(self):
        distance = 5
        for direction in Direction:
            dy = direction.value[0] * distance
            dx = direction.value[1] * distance
            if abs(dy) != abs(dx):
                self.assertRaises(ValueError, Line, direction, Point(10, 10), Point(10 + dx, 10 + dy), 1)

            dy = direction.value[0] * -distance
            dx = direction.value[1] * -distance
            if abs(dy) != abs(dx):
                self.assertRaises(ValueError, Line, direction, Point(10, 10), Point(10 + dx, 10 + dy), 1)

    def test_line_error(self):
        for direction in Direction:
            self.assertRaises(ValueError, Line, direction, Point(10, 10), Point(11, 12), 1)

    def test_length(self):
        distance = 5
        for direction in Direction:
            dy = direction.value[0] * distance
            dx = direction.value[1] * distance
            actual = Line(direction, Point(10, 10), Point(10 + dy, 10 + dx), 1).length
            self.assertEqual(actual, distance + 1)

            dy = direction.value[0] * -distance
            dx = direction.value[1] * -distance
            actual = Line(direction, Point(10, 10), Point(10 + dy, 10 + dx), 1).length
            self.assertEqual(actual, distance + 1)

    def test_length_long(self):
        line = Line(Direction.Vertical, Point(0, 0), Point(99, 0), 1)
        actual = line.length
        self.assertEqual(100, actual)

    def test_extend_first(self):
        for direction in Direction:
            dy = direction.value[0]
            dx = direction.value[1]
            actual = Line(direction, Point(10, 10), Point(10 + dy, 10 + dx), 1).extend_first()
            self.assertEquals(actual, (Line(direction, Point(10 - dy, 10 - dx),
                                            Point(10 + dy, 10 + dx), 1), Point(10 - dy, 10 - dx), True))
            actual = Line(direction, Point(10, 10), Point(10, 10), 1).extend_first()
            self.assertEquals(actual, (Line(direction, Point(10 - dy, 10 - dx),
                                            Point(10, 10), 1), Point(10 - dy, 10 - dx), True))

    def test_extend_second(self):
        for direction in Direction:
            dy = direction.value[0]
            dx = direction.value[1]
            actual = Line(direction, Point(10, 10), Point(10 + dy, 10 + dx), 1).extend_second()
            self.assertEquals(actual, (Line(direction, Point(10, 10),
                                            Point(10 + dy * 2, 10 + dx * 2), 1), Point(10 + dy * 2, 10 + dx * 2), True))
            actual = Line(direction, Point(10, 10), Point(10, 10), 1).extend_second()
            self.assertEquals(actual, (Line(direction, Point(10, 10),
                                            Point(10 + dy, 10 + dx), 1), Point(10 + dy, 10 + dx), True))


class TestTable(unittest.TestCase):
    def test_is_win_positive(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
                 Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4)),
                 Move(1, Point(7, 3)), Move(2, Point(6, 3))]
        table = Table(moves)
        table.compute()
        actual = table.is_win(1)
        self.assertEqual(True, actual)

    def test_is_win_negative(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
                 Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4))]
        table = Table(moves)
        table.compute()
        actual = table.is_win(1)
        self.assertEqual(False, actual)

    def test_is_win_negative_lose(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
                 Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4)),
                 Move(1, Point(7, 3)), Move(2, Point(6, 3))]
        table = Table(moves)
        table.compute()
        actual = table.is_win(2)
        self.assertEqual(False, actual)

    def test_table_compute_success(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6))]
        table = Table(moves)
        actual = table.compute()
        self.assertEqual((None, None), actual)

    def test_table_compute_fail_not_alternate_player(self):
        moves = [Move(1, Point(7, 7)), Move(1, Point(6, 7)), Move(1, Point(7, 6)), Move(1, Point(6, 6))]
        table = Table(moves)
        actual = table.compute()
        self.assertEqual((Move(1, Point(6, 7)), False), actual)

    def test_table_compute_fail_not_alternate_player2(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(1, Point(6, 6))]
        table = Table(moves)
        actual = table.compute()
        self.assertEqual((Move(1, Point(6, 6)), False), actual)

    def test_table_compute_fail_same_place(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(7, 7)), Move(1, Point(7, 6)), Move(1, Point(6, 6))]
        table = Table(moves)
        actual = table.compute()
        self.assertEqual((Move(2, Point(7, 7)), False), actual)

    def test_table_compute_success_win(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
                 Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4)),
                 Move(1, Point(7, 3)), Move(2, Point(6, 3))]
        table = Table(moves)
        actual = table.compute()
        self.assertEqual((Move(1, Point(7, 3)), True), actual)


class TestMove(unittest.TestCase):
    def test_table_stop_opponent_win(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
                 Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4))]
        table = Table(moves)
        table.compute()
        actual = table.choose_next_move(2)
        self.assertIn(actual[0], [Move(2, Point(7, 3)), Move(2, Point(7, 8))])

    def test_table_win_aggressive(self):
        moves = [Move(1, Point(7, 7)), Move(2, Point(6, 7)), Move(1, Point(7, 6)), Move(2, Point(6, 6)),
                 Move(1, Point(7, 5)), Move(2, Point(6, 5)), Move(1, Point(7, 4)), Move(2, Point(6, 4))]
        table = Table(moves)
        table.compute()
        actual = table.choose_next_move(1)
        self.assertIn(actual[0], [Move(1, Point(7, 3)), Move(1, Point(7, 8))])


if __name__ == "__main__":
    unittest.main()
