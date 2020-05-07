#!/usr/bin/env python3
import deck
import pygame
from pygame.constants import KEYDOWN, QUIT
from collections import defaultdict
import operators

screen = None


def on_keydown(event):
    return False


def on_quit(event):
    raise StopIteration('quit signal')


def no_action(*a):
    return False


handlers = defaultdict(lambda: no_action, {KEYDOWN: on_keydown, QUIT: on_quit})


def process_events():
    return reduce(operators.or_, handlers[event.type](event) for event in pygame.event.get(pump=True))


def main():
    pygame.init()
    global screen
    screen = pygame.display.set_mode((640, 480))
    try:
        deck.show_deck(screen)
        while True:
            if process_events():
                deck.show_deck(screen)
    except StopIteration:
        pass
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
