###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
__all__ = ['empty', 'deque', 'defaultdict', 'itercount', 'operators']


def logout(*args, **kwargs):
    print(*args, **kwargs)


class empty(object):
    def __init__(self, *args, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    pass  # placeholder to place elements on


# Importing defaultdict from plain "collections" pulls in several modules and
# adds over 1s in loading time in 7700HQ processor. Importing it from
# Javascript's _collections alleviates the situation partially. Defining it
# makes it faster
class defaultdict(dict):
    def __init__(self, default):
        super().__init__()
        self._default = default

    def __missing__(self, key):
        self[key] = r = self._default()
        return r


class deque(list):
    def __init__(self, iterable=None, maxlen=0):
        self._maxlen = maxlen
        if iterable is not None:
            if len(iterable) > maxlen:
                iterable = iterable[:maxlen]

            args = [iterable]
        else:
            args = []

        super().__init__(*args)

    def append(self, item):
        if self._maxlen and len(self) == self._maxlen:
            self.pop(0)  # remove from left

        super().append(item)  # append to right

    def appendleft(self, item):
        if self._maxlen and len(self) == self._maxlen:
            self.pop()  # default -1, remove from right

        self.insert(0, item)  # append to left

    def popleft(self):
        return self.pop(0)  # remove and return from left


# avoid import from heavy lifting operator module
class operators:
    eq = staticmethod(lambda x, y: x == y)
    gt = staticmethod(lambda x, y: x > y)
    ge = staticmethod(lambda x, y: x >= y)
    lt = staticmethod(lambda x, y: x < y)
    le = staticmethod(lambda x, y: x <= y)


def itercount(start=0, step=1):
    while True:
        yield start
        start += step


class count:
    def __init__(self, start=0, step=1):
        self.start = start - 1
        self.step = 1

    def __iter__(self):
        return self

    def __next__(self):
        self.start += self.step
        return self.start
