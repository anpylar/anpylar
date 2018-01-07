###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from .observable_base import ObservableOperator, _MetaObservableOperator


from .promise import Promise


__all__ = []


class _MetaToPromise(_MetaObservableOperator):
    def __call__(cls, parent, *args, **kwargs):
        self = super().__call__(parent, *args, **kwargs)  # create

        self._promise = Promise()
        self._parent._subscribe(self, self._get_sid())
        return self._promise


class To_Promise_Operator(ObservableOperator, metaclass=_MetaToPromise):
    def on_next(self, val, sid):
        self._promise._resolve(val)

    def on_error(self, error, sid):
        self._promise._reject(error)
