#!/usr/bin/env python3
import deck
from board import ReserveSlot, FoundationSlot, TableauSlot
import pygame
from pygame.constants import KEYDOWN, QUIT, RESIZABLE, VIDEORESIZE, MOUSEBUTTONDOWN, MOUSEBUTTONUP
from collections import defaultdict, deque, namedtuple
from functools import reduce
from copy import copy
from itertools import chain, cycle
import operator
from contextlib import suppress


def on_quit(event):
    print('quit')
    raise EOFError('quit signal')  # break the main loop


def on_resize(event):
    # need to delay action otherwise pygame choke
    def process_resize(screensize):
        resize(screensize)
        return True

    delay(action=lambda: resize(event.size), key='resize')


_focus = None


def unfocus():
    global _focus
    if _focus is None:
        return False
    else:
        _focus.toggle(False)
        _focus = None
        return True


def click(position):
    global _focus
    pos, slot = get_slot(position)
    if _focus is None or slot is _focus:
        try:
            _focus = slot if slot.toggle() else None
        except AttributeError:
            return False
        else:
            return True
    else:
        changed = slot.receive_from(_focus, max_cards=(1 + count_empty(tableau)) * (1 + count_empty(reserve)))
        print(changed)
        unfocus()
        if changed:
            save_board_state()
        return True


def count_empty(iterable_slots):
    return sum(map(lambda x: x.is_empty(), iterable_slots))


_peek = []


def peek(position):
    pos, slot = get_slot(position)
    try:
        r = slot.area().move(pos)
        if r.collidepoint(*position):
            x, y, a, b = *position, *pos
            relpos = (x - a, y - b)
            slot.peek_on(relpos)
            _peek.append(slot)
    except AttributeError:
        return False
    else:
        return True


click_handlers = defaultdict(lambda: no_action, {1: click, 3: peek})


def on_click(event):
    try:
        return click_handlers[event.button](event.pos)
    except ValueError:
        return unfocus()


def save_board_state():
    print('saving state to history')
    global history, history_current, history_future
    if history_current:
        history.append(history_current)
    history_current = tuple([slot.save() for slot in panel] for panel in board)
    history_future.clear()


def _history_step(from_stack, to_stack):
    global board, history_current
    try:
        state = from_stack.pop()  # raises IndexError if no history
    except IndexError:
        print('failed history step')
    else:
        to_stack.append(history_current)
        history_current = state
        print('load historical state')
        for panel, saved_panel in zip(board, history_current):
            for slot, saved_slot in zip(panel, saved_panel):
                slot.load(saved_slot)
        return True


def step_forward():
    global history, history_future
    print(f'before -> past ({len(history)}) future ({len(history_future)})')
    resp = _history_step(from_stack=history_future, to_stack=history)
    print(f'after -> past ({len(history)}) future ({len(history_future)})')
    return resp


def step_back():
    global history, history_future
    print(f'before -> past ({len(history)}) future ({len(history_future)})')
    resp = _history_step(from_stack=history, to_stack=history_future)
    print(f'after -> past ({len(history)}) future ({len(history_future)})')
    return resp


key_handlers = defaultdict(lambda: no_action, {'-': step_back, '+': step_forward})


def on_keydown(event):
    print(event)
    return key_handlers[event.unicode]()


def pop_iter(stack):
    try:
        while True:
            yield stack.pop()
    except IndexError:
        raise StopIteration()


def on_click_release(event):
    if event.button == 3:  # turn peek off
        resp = len(_peek) > 0
        for slot in pop_iter(_peek):
            slot.peek_off()
        return resp


def resize(screensize):
    pygame.display.set_mode(screensize, RESIZABLE)
    return deck.set_size(screensize, cols=8, rows=3.5, margin=margin * screensize[0])  # init board


def no_action(*a):
    return False


_differed = {}
_differed_delay = {}


def delay(action, key, delay=5000):
    _differed_delay[key] = delay
    _differed[key] = action


handlers = defaultdict(lambda: no_action, {KEYDOWN: on_keydown,
                                           QUIT: on_quit,
                                           VIDEORESIZE: on_resize,
                                           MOUSEBUTTONDOWN: on_click,
                                           MOUSEBUTTONUP: on_click_release})


def process_events():
    return reduce(operator.or_, (bool(handlers[event.type](event)) for event in pygame.event.get()), False)


def process_differed_events():
    change = False
    for k in list(_differed):
        _differed_delay[k] -= 1
        if _differed_delay[k] <= 0:
            _differed[k]()
            del _differed[k]
            del _differed_delay[k]
            change = True
    return change


reserve = [ReserveSlot() for i in range(4)]
foundation = [FoundationSlot() for i in range(4)]
tableau = [TableauSlot() for i in range(8)]
board = (reserve, foundation, tableau)
margin = 0.01  # % screen_width
slotmap = {}  # position -> slot  where position is in percent card_size

history = deque()
history_current = None
history_future = deque()


def get_slot(position):
    """
    Return tuple(slot_origin, slot) for the first slot that collide with position
    Raises ValueError if no slot collide
    """
    x, y = position
    w, h = deck.card_size
    x, y = x / w, y / h  # convert to percent card_size

    def dist_from(origin):
        a, b = origin
        return abs(x - a) + abs(y - b)

    def topleft_quadrant(origin):
        a, b = origin
        return a <= x and b <= y

    try:
        percent_position = sorted(filter(topleft_quadrant, slotmap), key=dist_from)[0]
    except IndexError:
        raise ValueError('No slot collides')
    else:
        ax, ay = percent_position
        pos, slot = (ax * w, ay * h), slotmap[percent_position]
        if slot.area().move(*pos).collidepoint(*position):
            return pos, slot
        else:
            raise ValueError('No slot collides')


def push_to_foundation():
    r = reduce(operator.or_, (bool(fnd.receive_from(tab, max_cards=1)) for tab in tableau for fnd in foundation), False)
    print(f'foundation push={r} score={score()}')


def score():
    return sum(map(len, foundation))


def win_condition():
    return score() == len(deck.deck)


def refresh_display():
    screen = pygame.display.get_surface()
    screen.fill(deck.Colors.green)
    w, h = deck.card_size
    for relativePosition, slot in slotmap.items():
        i, j = relativePosition  # relative %
        position = int(i * w), int(j * h)  # absolute pixels
        screen.blit(slot.render(), position, slot.area())
    pygame.display.flip()


def init():
    pygame.init()
    screensize = (640, 480)
    w, h = resize(screensize)
    # filter events
    pygame.event.set_allowed(list(handlers))
    # init deck
    m = margin * screensize[0] / w  # % card_width
    for k, slot in enumerate(chain(*board)):
        relativePosition = (m + (1 + m) * (k % 8), m + (1 + m) * (k // 8))
        slotmap[relativePosition] = slot
    # deal cards
    deck.shuffle()
    for card, slot in zip(deck.deck, cycle(tableau)):
        slot.stack.append(card)
    # init history+
    save_board_state()
    refresh_display()


def main():
    init()
    try:
        while not win_condition():
            pygame.event.pump()
            if process_events() or process_differed_events():
                push_to_foundation()
                refresh_display()
        else:
            print('Congrats !')
    except EOFError:  # Quit
        pass
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
