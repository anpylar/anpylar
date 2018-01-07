###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from .utils import operators

from .observable import Observable, ObservableSource, ObservableFetchError


__all__ = ['Observable', 'ObservableAttribute', 'ObservablePointed']


class ObservableAttribute(ObservableSource):

    def __init__(self, obj, name, ptd=None):
        # super().__init__()
        self._desc = getattr(obj.__class__, name)  # to access _Binding API
        self._obj = obj  # object to which is pointed
        self._name = name  # attribute pointed to
        self._ptd = ptd
        self._whos = {}

    def _subscribed(self, sid, **kwargs):
        who = getattr(kwargs.get('who', None), '_elid', None)
        if who is not None:
            self._whos[who] = sid

        val = self._desc.subscribe(self._obj, self.on_next,
                                   ptd=self._ptd, who=sid)

        self.on_next(val, sid)

        if kwargs.get('fetch', False):  # someone wants to pre-fetch
            raise ObservableFetchError(val)

    def on_next(self, val, sid):
        super().on_next(val, sid)

    def __getattr__(self, name):
        if not name.startswith('__'):
            if name[-1] == '_':  # format is: xxx_
                op = ObservablePointed(self._obj, self._name, name[:-1])
                setattr(self, name, op)  # cache it
                return op

        return super().__getattr__(name)

    def __call__(self, val, who=None):
        sid = self._whos.get(getattr(who, '_elid', None), None)
        self._desc.__set__(self._obj, val, who=sid)  # triggers subscriptions
        return val


class ObservablePointed(ObservableAttribute):

    def __call__(self, val, who=None):
        sid = self._whos.get(getattr(who, '_elid', None), None)

        ptrobj = self._desc.__get__(self._obj)
        ptrdesc = getattr(ptrobj.__class__, self._ptd)
        ptrdesc.__set__(ptrobj, val, who=sid)

        self._desc._notify(self._obj, val, sid, self._ptd)

        return val
