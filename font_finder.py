import pygame
import pygame.freetype
from pygame.constants import KEYDOWN, QUIT, RESIZABLE
from deck import Colors
from functools import partial
from itertools import chain
import os

main_dir = os.path.dirname(os.path.abspath(__file__))
fonts_dir = os.path.join(main_dir, 'data', 'fonts')

symbols = '{} ♠♥♣♦♞♛♚'  # unicode U+2660, 2663, 2665, 2666, 265A, 265B, 265E

selection = ['dejavusans',
             'dejavusansmono',
             'freeserif',
             'symbola',
             'wenquanyimicrohei',
             'wenquanyimicroheimono', ]


def render(font_name):
    try:
        fn, fp = font_name
    except ValueError:
        font = pygame.freetype.SysFont(font_name, 16)
        fn = font_name
    else:
        font = pygame.freetype.Font(fp, 16)
    return font.render(symbols.format(fn), fgcolor=Colors.white)


def print_screen(screen, screensize, flist):
    m = 5
    curw = px = py = 0
    for font in flist:
        try:
            surf, (_, _, w, h) = render(font)
        except OSError:
            continue
        py += m
        curw = max(curw, w)
        if py + h > screensize[1]:  # new column
            py = m
            px += curw + m
            curw = 0
        if px + w > screensize[0]:  # new screen
            px = py = m
            curw = w
            yield True
        screen.blit(surf, (px, py))
        pygame.display.update()
        py += h
    yield True


def main():
    try:
        pygame.freetype.init()
        screensize = (800, 600)
        screen = pygame.display.set_mode(screensize, RESIZABLE)
        screen.fill(Colors.black)
        try:
            custom = ((n, os.path.join(fonts_dir, n)) for n in os.listdir(fonts_dir))
        except OSError:
            custom = []
        flist = list(chain(custom, sorted(pygame.freetype.get_fonts()),))
        # print(flist)
        print_s = partial(print_screen, screen, screensize)
        while True:
            for wait in chain(print_s(selection), print_s(flist)):
                while wait:
                    for event in pygame.event.get():
                        if event.type == QUIT:
                            return
                        if event.type == KEYDOWN:
                            screen.fill(Colors.black)
                            wait = False
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
