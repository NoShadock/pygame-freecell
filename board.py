from deck import card_size, Colors, Card
import pygame
from collections import deque
from itertools import count


class Slot(object):
    """
    A space on the board that can contain zero, one or many Card -> Sequence<Card>
    """

    def __init__(self, spread=False, spreadth=0):
        self.stack = []
        self.spread = spread
        if spread and spreadth < 1:
            raise ValueError(f'cannot spread slot stack lower than spreadth=1, got {spreadth}')
        self.spreadth = spreadth
        self._peeking_at = None

    def __getitem__(self, index):
        return self.stack[index]

    def __len__(self):
        return len(self.stack)

    def put(self, cards):
        """
        Put a single card or iterable on top of the slot if feasible
        Raises ValueError if not feasible
        """
        if isinstance(cards, Card):
            self.put_single(cards)
        else:
            # backup state for revert
            self.freeze()
            try:
                for c in cards:
                    self.put_single(c)
            except ValueError as e:  # revert changes
                self.revert()
                raise e
            finally:
                self.unfreeze()

    def freeze(self):
        '''save state for upcoming revert'''
        self._freeze_stack = self.stack.copy()

    def revert(self):
        '''revert to previously frozen state'''
        self.stack = self._freeze_stack

    def unfreeze(self):
        '''delete saved state'''
        del self._freeze_stack

    def put_single(self, card):
        self.stack.append(card)

    def pop_from(self, index):
        resp, self.stack = self[index:], self[:index]
        return resp

    def receive_from(self, slot, max_cards):
        # print(self.__class__.__name__, ': receive max ', max_cards)
        for k in range(max_cards, 0, -1):
            try:
                self.put(slot[-k:])
            except ValueError:
                continue
            else:
                slot.pop_from(-k)
                return True
        else:
            return False

    def is_empty(self):
        try:
            self[0]
        except IndexError:
            return True
        else:
            return False

    @property
    def base_size(self):
        global card_size
        return card_size

    def _step_height(self):
        if not self.spread:
            return 0
        n = len(self)
        if n == 0:
            return 0
        _, h = self.base_size
        return min(h // 6, int((self.spreadth - 1) * h // n))

    def _height(self, index):
        return int(index * self._step_height())

    def get_index(self, position):
        """
        position -> tuple (x, y) relative position to the Slot origin/topleft
        """
        x, y = position
        s = self._step_height()
        if s == 0:
            return len(self) - 1
        else:
            return min(len(self) - 1, int(y / s))

    def get_position(self, index):
        """
        return position -> tuple (x, y) relative position to the Slot origin/topleft
        """
        if index < 0:
            index += len(self)
        return (0, self._height(index))

    def area(self):
        w, h = self.base_size
        return pygame.Rect(0, 0, w, self.get_position(-1)[1] + h)

    def peek_on(self, index_or_position):
        try:
            x, y = index_or_position
        except TypeError:
            index = index_or_position
        else:
            index = self.get_index(index_or_position)
        if 0 <= index < len(self):
            self._peeking_at = index
            # print(f'{self.__class__.__name__}: peeking at {index}')
        else:
            raise IndexError('peeking index out of bounds')

    def peek_off(self):
        self._peeking_at = None

    def render(self):
        # TODO improve perf
        w, h = self.base_size
        surface = pygame.Surface(size=(w, self.spreadth * h if self.spread else h))
        surface.fill(Colors.light_green, pygame.Rect(0, 0, w, h))
        surface.set_colorkey(Colors.black)
        for i, card in enumerate(self):  # TODO reverse order to lazy blit
            surface.blit(card.render(), self.get_position(i))
        if self._peeking_at is not None:
            surface.blit(self[self._peeking_at].render(), self.get_position(self._peeking_at))
        return surface

    def save(self):
        return self.stack.copy()

    def load(self, from_stack):
        self.stack = from_stack


class FoundationSlot(Slot):
    """docstring for FoundationSlot"""

    def put_single(self, card):
        try:
            topmost = self[-1]
        except IndexError:  # empty slot
            if card.number == 1:
                super().put_single(card)
            else:
                raise ValueError(f'First on FoundationSlot must be an Ace, got {card}')
        else:
            if card.suit == topmost.suit and card.number == topmost.number + 1:
                super().put_single(card)
            else:
                raise ValueError(f'Expecting following to {topmost} got {card}')


class ToggleSlot(Slot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._toggle = False

    def toggle(self, value=None):
        if self.is_empty():
            self._toggle = False
        elif value:
            self._toggle = value
        else:
            self._toggle ^= True
        return self._toggle

    def render(self):
        srf = super().render()
        if self._toggle:
            shade = pygame.Surface(size=self.area().size)
            shade.fill(Colors.blueish)
            shade.set_alpha(100)
            srf.blit(shade, self.area())
        return srf


class ReserveSlot(ToggleSlot):
    """docstring for ReserveSlot"""

    def put_single(self, card):
        if self.is_empty():
            super().put_single(card)
        else:
            raise ValueError('Slot is already occupied')

    def receive_from(self, slot, *a, **kw):
        return super().receive_from(slot, max_cards=1)


class TableauSlot(ToggleSlot):
    """docstring for TableauSlot"""

    def __init__(self):
        super().__init__(spread=True, spreadth=2.5)

    def put_single(self, card):
        try:
            topmost = self[-1]
        except IndexError:
            super().put_single(card)
        else:
            if card.number == topmost.number - 1 and card.suit.index % 2 != topmost.suit.index % 2:
                super().put_single(card)
            else:
                raise ValueError(f'{card} cannot stack on {topmost}')


def main():
    pass


if __name__ == '__main__':
    main()
