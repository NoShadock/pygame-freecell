#!/usr/bin/env python3
import deck
import pygame
from pygame.constants import KEYDOWN, QUIT, RESIZABLE, VIDEORESIZE
from collections import defaultdict, deque, namedtuple
from functools import reduce
import operator
import time


def on_keydown(event):
    print(event)
    return False


def on_quit(event):
    print('quit')
    raise EOFError('quit signal')


def on_resize(event):
    print('resize ', event.size, pygame.display.get_surface().get_rect())
    # need to delay action otherwise pygame choke
    k = 'resize'
    # if k not in differed:
    differed[k] = DifferedAction(delay=5000, action=lambda: resize(event.size))
    return False


def resize(size):
    print('resizing: ', size)
    pygame.display.set_mode(size, RESIZABLE)
    deck.resize(size)


def no_action(*a):
    return False


handlers = defaultdict(lambda: no_action, {KEYDOWN: on_keydown, QUIT: on_quit, VIDEORESIZE: on_resize})
DifferedAction = namedtuple('DifferedAction', ['delay', 'action'])
differed = {}


def process_events():
    return reduce(operator.or_, (handlers[event.type](event) for event in pygame.event.get(pump=True)), False)


def main():
    pygame.init()
    screen = pygame.display.set_mode((640, 480), RESIZABLE)
    deck.show_deck(screen)
    try:
        while True:
            change = False
            if process_events():
                change = True
            for k in list(differed):
                differed[k] = DifferedAction(delay=differed[k].delay - 1, action=differed[k].action)
                if differed[k].delay <= 0:
                    differed[k].action()
                    del differed[k]
                    change = True
            if change:
                deck.show_deck(pygame.display.get_surface())
    except EOFError:
        pass
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
