###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from . import stacks


__all__ = ['AuthGuard']


class _MetaAuthGuard(type):
    def __new__(meta, name, bases, dct, **kwds):
        # Scan for services in bases and self and install them
        srv = {}
        for b in bases:
            srv.update(getattr(b, 'services', {}))

        srv.update(dict(dct.pop('services', {})))  # pop/update class services
        dct['services'] = srv  # install in current dictionay

        return super().__new__(meta, name, bases, dct, **kwds)  # create class

    def __call__(cls, *args, **kwargs):
        # scan for kwargs that meet class attributes
        autokwargs = {k: v for k, v in kwargs.items() if hasattr(cls, k)}
        for k in autokwargs:
            kwargs.pop(k)

        self = cls.__new__(cls, *args, **kwargs)  # create

        self._module = stacks.modules[-1]

        for k, v in autokwargs.items():  # set the values in the instance
            setattr(self, k, v)  # before going to init

        # Kickstart any defined services
        for name, service in self.services.items():
            setattr(self, name, service())

        self.__init__(*args, **kwargs)
        return self


class AuthGuard(metaclass=_MetaAuthGuard):
    services = {}  # services offered to all the ecosystem (name: service)

    def __getattr__(self, name):
        if not name.startswith('__'):
            if self._module is not None:
                return getattr(self._module, name)

        return super().__getattr__(name)
