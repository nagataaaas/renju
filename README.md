# Renju Player

```python
from main import Table, Move, Point, write_data
table = Table(1, [Move(1, Point(7, 7))])
move, is_win = table.compute()  # to check moves are valid, and for initialize
print('current table:\n')
table.pretty_print()
if move:  # win or fault
    if is_win:
        print('Player number {} won by placing, {}'.format(move.program_number, move.point))
        exit()
    else:
        raise ValueError("Player number {} can't place here, {}".format(move.program_number, move.point))

print('\n'*2)
move, op = table.choose_next_move(table.me, depth=3, best=3)
print('chose move:', move)
foul = table.compute_move(move)
if foul:
    print('foul', move)
table.pretty_print()
if table.is_win(move.program_number):
    print('win', move)

write_data('data.txt', table.moves)
```

# for GUI play

`$ python gui.py`