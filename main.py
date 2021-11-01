import warnings
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from typing import List, Union, Dict, Tuple
import os

import config


class OptionType(Enum):
    Win = 3
    Checkmate = 2
    Preferable = 1
    OK = 4
    Trash = 0


class Option:
    def __init__(self, _type: OptionType, depth: int, point: Union['Point', None]):
        self.type = _type
        self.depth = depth
        self.point = point

    def add(self, option: 'Option') -> 'OptionWrapper':
        ow = OptionWrapper(self)
        ow.add(option)
        return ow

    def __repr__(self):
        return 'Option(type={!r}, depth={!r}, point={!r})'.format(self.type, self.depth, self.point)


class OptionWrapper:
    def __init__(self, option: Option):
        self.options = [option]

    def add(self, option: Option):
        ops = self.options[:]
        new = OptionWrapper(None)
        new.options = ops
        new.options.append(option)
        return new

    def max(self) -> Option:
        for v in self.options:
            if v.type == OptionType.Win:
                return v
        val = []
        for v in self.options:
            if v.type == OptionType.Checkmate:
                val.append(v)
        if val:
            val.sort(key=lambda x: x.depth)
            return val[0]

        val = []
        for v in self.options:
            if v.type == OptionType.Preferable:
                val.append(v)
        if val:
            val.sort(key=lambda x: x.depth)
            return val[0]

        val = []
        for v in self.options:
            if v.type == OptionType.OK:
                val.append(v)
        if val:
            val.sort(key=lambda x: x.depth)
            return val[0]

        val = []
        for v in self.options:
            if v.type == OptionType.Trash:
                val.append(v)
        if val:
            val.sort(key=lambda x: x.depth)
            return val[0]

    def __lt__(self, other: 'OptionWrapper'):
        me_win = any(option.type is OptionType.Win for option in self.options)
        op_win = any(option.type is OptionType.Win for option in other.options)
        if me_win ^ op_win:
            return not me_win

        for i in range(1, 3):
            me_win = any(option.depth == i and option.type is OptionType.Checkmate for option in self.options)
            op_win = any(option.depth == i and option.type is OptionType.Checkmate for option in other.options)
            if me_win - op_win:
                return not op_win > me_win

        for i in range(1, 3):
            me_win = any(option.depth == i and (option.type is OptionType.Checkmate or
                                                option.type is OptionType.Preferable) for option in self.options)
            op_win = any(option.depth == i and (option.type is OptionType.Checkmate or
                                                option.type is OptionType.Preferable) for option in other.options)
            if me_win - op_win:
                return not op_win > me_win

        for i in range(1, 3):
            me_win = any(option.depth == i and option.type is not OptionType.Trash for option in self.options)
            op_win = any(option.depth == i and option.type is not OptionType.Trash for option in other.options)
            if me_win - op_win:
                return not op_win > me_win
        return False
    def __repr__(self):
        return 'OptionWrapper(options={!r})'.format(self.options)

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
    Horizontal = (0, 1)  # →
    Vertical = (1, 0)  # ↓
    Diagonal_UL_BR = (1, 1)  # ↘︎
    Diagonal_UR_BL = (1, -1)  # ↙︎

    def __repr__(self):
        return 'Direction.{}'.format(self.name)


