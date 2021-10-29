import sys
from typing import List, Union, Dict, Tuple
from collections import defaultdict
from enum import Enum

TABLE_SIZE = 15


class Point:
    def __init__(self, y: int, x: int):
        """
        :param y: y-coordinate
        :param x: x-coordinate
        """
        self.y = y
        self.x = x

    def __repr__(self):
        return 'Point(y={!r}, x={!r})'.format(self.y, self.x)


class Direction(Enum):
    Horizontal = 0  # -
    Vertical = 1  # |
    Diagonal_LU_RB = 2  # \
    Diagonal_LB_RU = 2  # /

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

        id_dy_norm = self.second.y - self.first.y
        if id_dy_norm:
            id_dy_norm = id_dy_norm // abs(id_dy_norm)

        id_dx_norm = self.second.x - self.first.x
        if id_dx_norm:
            id_dx_norm = id_dx_norm // abs(id_dx_norm)

        next_y = self.first.y - id_dy_norm
        next_x = self.first.x - id_dx_norm

        if not 0 <= next_x < TABLE_SIZE or not 0 <= next_y < TABLE_SIZE:
            return None, None, False

        new_point = Point(next_y, next_x)

        return Line(self.direction, new_point, self.second), new_point, True

    def extend_second(self) -> Union[Tuple['Line', Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `second` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """

        id_dy_norm = self.second.y - self.first.y
        if id_dy_norm:
            id_dy_norm = id_dy_norm // abs(id_dy_norm)

        id_dx_norm = self.second.x - self.first.x
        if id_dx_norm:
            id_dx_norm = id_dx_norm // abs(id_dx_norm)

        next_y = self.second.y + id_dy_norm
        next_x = self.second.x + id_dx_norm

        if not 0 <= next_x < TABLE_SIZE or not 0 <= next_y < TABLE_SIZE:
            return None, None, False

        new_point = Point(next_y, next_x)

        return Line(self.direction, self.first, new_point), new_point, True

    def __repr__(self):
        return 'Line(direction={!r}, first={!r}, second={!r})'.format(self.direction, self.first, self.second)


class Move:
    def __init__(self, program_number: int, point: Point):
        """
        Single Move of Renju
        :param program_number: Player Number
        :param point: Point where player placed GoIshi
        """
        self.program_number = program_number
        self.point = point

    def __repr__(self):
        return 'Move(program_number={!r}, point={!r})'.format(self.program_number, self.point)


class Table:
    def __init__(self, moves_count: int, moves: List[Move]):
        """
        Table of Renju
        :param moves_count: All moves count
        :param moves: All moves
        """
        self.moves_count = moves_count
        self.moves = moves

        self.table: List[List[Union[int, None]]] = [[None for _ in range(TABLE_SIZE)] for _ in range(TABLE_SIZE)]

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

        current_score = self.eval(program_number)
        new = self.copy()
        new.table[y][x] = program_number
        new_score = new.eval(program_number)


        if len(new_score[3]) - len(current_score[3]) >= 2 or \
                len(new_score[4]) - len(current_score[4]) >= 2 or max(new_score.keys()) > 5:
            return True

        return False

    def eval(self, program_number: int) -> Dict[int, List[Line]]:
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
                    if x - start == 1:
                        add_flag = True
                        for x_ in range(-1, 2):
                            for y_ in [-1, 1]:
                                if x + x_ not in range(TABLE_SIZE) or y_ind + y_ not in range(TABLE_SIZE):
                                    continue
                                if self.table[y_ind + y_][x + x_] == program_number:
                                    add_flag = False
                        if add_flag:
                            result[1].append(Line(Direction.Horizontal, Point(y_ind, start), Point(y_ind, start)))
                        continue
                    result[x - start].append(Line(Direction.Horizontal, Point(y_ind, start), Point(y_ind, x - 1)))

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
                    if y - start == 1:
                        continue
                    result[y - start].append(Line(Direction.Vertical, Point(y - 1, x), Point(start, x)))

        # diagonal
        for offset in range(TABLE_SIZE * 2):
            x = max(offset - TABLE_SIZE, 0)
            y = max(TABLE_SIZE - offset, 0)
            if max(x, y) == TABLE_SIZE:
                continue

            started = False
            start = None
            for dist in range(TABLE_SIZE - max(x, y)):
                val = self.table[y + dist][x + dist]
                if val == program_number:
                    if not started:
                        started = True
                        start = dist
                elif started:
                    started = False
                    if dist - start == 1:
                        continue
                    result[dist - start].append(
                        Line(Direction.Diagonal_LU_RB, Point(y, x), Point(y + dist - 1, x + dist - 1)))

            started = False
            start = None
            x, y = y, x
            for dist in range(15 - max(x, y)):
                val = self.table[y - dist][x - dist]
                if val == program_number:
                    if not started:
                        started = True
                        start = dist
                elif started:
                    started = False
                    if dist - start == 1:
                        continue
                    result[dist - start].append(
                        Line(Direction.Diagonal_LB_RU, Point(y, x), Point(y - dist + 1, x - dist + 1)))

        return result

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


def load_data(filename: str) -> Tuple[int, List[Move]]:
    """
    Load data with given filename
    :param filename: filename of moves
    :return: Tuple[total_moves, List[Move]]
    """
    with open(filename, 'r') as f:
        data = f.read()
    count, *data = [list(map(int, d.split(';'))) for d in data.split(',')]
    moves = [Move(program_number, Point(y, x)) for program_number, y, x in data]

    return count, moves


def write_data(filename: str, moves: List[Move]):
    """
    Write moves with given filename
    :param filename: filename to write
    :param moves: moves to write
    """
    with open(filename, 'w') as f:
        f.write('{},{}'.format(str(len(moves)), ','.join([';'.join(map(str, [move.program_number, move.point.y, move.point.x])) for move in moves])))


if __name__ == '__main__':
    # filename = sys.argv[1]

    count, data = load_data('data.txt')
    print(count, data)  # 4,1;5;6,2;6;6,1;5;7,2;5;8
    data.append(Move(1, Point(5, 9)))
    write_data('data.txt', data)
    exit()
    t = Table(3, [Move(0, Point(3, 3)), Move(1, Point(0, 0)), Move(0, Point(3, 4)), Move(0, Point(3, 5)), Move(0, Point(4, 4)), Move(0, Point(5, 4))])
    t.compute()
    print(t.eval(0))
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
        print(t.eval(0))
        print(t.compute_move(Move(0, m)))
        print(t.eval(0))