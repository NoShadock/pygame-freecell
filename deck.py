#!/usr/bin/env python3
import pygame
import pygame.freetype
from pygame.constants import RESIZABLE, KEYDOWN, QUIT
from collections import namedtuple
from functools import partial, singledispatch
from itertools import chain, cycle
from time import sleep

pygame.init()

card_ratio = 8 / 5
card_size = (75, 120)
font = None
font_selection = [
    'dejavusansmono',
    'freeserif',
    'dejavusans',
    'wenquanyimicroheimono', 'wenquanyimicrohei',
    'symbola',
]

Color = namedtuple('Color', ['r', 'g', 'b'])


class Colors(object):  # hex code comments for my color highlighter
    red = Color(r=255, g=0, b=0)  # 0xFF0000
    green = Color(r=0, g=79, b=15)  # 0x004D0F
    light_green = Color(r=0, g=79, b=15)  # 0x578132
    black = Color(r=0, g=0, b=0)  # 0x000000
    white = Color(r=255, g=255, b=255)  # 0xFFFFFF
    blue = Color(r=0, g=0, b=255)  # 0x0000FF
    gold = pygame.color.THECOLORS['goldenrod']


Suit = namedtuple('Suit', ['index', 'name', 'color', 'symbol', 'alt_symbol'])


class Suits(object):
    symbols = list('♠♥♣♦♤♡♧♢')  # unicodes U+2660,2663,2665,2666,2664,2661,2662,2667
    names = ['spade', 'heart', 'clover', 'diamond']

    def _suit(symbols, names, suit_index):
        return Suit(index=suit_index,
                    name=names[suit_index],
                    color=Colors.black if suit_index % 2 == 0 else Colors.red,
                    symbol=symbols[suit_index],
                    alt_symbol=symbols[4 + suit_index])
    suits = list(map(partial(_suit, symbols, names), range(4)))
    spade, heart, clover, diamond = suits


class FrenchCard(object):
    court = {1: 'A', 11: 'J', 12: 'Q', 13: 'K'}

    def __init__(self, number=1, suit=Suits.spade, **kwargs):
        super().__init__(**kwargs)
        self.number = number
        self.suit = suit

    @ property
    def value(self):
        try:
            return self.court[self.number]
        except KeyError:
            return str(self.number)

    def is_court(self):
        return self.number in self.court

    def __str__(self):
        return self.value + self.car.suit.symbol


class CardSurface(FrenchCard):
    """
    Abstract class for card object meant to be displayed
    abstract method: render()
    """

    def __init__(self, number=0, suit=None, size=None, **kwargs):
        super().__init__(number=number, suit=suit, **kwargs)
        if size is None:
            self.size = card_size

    @property
    def surface(self):
        try:
            return self._surface
        except AttributeError:
            self._surface = pygame.Surface(self.size)
            self.render_surface()
            return self._surface

    def render(self):
        return self.surface

    def render_surface(self):
        raise NotImplementedError('CardSurface is an abstract class')

    def clear(self):
        try:
            del self._surface
        except AttributeError:
            pass

    def resize(self, new_size):
        self.size = new_size
        self.clear()


court_pic = {11: '♗', 12: '♕', 13: '♔'}
# court_pic = {11: '♞', 12: '♛', 13: '♚'}  # unicode U+265A, 265B, 265E
# ches unicodes: ♔♕♖♗♘♙♚♛♜♝♞♟  U+265A ...


def court_image(card):
    """
    Customize court cards design by overriding this function.
    Return char or pygame.Surface
    """
    return court_pic[card.number]


