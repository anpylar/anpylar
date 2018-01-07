###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from .observable_base import ObservableSource, _MetaObservableSource

from .utils import defaultdict


__all__ = []


class From__Source(ObservableSource):
    '''
    Generates an observable from ``iterable``, generating as many values as
    elements are present in ``iterable``
    '''
    def __init__(self, iterable):
        self._iterable = iterable

    def _subscribed(self, sid, **kwargs):
        for x in self._iterable:
            self.on_next(x, sid=sid)

        self.on_completed(sid=sid)


class Of_Source(ObservableSource):
    '''
    Generates an observable from ``*args``, generating as many values as
    arguments are provided
    '''
    def __init__(self, *args):
        self._args = args

    def _subscribed(self, sid, **kwargs):
        for arg in self._args:
            self.on_next(arg, sid=sid)

        self.on_completed(sid=sid)


class Range_Source(ObservableSource):
    '''
    Generates an observable that will issue ``count`` events starting with
    ``start`` and increasing each iteration by ``step``
    '''
    def __init__(self, start, count, step=1):
        self._start = start
        self._count = count
        self._step = step

    def _subscribed(self, sid, **kwargs):
        for i in range(self._start, self._start + self._count, self._step):
            self.on_next(i, sid=sid)

        self.on_completed(sid=sid)


class Throw__Source(ObservableSource):
    '''
    Create an *Observable* that delivers an error using ``throw``

    .. note:: There is also a ``throw_`` operator. See below.
    '''

    def __init__(self, throw):
        self._throw = throw

    def _subscribed(self, sid, **kwargs):
        self.on_error(self._throw, sid)