class Line:
    def __init__(self, direction: Direction, first: Point, second: Point, program_number: int):
        """
        Line of Go-Ishi
        :param direction: Direction of Line
        :param first: first point of line
        :param second: second point of line
        :param program_number: program number which made this line
        """
        self.direction = direction
        self.first = first
        self.second = second
        self.program_number = program_number

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

        return Line(self.direction, new_point, self.second, self.program_number), new_point, True

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

        return Line(self.direction, self.first, new_point, self.program_number), new_point, True

    @property
    def length(self) -> int:
        return max(abs(self.first.x - self.second.x), abs(self.first.y - self.second.y)) + 1

    def __repr__(self):
        return ('Line(direction={!r}, first={!r}, second={!r}, '
                'length={!r}, program_number={!r})'.format(self.direction, self.first, self.second, self.length,
                                                           self.program_number))


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
                    result[x - start].append(Line(Direction.Horizontal, Point(y_ind, start), Point(y_ind, x - 1),
                                                  program_number))
            if started:
                result[x - start + 1].append(Line(Direction.Horizontal, Point(y_ind, start), Point(y_ind, x),
                                                  program_number))

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
                    result[y - start].append(Line(Direction.Vertical, Point(start, x), Point(y - 1, x), program_number))
            if started:
                result[y - start + 1].append(Line(Direction.Vertical, Point(start, x), Point(y, x), program_number))

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
                    result[dist - start].append(Line(Direction.Diagonal_UL_BR, Point(y + start, x + start),
                                                     Point(y + dist - 1, x + dist - 1), program_number))
            if started:
                result[dist - start + 1].append(Line(Direction.Diagonal_UL_BR, Point(y + start, x + start),
                                                     Point(y + dist, x + dist), program_number))

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
                    result[dist - start].append(Line(Direction.Diagonal_UR_BL, Point(y + start, x - start),
                                                     Point(y + dist - 1, x - dist + 1), program_number))
            if started:
                result[dist - start + 1].append(
                    Line(Direction.Diagonal_UR_BL, Point(y + start, x - start), Point(y + dist, x - dist),
                         program_number))

        return result

    def eval_condition(self, program_number: int) -> int:
        # view 2 -> 1 -> 1
        pass

    def can_win_with_line(self, line: Line) -> Option:
        """
        return preferable option and priority
        :param line: line to extend
        :return: [priority(3: win, 2: checkmate, 1: ok, 0: no advantage or lose),
        point to pick(None to any)]
        """
        if line.length > 5 and self.is_black_line(line):
            return Option(OptionType.Trash, 0, None)

        elif line.length >= 5:
            return Option(OptionType.Win, 0, None)

        if line.length == 4:
            ln_f, pf, success_f = self.line_extend_first(line)
            ln_s, ps, success_s = self.line_extend_second(line)
            if self.is_black_line(line):
                if (success_f and ln_f.length == 5) + (success_s and ln_s.length == 5) == 0:
                    return Option(OptionType.Trash, 1, None)
                elif success_f and ln_f.length == 5:
                    if self.check_fault(Move(self.opponent(line.program_number), pf)):
                        return Option(OptionType.Checkmate, 1, pf)
                    return Option(OptionType((success_f and ln_f.length == 5) + (success_s and ln_s.length == 5)),
                                  1, pf)

                if self.check_fault(Move(self.opponent(line.program_number), ps)):
                    return Option(OptionType.Checkmate, 1, ps)
                return Option(OptionType.Preferable, 1, ps)

            if success_f + success_s == 0:
                return Option(OptionType.Trash, 1, None)
            elif success_f:
                if self.check_fault(Move(self.opponent(line.program_number), pf)):
                    return Option(OptionType.Checkmate, 1, pf)
                return Option(OptionType(success_f + success_s), 1, pf)
            if self.check_fault(Move(self.opponent(line.program_number), ps)):
                return Option(OptionType.Checkmate, 1, ps)
            return Option(OptionType.Preferable, 1, ps)

        elif line.length == 3:
            result = 0
            ln_f, pf1, success = self.line_extend_first(line)
            if success:
                res_f = self.can_win_with_line(ln_f)  # already 5
                result += res_f.type is OptionType.Win
            ln_s, ps1, success = self.line_extend_second(line)
            if success:
                res_s = self.can_win_with_line(ln_s)  # already 5
                result += res_s.type is OptionType.Win

            if result == 2:  # can make 5 whatever opponent does
                return Option(OptionType.Checkmate, 1, res_f.point)

            if not ln_f and not ln_s:  # can't extend at all
                return Option(OptionType.Trash, 2, None)

            faults = [0, 0, 0, 0]  # leftside_left, lefttside_right, rightside_left, rightside_right
            if ln_f and ln_f.length == 4:
                ln_f, pf2, success = self.line_extend_first(line)
                if success and ln_f.length == 5:
                    if self.check_fault(Move(self.opponent(line.program_number), pf1)):
                        faults[1] = 1
                    if self.check_fault(Move(self.opponent(line.program_number), pf2)):
                        faults[0] = 1
            if ln_s and ln_s.length == 4:
                ln_s, ps2, success = self.line_extend_second(line)
                if success and ln_s.length == 5:
                    if self.check_fault(Move(self.opponent(line.program_number), ps1)):
                        faults[2] = 1
                    if self.check_fault(Move(self.opponent(line.program_number), ps2)):
                        faults[3] = 1
            if sum(faults) >= 2:
                if sum(faults[:2]) and sum(sum[2:]) != 2:
                    if faults[0]:
                        return Option(OptionType.Checkmate, 2, pf1)
                    return Option(OptionType.Checkmate, 2, pf2)
                if faults[3]:
                    return Option(OptionType.Checkmate, 2, ps1)
                return Option(OptionType.Checkmate, 2, ps2)
            if sum(faults):
                if faults[0]:
                    return Option(OptionType.Preferable, 2, pf1)
                elif faults[1]:
                    return Option(OptionType.Preferable, 2, pf2)
                elif faults[2]:
                    return Option(OptionType.Preferable, 2, ps2)
                return Option(OptionType.Preferable, 2, ps1)

            if pf1:
                return Option(OptionType.OK, 2, pf1)
            elif ps1:
                return Option(OptionType.OK, 2, ps1)

            return Option(OptionType.Trash, 2, pf1)

        elif line.length == 2:
            result = 0
            ln_f, pf1, success = self.line_extend_first(line)
            if success:
                res_f = self.can_win_with_line(ln_f)  # already 5
                result += res_f.type is OptionType.Win
            ln_s, ps1, success = self.line_extend_second(line)
            if success:
                res_s = self.can_win_with_line(ln_s)  # already 5
                result += res_s.type is OptionType.Win

            if result == 2:  # can make 5 whatever opponent does
                return Option(OptionType.Win, 1, res_f.point)

            if not ln_f and not ln_s:  # can't extend at all
                return Option(OptionType.Trash, 3, None)
            if ln_f:
                return Option(OptionType.OK, 3, pf1)
            elif ln_s:
                return Option(OptionType.OK, 3, ps1)
        return Option(OptionType.Trash, 0, None)

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

    def opponent(self, program_number: int) -> int:
        """
        Create or get next opponent's number
        :param program_number: yourself
        :return: int. program number
        """
        numbers = {move.program_number for move in self.moves}
        numbers.add(self.me)
        numbers.remove(program_number)
        return list(numbers)[0]

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

    def line_extend_first(self, line: Line) -> Union[Tuple[Line, Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `first` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """
        line, point, success = line.extend_first()
        if not success or self.check_fault(Move(line.program_number, point)):
            return line, point, success

        while 0 <= point.y - line.direction.value[0] < config.TABLE_SIZE and \
                0 <= point.x - line.direction.value[1] < config.TABLE_SIZE and \
                self.table[point.y - line.direction.value[0]][point.x - line.direction.value[1]] == line.program_number:
            point = Point(point.y - line.direction.value[0], point.x - line.direction.value[1])
        line.first = point

        return line, point, success

    def line_extend_second(self, line: Line) -> Union[Tuple[Line, Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `second` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """
        line, point, success = line.extend_second()
        if not success or self.copy().compute_move(Move(line.program_number, point)):
            return line, point, success

        while 0 <= point.y + line.direction.value[0] < config.TABLE_SIZE and \
                0 <= point.x + line.direction.value[1] < config.TABLE_SIZE and \
                self.table[point.y + line.direction.value[0]][point.x + line.direction.value[1]] == line.program_number:
            point = Point(point.y + line.direction.value[0], point.x + line.direction.value[1])
        line.second = point

        return line, point, success

    def pretty_print(self):
        """
        pretty print the table. 'ー｜・🔴⚪︎'
        """
        nums = ['１', '２', '３', '４', '５', '６', '７', '８', '９', '10', '11', '12', '13', '14', '15']

        lines = ['　　' + '　'.join(nums)]
        for y_ind, y in enumerate(self.table):
            line = [nums[y_ind], '　']
            for x in y:
                if x:
                    if x == self.moves[0].program_number:
                        line.append('🔴')
                    else:
                        line.append('⚪︎︎')
                else:
                    line.append('・')
                line.append('ー')
            line.pop()
            lines.append(''.join(line))
            lines.append('　　' + ('｜　' * config.TABLE_SIZE)[:-1])
        lines.pop()
        print('\n'.join(lines))

    def is_black_line(self, line: Line) -> bool:
        """
        return whether line is made by black
        :param line: Line to judge
        :return: bool
        """
        return not self.moves_count or line.program_number == self.moves[0].program_number


def load_data(filename: str) -> Tuple[int, List[Move]]:
    """
    Load data with given filename
    :param filename: filename of moves
    :return: Tuple[total_moves, List[Move]]
    """
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = f.read()
        count, *data = [list(map(int, d.split(';'))) for d in data.split(',')]
        count = count[0]
    else:
        data = []
        count = 0
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
    choose, max_val = None, OptionWrapper(Option(OptionType.Trash, 0, None))
    for point in move:
        t = table.copy()
        t.compute_move(Move(table.me, point))
        m = Option(OptionType.Trash, 0, None)
        for line in chain.from_iterable(t.get_lines(t.me).values()):
            mm = t.can_win_with_line(line)
            m = m.add(mm)
        if max_val < m:
            print('no', m.options)
            choose = point
            max_val = m
        print(point, m, m.max())
    print(max_val.max())