class Card(CardSurface):
    """
    CardSurface rendered procedurally from unicode symbols.
    """

    def __init__(self, *args, **kwargs):
        global font
        if font is None:
            font = pygame.freetype.SysFont(','.join(font_selection), 80)
        super().__init__(*args, **kwargs)

    def render_surface(self):
        # TODO clean up by using pygame.Rect utility
        # TODO fix resize bug
        self.surface.fill(Colors.white)
        card_rect = self.surface.get_rect()
        _, _, card_w, card_h = card_rect
        # border
        pygame.draw.rect(self.surface, Colors.black, card_rect, 1)
        # corners
        midh = card_h // 2 + 1
        corner = (card_w // 6, card_h // 6)
        margin = card_w // 30
        x_pos = (margin, card_w - corner[0] - margin)
        y_pos_val = (margin, card_h - margin - corner[1])
        y_pos_sym = (corner[1], card_h - 2 * corner[1])  # no margin for compact style
        corner_val_size = (corner[0] // len(self.value), corner[1])
        corner_sym_size = (corner[0], corner[0])
        for x in x_pos:
            for y in y_pos_val:  # corner values
                srf, _ = font.render(self.value, size=corner_val_size,
                                     rotation=180 if y > midh else 0, fgcolor=self.suit.color)
                self.surface.blit(srf, srf.get_rect(center=pygame.Rect(x, y, *corner).center))
            for y in y_pos_sym:  # corner symbol
                srf, _ = font.render(self.suit.symbol, size=corner_sym_size,
                                     rotation=180 if y > midh else 0, fgcolor=self.suit.color)
                self.surface.blit(srf, srf.get_rect(center=pygame.Rect(x, y, *corner_sym_size).center))
        # center symbols
        c_x, c_y = corner[0], corner[1] // 2
        c_w, c_h = card_w - 2 * c_x, card_h - 2 * c_y
        sym_size = c_h // 4
        pic_size = c_h * 2 // 3
        if self.is_court():
            # display big pic in center
            try:
                srf = court_image(self)
            except KeyError:
                srf = self.suit.alt_symbol
            if not isinstance(srf, pygame.Surface):
                srf, _ = font.render(srf, size=3 * sym_size, fgcolor=self.suit.color)
            dest_rect = pygame.Rect(c_x + (c_w - pic_size) // 2, c_y + (c_h - pic_size) // 2, pic_size, pic_size)
            self.surface.blit(srf, srf.get_rect(center=dest_rect.center))
        else:
            sym_area = (c_x, c_y, c_w - sym_size, c_h - sym_size)
            x_pos = [1 / 2] if self.number < 4 else [0, 1]
            rows = min(4, self.number // len(x_pos))
            y_pos = map(lambda x: x / (rows - 1), range(rows))
            positions = ((x, y) for x in x_pos for y in y_pos)
            remain = self.number - rows * len(x_pos)
            remain_pos = map(lambda x: (1 / 2, (2 * x + 1) / 2 / (rows - 1)),
                             {1: [(rows - 2) // 2], 2: [0, rows - 2]}.get(remain, range(remain)))
            for x, y in chain(positions, remain_pos):
                dest_rect = pygame.Rect(sym_area[0] + (x * sym_area[2]),
                                        sym_area[1] + (y * sym_area[3]),
                                        sym_size,
                                        sym_size)
                srf, _ = font.render(self.suit.symbol, size=sym_size,
                                     rotation=180 if dest_rect[1] > midh else 0,
                                     fgcolor=self.suit.color)
                self.surface.blit(srf, srf.get_rect(center=dest_rect.center))


deck = [Card(number=i, suit=Suits.suits[s]) for s in range(4) for i in range(1, 14)]


def _resize(new_size):
    global card_size
    card_size = new_size
    for c in deck:
        c.resize(new_size)


@singledispatch
def resize(new_width):
    new_size = int(new_width), int(new_width * card_ratio)
    _resize(new_size)


@resize.register(tuple)
def _(new_size):
    _resize(new_size)


def show_deck(screen, suit_offset=0, clean=True):
    if(clean):
        screen.fill(Colors.green)
    m = 5
    wc, hc = map(lambda x: x + m, card_size)
    n = len(deck)
    rows = len(Suits.suits)
    cols = (n - 1) // rows + 1
    _, _, ws, hs = screen.get_rect()
    max_wc = min(ws // cols, hs / card_ratio // rows)
    if max_wc < wc:
        resize(max_wc - m)
        wc, hc = map(lambda x: x + m, card_size)
    for c, (i, j) in zip(deck, ((i, j) for i in range(rows) for j in range(cols))):
        screen.blit(c.render(), (m + wc * j, m + hc * i))
    pygame.display.update()


def show_fonts(screen):
    for font_name in cycle(font_selection):
        global font  # init freetype
        font = pygame.freetype.SysFont(font_name, 80)
        # font.style = pygame.freetype.STYLE_STRONG
        # font.origin = True
        show_deck(screen)
        font.render_to(screen, (25, 400), font_name, size=24, fgcolor=Colors.gold)
        while wait_events():
            sleep(0.01)


def wait_events():
    for event in pygame.event.get():
        if event.type == KEYDOWN:
            return False
        if event.type == QUIT:
            raise EOFError('quit signal')
    else:
        return True


def main():
    screensize = (1200, 480)
    screen = pygame.display.set_mode(screensize, RESIZABLE)
    global font  # init freetype
    font = pygame.freetype.SysFont(','.join(font_selection), 80)
    try:
        for offset in cycle(range(4)):
            show_deck(screen, offset)
            while wait_events():
                sleep(0.01)
    except EOFError:
        pass
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
