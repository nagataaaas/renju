import warnings
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from typing import List, Union, Dict, Tuple

import config


@dataclass(frozen=True)
class Point:
    """
    :param y: y-coordinate
    :param x: x-coordinate
    """
    y: int
    x: int

    def __post_init__(self):
        if not 0 <= self.y < config.TABLE_SIZE:
            raise ValueError(
                'y coordinate is invalid (given: {}). '.format(self.y))
        if not 0 <= self.x < config.TABLE_SIZE:
            raise ValueError(
                'x coordinate is invalid (given: {}). '.format(self.x))


class Direction(Enum):
    Horizontal = (0, 1)  # -
    Vertical = (1, 0)  # |
    Diagonal_UL_BR = (1, 1)  # \
    Diagonal_UR_BL = (1, -1)  # /

    def __repr__(self):
        return 'Direction.{}'.format(self.name)


class Line:
    def __init__(self, direction: Direction, first: Point, second: Point):
        """
        Line of Go-Ishi
        :param direction: Direction of Line
        :param first: first point of line
        :param second: second point of line
        """
        self.direction = direction
        self.first = first
        self.second = second

    def extend_first(self) -> Union[Tuple['Line', Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `first` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """
        dy, dx = self.direction.value
        next_y = self.first.y - dy
        next_x = self.first.x - dx

        if not 0 <= next_x < config.TABLE_SIZE or not 0 <= next_y < config.TABLE_SIZE:
            return None, None, False

        new_point = Point(next_y, next_x)

        return Line(self.direction, new_point, self.second), new_point, True

    def extend_second(self) -> Union[Tuple['Line', Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `second` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """

        dy, dx = self.direction.value
        next_y = self.second.y + dy
        next_x = self.second.x + dx

        if not 0 <= next_x < config.TABLE_SIZE or not 0 <= next_y < config.TABLE_SIZE:
            return None, None, False

        new_point = Point(next_y, next_x)

        return Line(self.direction, self.first, new_point), new_point, True

    def __repr__(self):
        return 'Line(direction={!r}, first={!r}, second={!r})'.format(self.direction, self.first, self.second)


@dataclass(frozen=True)
class Move:
    """
    Single Move of Renju
    :param program_number: Player Number
    :param point: Point where player placed GoIshi
    """
    program_number: int
    point: Point


class Table:
    def __init__(self, moves_count: int, moves: List[Move]):
        """
        Table of Renju
        :param moves_count: All moves count
        :param moves: All moves
        """
        self.moves_count = moves_count
        self.moves = moves

        self.table: List[List[Union[int, None]]] = [[None for _ in range(config.TABLE_SIZE)] for _ in
                                                    range(config.TABLE_SIZE)]

    def compute(self) -> Union[None, Move]:
        """
        Compute all moves and update table. If there is any foul, return it
        :return: Move if foul move is there. Otherwise, None
        """
        for move in self.moves:
            if self.compute_move(move):
                return move

    def compute_move(self, move: Move) -> bool:
        """
        Compute single move and return whether move is fault.
        :param move: Move to compute
        :return: Whether fault of not.
        """
        if self.check_fault(move):
            return True
        self.table[move.point.y][move.point.x] = move.program_number
        return False

    def check_fault(self, move: Move) -> bool:
        """
        Check if the move is foul
        :param move: Move to be judged
        :return: boolean
        """
        program_number = move.program_number
        y = move.point.y
        x = move.point.x
        if self.table[y][x]:
            return True

        is_black = not self.moves_count or program_number == self.moves[0].program_number

        if not is_black:
            return False

        current_score = self.get_lines(program_number)
        new = self.copy()
        new.table[y][x] = program_number
        new_score = new.get_lines(program_number)

        if len(new_score[3]) - len(current_score[3]) >= 2 or \
                len(new_score[4]) - len(current_score[4]) >= 2 or max(new_score.keys()) > 5:
            return True

        return False

    def get_lines(self, program_number: int) -> Dict[int, List[Line]]:
        """
        Compute how many lines are there is the table
        :param program_number: Compute as
        :return: Dict in format of {length: count}
        """
        result = defaultdict(list)

        # horizontal
        for y_ind, y in enumerate(self.table):
            started = False
            start = None
            for x, val in enumerate(y):
                if val == program_number:
                    if not started:
                        started = True
                        start = x
                elif started:
                    started = False
                    result[x - start].append(Line(Direction.Horizontal, Point(y_ind, start), Point(y_ind, x - 1)))
            if started:
                result[x - start + 1].append(Line(Direction.Horizontal, Point(y_ind, start), Point(y_ind, x)))

        # vertical
        for x, line in enumerate(zip(*self.table)):
            started = False
            start = None
            for y, val in enumerate(line):
                if val == program_number:
                    if not started:
                        started = True
                        start = y
                elif started:
                    started = False
                    result[y - start].append(Line(Direction.Vertical, Point(y - 1, x), Point(start, x)))
            if started:
                result[y - start + 1].append(Line(Direction.Vertical, Point(y, x), Point(start, x)))

        # diagonal
        for offset in range(config.TABLE_SIZE * 2 - 1):
            x = max(offset - config.TABLE_SIZE, 0)
            y = max(config.TABLE_SIZE - offset, 0)
            if max(x, y) == config.TABLE_SIZE:
                continue

            started = False
            start = None
            for dist in range(config.TABLE_SIZE - max(x, y)):
                val = self.table[y + dist][x + dist]
                if val == program_number:
                    if not started:
                        started = True
                        start = dist
                elif started:
                    started = False
                    result[dist - start].append(
                        Line(Direction.Diagonal_UL_BR, Point(y + start, x + start), Point(y + dist - 1, x + dist - 1)))
            if started:
                result[dist - start + 1].append(
                    Line(Direction.Diagonal_UL_BR, Point(y + start, x + start), Point(y + dist, x + dist)))

            started = False
            start = None
            _x = x
            x = config.TABLE_SIZE - x - 1
            for dist in range(config.TABLE_SIZE - max(_x, y)):
                val = self.table[y + dist][x - dist]
                if val == program_number:
                    if not started:
                        started = True
                        start = dist
                elif started:
                    started = False
                    result[dist - start].append(
                        Line(Direction.Diagonal_UR_BL, Point(y + start, x - start), Point(y + dist - 1, x - dist + 1)))
            if started:
                result[dist - start + 1].append(
                    Line(Direction.Diagonal_UR_BL, Point(y + start, x - start), Point(y + dist, x - dist)))

        return result

    def eval_condition(self, program_number: int) -> int:
        pass

    def available_extended_points(self, program_number: int, distance: int = 5) -> List[Point]:
        """
        return available points which is an extension of line
        :param program_number: Compute as
        :param distance: distance threshold to be considered
        :return: List[Point]. available options
        """
        lines = list(chain.from_iterable(self.get_lines(program_number).values()))
        options = set()

        for line in lines:
            initial = line

            table = self.copy()
            extends = 0
            while True:
                if extends == distance:
                    break
                line, point, extendable = line.extend_first()
                if not extendable or table.compute_move(Move(program_number, point)):
                    break
                options.add(point)
                extends += 1

            table = self.copy()
            line = initial
            extends = 0
            while True:
                if extends == distance:
                    break
                line, point, extendable = line.extend_second()
                if not extendable or table.compute_move(Move(program_number, point)):
                    break
                options.add(point)
                extends += 1

        return list(options)

    @property
    def me(self) -> int:
        """
        Create or get next program's number
        :return: int. program number
        """
        if self.moves_count == 0:
            return 1
        elif self.moves_count == 1:
            return self.moves[0].program_number + 1
        return self.moves[-2].program_number

    def copy(self) -> 'Table':
        """
        Create copy of `self`.
        :return: Table. copy of itself.
        """
        new = Table(self.moves_count, self.moves[:])
        for y, line in enumerate(self.table):
            for x, val in enumerate(line):
                new.table[y][x] = val
        return new

    def pretty_print(self):
        """
        pretty print the table. '―｜・○●'
        """
        nums = ['１', '２', '３', '４', '５', '６', '７', '８', '９', '10', '11', '12', '13', '14', '15']

        lines = ['　　' + '　'.join(nums)]
        for y_ind, y in enumerate(self.table):
            line = [nums[y_ind], '　']
            for x in y:
                if x:
                    if x == self.moves[0].program_number:
                        line.append('●')
                    else:
                        line.append('○')
                else:
                    line.append('・')
                line.append('―')
            line.pop()
            lines.append(''.join(line))
            lines.append('　　' + ('｜　' * config.TABLE_SIZE)[:-1])
        lines.pop()
        print('\n'.join(lines))


def load_data(filename: str) -> Tuple[int, List[Move]]:
    """
    Load data with given filename
    :param filename: filename of moves
    :return: Tuple[total_moves, List[Move]]
    """
    with open(filename, 'r') as f:
        data = f.read()
    count, *data = [list(map(int, d.split(';'))) for d in data.split(',')]
    count = count[0]
    moves = [Move(program_number, Point(y - config.TABLE_STARTS_WITH_ONE, x - config.TABLE_STARTS_WITH_ONE)) for
             program_number, y, x in data]

    if count != len(moves):
        if config.RAISE_ON_CSV_ERROR:
            raise ValueError('total count is incorrect. (given: {}, moves_length: {})'.format(count, len(moves)))
        warnings.warn('total count is incorrect. (given: {}, moves_length: {})'.format(count, len(moves)))

    return count, moves


def write_data(filename: str, moves: List[Move]):
    """
    Write moves with given filename
    :param filename: filename to write
    :param moves: moves to write
    """
    with open(filename, 'w') as f:
        f.write('{},{}'.format(str(len(moves)), ','.join(
            [';'.join(map(str, [move.program_number, move.point.y + config.TABLE_STARTS_WITH_ONE,
                                move.point.x + config.TABLE_STARTS_WITH_ONE])) for move in moves])))


if __name__ == '__main__':
    # filename = sys.argv[1]

    count, data = load_data('data.txt')
    print(count, data)  # 4,1;5;6,2;6;6,1;5;7,2;5;8
    write_data('data.txt', data)
    table = Table(count, data)
    table.compute()
    table.pretty_print()
    move = table.available_extended_points(1, 2)
    print(move)
    for point in move:
        table.table[point.y][point.x] = 1
    table.pretty_print()
    print(table.get_lines(1))
    exit()
    t = Table(3, [Move(0, Point(3, 3)), Move(1, Point(0, 0)), Move(0, Point(3, 4)), Move(0, Point(3, 5)),
                  Move(0, Point(4, 4)), Move(0, Point(5, 4))])
    t.compute()
    print(t.get_lines(0))
    print(Line(direction=Direction.Horizontal, first=Point(y=3, x=3), second=Point(y=3, x=5)))
    print()
    l, m, a = Line(direction=Direction.Horizontal, first=Point(y=3, x=3), second=Point(y=3, x=5)).extend_first()
    if a:
        print(t.compute_move(Move(0, m)))
        l, m, a = l.extend_first()
        print(t.compute_move(Move(0, m)))
        l, m, a = l.extend_first()
        print(t.compute_move(Move(0, m)))
        l, m, a = l.extend_second()
        print(t.compute_move(Move(0, m)))
        l, m, a = l.extend_second()
        print(t.get_lines(0))
        print(t.compute_move(Move(0, m)))
        print(t.get_lines(0))
