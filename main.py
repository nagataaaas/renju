import os
import random
import sys
import warnings
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from itertools import chain
from typing import List, Union, Dict, Tuple

import config


class OptionType(Enum):
    Win = 5  # already won
    Checkmate = 4  # opponent can't prevent loosing
    ToCheckmate = 3  # opponent needs to stop "NOW" or loose
    Winnable = 2  # opponent needs to stop or loose
    Preferable = 1  # closer to win
    Trash = 0  # trash

    @property
    def priority(self) -> int:
        return self.value


@dataclass
class Option:
    """
    Available option
    :param type: type of option
    :param win_to: how many moves needed to win `actually`
    :param point: point to place
    """
    type: OptionType
    win_to: int
    point: Union['Point', None]

    def add(self, option: 'Option') -> 'OptionContainer':
        """
        create OptionContainer with another option
        :param option: Option to create OptionContainer with
        :return: OptionContainer
        """
        ow = OptionContainer(self)
        ow.add(option)
        return ow


class OptionContainer:
    def __init__(self, *options: Option):
        """
        Container of all options
        :param options: options initialize with
        """
        self.options = list(options)

    def add(self, option: Union[Option, 'OptionContainer']) -> 'OptionContainer':
        """
        extend options with other `Option` or `OptionContainer`
        :param option: Union[Option, 'OptionContainer'].
        :return: extended OptionContainer
        """
        new = OptionContainer()
        if isinstance(option, Option):
            new.options = self.options[:]
            new.options.append(option)
            return new
        new.options = self.options[:] + option.options
        return new

    @property
    def max(self) -> Option:
        """
        return the best option in OptionContainer.
        :return: Option
        """
        if not self.options:
            return Option(OptionType.Trash, 0, None)

        checkmates = []
        to_checkmates = []
        winnables = []
        preferables = []
        trashes = []

        for v in self.options:
            if v.type == OptionType.Win:
                return v

            if v.type == OptionType.Checkmate:
                checkmates.append(v)
            elif v.type == OptionType.ToCheckmate:
                to_checkmates.append(v)
            elif v.type == OptionType.Winnable:
                winnables.append(v)
            elif v.type == OptionType.Preferable:
                preferables.append(v)
            else:
                trashes.append(v)
        if checkmates:
            checkmates.sort(key=lambda x: x.win_to)
            return checkmates[0]
        if to_checkmates:
            to_checkmates.sort(key=lambda x: x.win_to)
            return to_checkmates[0]
        if winnables:
            winnables.sort(key=lambda x: x.win_to)
            return winnables[0]
        if preferables:
            preferables.sort(key=lambda x: x.win_to)
            return preferables[0]
        trashes.sort(key=lambda x: x.win_to)
        return trashes[0]

    @property
    def winnable_with_skip(self) -> bool:
        """
        return if winnable with enemy's turn.
        :return: bool. winnable or not
        """
        if any(option.type is OptionType.Win or option.type is OptionType.Checkmate for option in self.options):
            # already won or 100% winnable
            return True

        if len(set(option.point for option in self.options
                   if option.type is OptionType.ToCheckmate)) >= 2:
            # opponent doesn't have enough turns to deals with it.
            return True

        return False

    @property
    def score(self) -> int:
        """
        score the Options.
        :return: score
        """

        # each score needs to be more adjusted.
        # to make more strong CPU
        result = 0
        if self.winnable_with_skip:
            result += 9999999
        for option in self.options:
            if option.type == OptionType.Win:
                result += 99999
            elif option.type == OptionType.Checkmate:
                result += 99999
            elif option.type == OptionType.ToCheckmate:
                result += 9999
            elif option.type == OptionType.Winnable:
                result += 50
            elif option.type == OptionType.Preferable:
                if option.win_to == 1:
                    result += 10
                result += 3
        return result

    def __lt__(self, other: 'OptionContainer'):
        me, op = self.score, other.score
        if me - op:
            return me < op
        return random.choice((True, False))

    def __repr__(self):
        return 'OptionContainer(options={!r})'.format(self.options)


@dataclass(frozen=True)
class Point:
    """
    :param y: y-coordinate
    :param x: x-coordinate
    """
    y: int
    x: int

    def __lt__(self, other):
        # just to create prevent errors on comparison
        return False


