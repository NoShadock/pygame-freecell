#!/usr/bin/env python3
import pygame
import pygame.freetype
from pygame.constants import RESIZABLE, KEYDOWN, QUIT
from collections import namedtuple
from functools import partial, singledispatch, reduce
from itertools import chain, cycle, starmap
from time import sleep
from operator import sub
from contextlib import suppress

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
            self._surface.fill(Colors.white)
            if 'font' not in dir(self) or self.font is None:
                global font
                if font is None:
                    font = pygame.freetype.SysFont(','.join(font_selection), 80)
                self.font = font
            with suppress(ValueError, ZeroDivisionError, StopIteration):
                self.render_surface()
            return self._surface

    def render(self):
        """NB: rendered surface is cached ; call clear to trully render again"""
        return self.surface

    def render_surface(self):
        raise NotImplementedError('CardSurface is an abstract class')

    def clear(self):
        """
        Clear surface to trigger rendering
        """
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


def symetry_arithmetic_dist(coord_1d, coord_1d_axis):
    return 2 * (coord_1d - coord_1d_axis) - 1


def rect_symetry(rect, x=None, y=None):
    i = j = 0
    if x:
        i = symetry_arithmetic_dist(x, rect.centerx)
    if y:
        j = symetry_arithmetic_dist(y, rect.centery)
    return rect.move(i, j)


def _dichoto_next(bottom, top, mid, func_eval, goal):
    """
    Assuming positive gradient (monotonous growing function)
    """
    if func_eval == goal:
        return None
    elif func_eval > goal:
        if mid > bottom:
            return (bottom, mid - 1)
        else:
            return None
    else:
        if mid < top:
            return (mid + 1, top)
        else:
            return None


def _dichoto_search(goal, func, a, b):
    """
    Assuming positive gradient (monotonous growing function)
    """
    c = (a + b) // 2
    y, resp = func(c)
    latest = (c, resp)
    try:
        a, b = _dichoto_next(a, b, c, y, goal)
    except TypeError:
        return latest
    else:
        return _dichoto_search(goal, func, a, b)


def _dichoto_search_2D(gx, gy, func, ax, bx, ay, by):
    """
    Assuming positive gradient (monotonous growing function)
    """
    cx, cy = (ax + bx) // 2, (ay + by) // 2
    (fx, fy), resp = func(cx, cy)
    latest = ((cx, cy), resp)
    try:
        ax, bx = _dichoto_next(ax, bx, cx, fx, gx)
    except TypeError:
        ax = bx = cx
    try:
        ay, by = _dichoto_next(ay, by, cy, fy, gy)
    except TypeError:
        ay = by = cy
    if ax == bx and ay == by:
        return latest
    else:
        return _dichoto_search_2D(gx, gy, func, ax, bx, ay, by)


def font_fill(font, text, size, botx=1, boty=1, **kwargs):
    gx, gy = size

    def func(x, y):
        srf, r = font.render(text, size=(x, y), **kwargs)
        return r.size, (srf, r)

    c, (srf, r) = _dichoto_search_2D(gx, gy, func, botx, 3 * gx, boty, 3 * gy)
    return srf, r


class Card(CardSurface):
    """
    CardSurface rendered procedurally from unicode symbols.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with suppress(KeyError):
            self.font = kwargs['font']

    def blit_text_to(self, surface, text, position, centered=True):
        txt_srf, _ = font_fill(self.font, text, size=position.size, fgcolor=self.suit.color)
        if centered:
            position = txt_srf.get_rect(center=position.center)
        surface.blit(txt_srf, position)

    def render_surface(self):
        card = self.surface.get_rect()
        # border
        pygame.draw.rect(self.surface, Colors.black, card, 1)
        # corners
        margin = card.w // 20
        corner_sprite = pygame.Surface(size=(card.w // 8, card.h // 4))
        corner_sprite.fill(Colors.white)
        corner_value = corner_sprite.get_rect()
        corner_value.height //= 2  # top half corner
        self.blit_text_to(corner_sprite, text=self.value, position=corner_value)
        corner_sym = pygame.Rect(corner_value.midbottom, (min(corner_value.size),) * 2)
        corner_sym.centerx = corner_value.centerx
        self.blit_text_to(corner_sprite, text=self.suit.symbol, position=corner_sym)
        topleft_corner = corner_sprite.get_rect().move(margin, margin)
        corners = [rect_symetry(topleft_corner, x=x, y=y) for x in [None, card.centerx] for y in [None, card.centery]]
        flipped_corner_sprite = pygame.transform.flip(corner_sprite, False, True)
        for corner_position in corners:
            self.surface.blit(flipped_corner_sprite if corner_position.y > card.centery else corner_sprite, corner_position)
        # center symbols
        botright_corner = next((c for c in corners if c.x > card.centerx and c.y > card.centery))
        cisize = tuple(map(lambda it: reduce(sub, it), zip(botright_corner.bottomleft, (margin, 0), topleft_corner.midright)))
        card_image_sprite = pygame.Surface(size=cisize)
        card_image = card_image_sprite.get_rect(center=card.center)
        sym_size = min(2 * card_image.width // 5, card_image.height // 4)
        court_size = 3 * sym_size
        if self.is_court():
            # display big pic in center
            try:
                court_srf = court_image(self)
            except KeyError:
                court_srf = self.suit.alt_symbol
            if not isinstance(court_srf, pygame.Surface):
                court_srf, _ = self.font.render(court_srf, size=court_size, fgcolor=self.suit.color)
            self.surface.blit(court_srf, court_srf.get_rect(center=card_image.center))
        else:
            sym_sprite, sym = font_fill(self.font, text=self.suit.symbol, size=(sym_size,) * 2, fgcolor=self.suit.color)
            sym.topleft = (0, 0)
            flipped_sym_sprite = pygame.transform.flip(sym_sprite, False, True)
            # numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            # columns = [1, 1, 1, 2, 2, 2, 2, 2, 2, 2]
            # per_col = [1, 2, 3, 2, 2, 3, 3, 3, 4, 4]
            # remaind = [0, 0, 0, 0, 1, 0, 1, 0, 1, 2]
            if self.number < 4:
                per_col = self.number
                column_x = card_image.centerx - (sym.width // 2)
            else:
                per_col = self.number // 3 + 1
                column_x = card_image.x
            column_y = (card_image.y + (card_image.h - sym.h) * k / (per_col - 1) for k in range(per_col))
            positions = [sym.move(column_x, y) for y in column_y]
            if self.number >= 4:  # add symetric positions
                positions += [rect_symetry(pos, x=card_image.centerx) for pos in positions]
            column_y = [card_image.y + sym.h / 2 + (card_image.h - sym.h) * (2 * k + 1) / 2 / (per_col - 1) for k in range(per_col)]
            remainder_y = {5: [card_image.centery], 9: [card_image.centery], 7: column_y[0:1], 8: column_y[0:2],
                           10: column_y[0:3:2]}.get(self.number, [])
            positions += (sym_sprite.get_rect(center=(card_image.centerx, y)) for y in remainder_y)
            for pos in positions:
                self.surface.blit(flipped_sym_sprite if pos.y > card.centery else sym_sprite, pos)


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
    pygame.init()
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