class Direction(Enum):
    Horizontal = (0, 1)  # →
    Vertical = (1, 0)  # ↓
    Diagonal_UL_BR = (1, 1)  # ↘
    Diagonal_UR_BL = (1, -1)  # ↙


@dataclass
class Line:
    """
    Line of Go-Ishi
    :param direction: Direction of Line
    :param first: first point of line
    :param second: second point of line
    :param program_number: program number which made this line
    """
    direction: Direction
    first: Point
    second: Point
    program_number: int

    def __post_init__(self):

        dy = self.second.y - self.first.y
        dx = self.second.x - self.first.x
        if (dy and not self.direction.value[0]) or (dx and not self.direction.value[1]) or \
                (self.direction.value[0] and self.direction.value[1] and
                 dy / self.direction.value[0] != dx / self.direction.value[1]):
            raise ValueError('Looks like direction `{}` is not suitable for points [{}, {}]'.format(self.direction,
                                                                                                    self.first,
                                                                                                    self.second))

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
        """
        return length of line
        :return: int. length
        """
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
    moves: List[Move]
    table: Dict[Point, Union[None, int]]  # point to program_number. if not set, return None

    def __init__(self, moves: List[Move]):
        """
        Table of Renju
        :param moves: All moves

        :var
        """
        self.moves_count = len(moves)
        self.moves = moves

        self.table: Dict[Point, Union[None, int]] = defaultdict(lambda: None)

    def compute(self) -> Union[Tuple[None, None], Tuple[Move, bool]]:
        """
        Compute all moves and update table. If there is any foul move or win move, return it
        :return: [Move, is_win] if foul move or Win move is there. Otherwise, [None, None]
        """
        prev = None
        for move in self.moves:
            if move.program_number == prev:
                if config.RAISE_ON_CSV_COUNT_ERROR:
                    return move, False
                warnings.warn('It seems like player is not playing alternately')
            prev = move.program_number
            if self.check_foul(move):
                return move, False
            self.table[move.point] = move.program_number

            if self.is_win(move.program_number):
                return move, True

        return None, None

    def is_win(self, program_number: int) -> bool:
        """
        return whether program_number is already won
        :param program_number: program_number check to
        :return: bool
        """
        is_black = self.is_black(program_number)

        lines = self.get_lines(program_number)

        if is_black:
            return max(lines.keys()) == 5
        return max(lines.keys()) >= 5

    def compute_move(self, move: Move) -> bool:
        """
        Compute single move and return whether move is foul.
        :param move: Move to compute
        :return: Whether foul of not.
        """
        if self.check_foul(move):
            return True
        self.table[move.point] = move.program_number
        self.moves.append(move)
        self.moves_count += 1
        return False

    def check_foul(self, move: Move) -> bool:
        """
        Check if the move is foul
        :param move: Move to be judged
        :return: boolean
        """
        program_number = move.program_number
        if move.point in self.table:
            # already placed
            return True

        is_black = self.is_black(move.program_number)

        if not is_black:
            # white has no foul moves
            return False

        new = [0, 0, 0, 0, 0, 0, 0, 0]
        for direction in Direction:
            line = Line(direction, move.point, move.point, program_number)
            l, p, s = line.extend_first()
            if s and p in self.table and self.table[p] == program_number:  # extendable and already placed there
                l, p, s = self.line_extend_first(line, False)  # then connect with it
                if s:
                    line = l
            l, p, s = line.extend_second()
            if s and p in self.table and self.table[p] == program_number:
                l, p, s = self.line_extend_second(line, False)
                if s:
                    line = l
            new[line.length - 1] += 1

        if new[4]:  # 5 length line is win
            return False
        if any(new[5:]):  # cho-ren
            return True
        return new[3] >= 2 or new[2] >= 2  # san-san or shi-shi

    def get_lines(self, program_number: int) -> Dict[int, List[Line]]:
        """
        return all lines with its length
        :param program_number: Compute as
        :return: Dict in format of {length: count}
        """
        placed_points = set(point for point, pn in self.table.items() if pn == program_number)

        result = defaultdict(list)
        result[0] = []
        # prevent errors on func like max(result.keys())

        for direction in Direction:  # for each direction
            points_copy = placed_points.copy()

            while points_copy:  # if any point is not used
                first = second = points_copy.pop()  # create 1 length line
                while True:
                    next_first = Point(first.y - direction.value[0], first.x - direction.value[1])
                    if next_first not in points_copy:
                        break

                    # extend if line is extendable
                    points_copy.remove(next_first)
                    first = next_first
                while True:
                    next_second = Point(second.y + direction.value[0], second.x + direction.value[1])
                    if next_second not in points_copy:
                        break

                    points_copy.remove(next_second)
                    second = next_second
                line = Line(direction, first, second, program_number)
                result[line.length].append(line)

        return result

    def choose_next_move(self, program_number: int, depth=1, best=5) -> Tuple[Move, OptionContainer]:
        """
        calculate the best move and return OptionContainer for the recursive calc.
        :param program_number: Compute as
        :param depth: how many times to calculate recursively
        :param best: for each recurrence, how many of the best should be computed
        :return: Tuple[Move, Union[OptionContainer, None]]
        """
        if self.moves_count == 0:
            # place to center
            return Move(program_number, Point(7, 7)), OptionContainer()

        if self.moves_count == 1:
            if Point(7, 7) not in self.table is None:
                # if black haven't placed to center
                return Move(program_number, Point(7, 7)), OptionContainer()

            for i in range(9):
                # any around
                y, x = 7 + (i % 3 - 1), 7 + (i // 3 - 1)
                if y in range(0, config.TABLE_SIZE) and x in range(0, config.TABLE_SIZE) and i != 4:
                    return Move(program_number, Point(y, x)), OptionContainer()
        if self.moves_count == 2:
            for i in range(9):
                # any around of 2 block distant
                y, x = 7 + (i % 3 - 1) * 2, 7 + (i // 3 - 1) * 2
                if y in range(0, config.TABLE_SIZE) and x in range(0, config.TABLE_SIZE) and i != 4:
                    return Move(program_number, Point(y, x)), OptionContainer()

        opponent = self.opponent(program_number)

        scores: List[List[List[OptionContainer, Point]], List[List[OptionContainer, Point]]] = [[], []]

        for pn, es in [(program_number, scores[0]), (opponent, scores[1])]:
            available_points = self.available_extended_points(pn, 2)
            for point in available_points:
                # for each point available, calc score of condition when program_number placed there
                table = self.copy()
                table.compute_move(Move(pn, point))
                oc = OptionContainer()
                for line in chain.from_iterable(table.get_lines(pn).values()):
                    _oc = table.find_options(line)
                    if _oc.max.type == OptionType.Win:
                        # if winnable as myself, use this move
                        #   OR
                        # if there is a point which if enemy place there and they will win,
                        # place there if it's not foul
                        if pn == program_number or not self.check_foul(Move(program_number, point)):
                            return Move(program_number, point), OptionContainer()
                    oc = oc.add(_oc)
                oc.options.sort(key=lambda v: v.type.priority)
                es.append([oc, point])
            es.sort(reverse=True)

        win_to, points = [999, 999], [None, None]
        for i in range(2):
            if any(ev[0].winnable_with_skip for ev in scores[i]):
                # if there are any options enemy winnable
                for ev, _point in scores[i]:
                    if ev.winnable_with_skip:
                        _win_to = min(op.win_to for op in ev.options if op.type in (OptionType.Win,
                                                                                    OptionType.Checkmate,
                                                                                    OptionType.ToCheckmate))
                        if _win_to < win_to[i]:
                            win_to[i] = _win_to
                            points[i] = _point

        if win_to[1] != 999:
            if win_to[1] < win_to[0]:  # enemy will win first
                return Move(program_number, points[1]), OptionContainer()
            # player can win earlier
            return Move(program_number, points[0]), OptionContainer()
        if win_to[0] != 999:
            # can will
            return Move(program_number, points[0]), OptionContainer()

        if depth <= 1:
            ow, point = scores[0][0]
            return Move(program_number, point), ow

        diff = []
        for ow, point in scores[0][:best]:
            table = self.copy()
            table.compute_move(Move(program_number, point))
            # for each point, compute opponents move recursively and take the best one
            enemy_move, enemy_choice = self.choose_next_move(self.opponent(program_number), depth - 1, best)
            diff.append([enemy_choice.score - ow.score, ow, enemy_choice, enemy_move, point])

        diff.sort()
        return Move(program_number, diff[0][4]), diff[0][1] or OptionContainer()

    def find_options(self, line: Line) -> OptionContainer:
        """
        return preferable option and current condition
        :param line: line to be computed
        :return: OptionContainer
        """
        is_black = self.is_black(line.program_number)
        if line.length > 5 and is_black:
            # for black, more than 5-length line is a total trash
            return OptionContainer(Option(OptionType.Trash, 999, None))

        elif line.length >= 5:
            # win
            return OptionContainer(Option(OptionType.Win, 0, None))

        if line.length == 4:
            ln_f, pf, success_f = self.line_extend_first(line)
            ln_s, ps, success_s = self.line_extend_second(line)
            if success_f + success_s == 0:
                # not extendable. trash
                return OptionContainer(Option(OptionType.Trash, 999, None))

            if is_black:
                # can't create 5-length. trash for black
                if (success_f and ln_f.length == 5) + (success_s and ln_s.length == 5) == 0:
                    return OptionContainer(Option(OptionType.Trash, 999, None))

            options = []
            if success_f and (not is_black or ln_f.length == 5):
                if self.check_foul(Move(self.opponent(line.program_number), pf)):
                    # if enemy can't stop this
                    options.append(Option(OptionType.Checkmate, 1, pf))
                else:
                    options.append(Option(OptionType.ToCheckmate, 1, pf))
            if success_s and (not is_black or ln_s.length == 5):
                if self.check_foul(Move(self.opponent(line.program_number), ps)):
                    options.append(Option(OptionType.Checkmate, 1, ps))
                else:
                    options.append(Option(OptionType.ToCheckmate, 1, ps))
            if len(options) == 2:
                # both sides are critical for opponent. Tasshi
                return OptionContainer(Option(OptionType.Checkmate, 1, pf), Option(OptionType.Checkmate, 1, ps))
            return OptionContainer(*options)

        elif line.length == 3:
            options = []

            result = 0
            ln_f, pf1, success_f = self.line_extend_first(line)
            ln_s, ps1, success_s = self.line_extend_second(line)
            for ln, p, success in [[ln_f, pf1, success_f], [ln_s, ps1, success_s]]:
                if success and not self.check_foul(Move(line.program_number, p)):
                    if ln.length > 5 and is_black:
                        pass
                    elif ln.length >= 5:
                        result += 1
                        # can create 5
                        if self.check_foul(Move(self.opponent(line.program_number), p)):
                            return OptionContainer(Option(OptionType.Checkmate, 1, p))
                        options.append(Option(OptionType.ToCheckmate, 1, p))
                    else:
                        next = self.find_options(ln).max
                        if next.type is OptionType.Checkmate:
                            options.append(Option(OptionType.ToCheckmate, 2, p))
                        elif next.type is OptionType.ToCheckmate:
                            options.append(Option(OptionType.Winnable, 2, p))

            if result == 2:  # can make 5 whatever opponent does
                return OptionContainer(Option(OptionType.Checkmate, 1, pf1),
                                       Option(OptionType.Checkmate, 1, ps1))
            if len(options) == 2:
                return OptionContainer(Option(OptionType.ToCheckmate, 2, pf1),
                                       Option(OptionType.ToCheckmate, 2, ps1))

            if not ln_f and not ln_s:  # can't extend at all
                return OptionContainer(Option(OptionType.Trash, 999, None))

            # find a place within two distance to the left or right that opponent cannot select.
            fouls = [0, 0, 0, 0]  # left_side_left, left_side_right, right_side_left, right_side_right
            if ln_f and ln_f.length == 4:
                ln_f, pf2, success = self.line_extend_first(ln_f)
                if success and ln_f.length == 5:
                    if self.check_foul(Move(self.opponent(line.program_number), pf1)):
                        fouls[1] = 1
                    if self.check_foul(Move(self.opponent(line.program_number), pf2)):
                        fouls[0] = 1
            if ln_s and ln_s.length == 4:
                ln_s, ps2, success = self.line_extend_second(ln_s)
                if success and ln_s.length == 5:
                    if self.check_foul(Move(self.opponent(line.program_number), ps1)):
                        fouls[2] = 1
                    if self.check_foul(Move(self.opponent(line.program_number), ps2)):
                        fouls[3] = 1

            if sum(fouls) >= 2:  # there are more than 2 places opponent can't select
                if sum(fouls[:2]) == 2:  # both of left half
                    return OptionContainer(Option(OptionType.ToCheckmate, 2, pf1),
                                           Option(OptionType.ToCheckmate, 2, pf2),
                                           *options)
                elif sum(fouls[2:]) == 2:  # right half
                    return OptionContainer(Option(OptionType.ToCheckmate, 2, ps1),
                                           Option(OptionType.ToCheckmate, 1, ps2),
                                           *options)
                # one for each side
                if fouls[0]:
                    options.append(Option(OptionType.ToCheckmate, 2, pf1))
                else:
                    options.append(Option(OptionType.ToCheckmate, 2, pf2))
                if fouls[3]:
                    options.append(Option(OptionType.ToCheckmate, 2, ps2))
                else:
                    options.append(Option(OptionType.ToCheckmate, 2, ps1))
                return OptionContainer(*options)

            if fouls[0]:
                return OptionContainer(Option(OptionType.ToCheckmate, 2, pf1))
            elif fouls[1]:
                return OptionContainer(Option(OptionType.ToCheckmate, 2, pf2))
            elif fouls[2]:
                return OptionContainer(Option(OptionType.ToCheckmate, 2, ps2))
            elif fouls[3]:
                return OptionContainer(Option(OptionType.ToCheckmate, 2, ps1))

            if pf1:
                options.append(Option(OptionType.Preferable, 2, pf1))
            if ps1:
                options.append(Option(OptionType.Preferable, 2, ps1))
            if options:
                return OptionContainer(*options)

            return OptionContainer(Option(OptionType.Trash, 2, pf1))

        elif line.length == 2:
            options = []

            result = 0
            ln_f, pf1, success_f = self.line_extend_first(line)
            ln_s, ps1, success_s = self.line_extend_second(line)
            for ln, p, success in [[ln_f, pf1, success_f], [ln_s, ps1, success_s]]:
                if success and not self.check_foul(Move(line.program_number, p)):
                    if ln.length > 5 and is_black:
                        pass
                    if ln.length >= 5:
                        result += 1
                        # can create 5
                        options.append(Option(OptionType.ToCheckmate, 1, p))
                    else:
                        next = self.find_options(ln).max
                        if next.type is OptionType.Checkmate:
                            options.append(Option(OptionType.ToCheckmate, next.win_to + 1, p))
                        elif next.type is OptionType.ToCheckmate:
                            options.append(Option(OptionType.Winnable, next.win_to + 1, p))

            if result == 2:  # can make 5 whatever opponent does
                return OptionContainer(Option(OptionType.Checkmate, 1, pf1),
                                       Option(OptionType.Checkmate, 1, ps1))

            if not ln_f and not ln_s:  # can't extend at all
                return OptionContainer(Option(OptionType.Trash, 3, None))

            if ln_f:
                options.append(Option(OptionType.Preferable, 3, pf1))
            elif ln_s:
                options.append(Option(OptionType.Preferable, 3, ps1))
            if options:
                return OptionContainer(*options)

        return OptionContainer(Option(OptionType.Trash, 0, None))

    def available_extended_points(self, program_number: int, distance: int) -> List[Point]:
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

            extends = 0
            while True:
                if extends == distance:
                    break
                line, point, extendable = self.line_extend_first(line)
                if not extendable:
                    break
                options.add(point)
                extends += 1

            line = initial
            extends = 0
            while True:
                if extends == distance:
                    break
                line, point, extendable = self.line_extend_second(line)
                if not extendable:
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
        new = Table(self.moves[:])
        new.table = self.table.copy()
        return new

    def line_extend_first(self, line: Line, foul_check=True) -> \
            Union[Tuple[Line, Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `first` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """
        line, point, success = line.extend_first()
        if not success or (foul_check and self.check_foul(Move(line.program_number, point))):
            return None, None, False

        _point = point
        while True:
            ny = point.y - line.direction.value[0]
            nx = point.x - line.direction.value[1]
            if not (0 <= nx < config.TABLE_SIZE and
                    0 <= ny < config.TABLE_SIZE and
                    Point(ny, nx) in self.table and
                    self.table[Point(ny, nx)] == line.program_number):
                break
            point = Point(ny, nx)
        line.first = point

        return line, _point, success

    def line_extend_second(self, line: Line, foul_check=True) -> \
            Union[Tuple[Line, Point, bool], Tuple[None, None, bool]]:
        """
        return line extended in the `second` point direction.
        :return: [extended_Line, extended_point, whether extended successful]
        """
        line, point, success = line.extend_second()
        if not success or (foul_check and self.check_foul(Move(line.program_number, point))):
            return None, None, False

        _point = point
        while True:
            ny = point.y + line.direction.value[0]
            nx = point.x + line.direction.value[1]
            if not (0 <= nx < config.TABLE_SIZE and
                    0 <= ny < config.TABLE_SIZE and
                    Point(ny, nx) in self.table and
                    self.table[Point(ny, nx)] == line.program_number):
                break
            point = Point(ny, nx)
        line.second = point

        return line, _point, success

    def pretty_print(self):
        """
        pretty print the table. '―｜■○'
        """
        black = self.moves and self.moves[0].program_number
        nums = list('①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮')

        lines = ['　　' + '　'.join(nums)]
        for y in range(config.TABLE_SIZE):
            line = [nums[y], '　']
            for x in range(config.TABLE_SIZE):
                if Point(y, x) in self.table:
                    if self.table[Point(y, x)] == black:
                        line.append('■')
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

    def is_black(self, program_number: int) -> bool:
        """
        return whether player of program_number is black
        :param program_number: player number
        :return: bool
        """
        return not self.moves_count or program_number == self.moves[0].program_number


def load_data(filename: str) -> Tuple[int, List[Move]]:
    """
    Load data with given filename
    :param filename: filename of moves
    :return: Tuple[total_moves, List[Move]]
    """
    data = []
    count = 0
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = f.read()
        if data:
            count, *data = [list(map(int, d.split(';'))) for d in data.split(',')]
            count = count[0]
    moves = [Move(program_number, Point(y - config.TABLE_STARTS_WITH_ONE, x - config.TABLE_STARTS_WITH_ONE)) for
             program_number, y, x in data]

    if count != len(moves):
        if config.RAISE_ON_CSV_COUNT_ERROR:
            raise ValueError('total count is incorrect. (given: {}, moves_length: {})'.format(count, len(moves)))
        warnings.warn('total count is incorrect. (given: {}, moves_length: {})'.format(count, len(moves)))

    return count, moves


def write_data(filename: str, table: Table):
    """
    Write moves with given filename
    :param filename: filename to write
    :param table: table to write
    """
    with open(filename, 'w') as f:
        f.write('{},{}'.format(str(table.moves_count), ','.join(
            [';'.join(map(str, [move.program_number, move.point.y + config.TABLE_STARTS_WITH_ONE,
                                move.point.x + config.TABLE_STARTS_WITH_ONE])) for move in table.moves])))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        warnings.warn('no filename given. defaults to `data.txt`')
        filename = 'data.txt'

    count, data = load_data(filename)

    table = Table(data)
    move, is_win = table.compute()
    print('current table:\n')
    table.pretty_print()
    if move:
        if is_win:
            print('Player number {} won by placing, {}'.format(move.program_number, move.point))
            exit()
        else:
            raise ValueError("Player number {} can't place here, {}".format(move.program_number, move.point))

    print('\n' * 2)
    move, op = table.choose_next_move(table.me, depth=3, best=3)
    print('chose move:', move)
    foul = table.compute_move(move)
    if foul:
        print('foul', move)
    table.pretty_print()
    if table.is_win(move.program_number):
        print('win', move)

    # ##### Code to play against itself
    # while True:
    #     me = table.me
    #     if me == 1:
    #         move, op = table.choose_next_move(table.me, depth=3, best=3)
    #     else:
    #         move, op = table.choose_next_move(table.me, depth=2, best=3)
    #     foul = table.compute_move(move)
    #     print(me, move)
    #     if foul:
    #         print('foul', move)
    #     table.pretty_print()
    #     if table.is_win(move.program_number):
    #         print('win', move)
    #         break
    #     print('\n' * 5)

    write_data(filename, table)
