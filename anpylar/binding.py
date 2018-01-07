###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from .observable_attribute import ObservableAttribute
from . import stacks
from .utils import defaultdict


__all__ = ['MetaDataBindings', 'DataBindings', 'Model']


class _Binding(object):
    '''
    This is a descriptor meant to work as a binding, ie: it does accept
    *subscriptions* from external which get bound to changes in the value held
    for each object

    Attributes

      - _name: informative and could be used for debugging. Name of the
        attribute in the host class

      - default: default value when a class is instantiated

      - cache: holds the current value for each instance plus itself for class
        lookups

      - subs: a dictionary holding the subscriptions
    '''
    def __init__(self, name, default):
        self._name = name
        self.default = default
        self.cache = {None: self}  # for class attribute lookups
        self.subs = defaultdict(list)  # hold list of subs  per object

    def __get__(self, obj, cls=None):
        # return cached value or set the default as value
        return self.cache.setdefault(obj, self.default)

    def __set__(self, obj, val, who=None):
        # After setting the value for obj, notify subscriptors except notifier
        self.cache[obj] = val
        for cb, ptd, whom in self.subs[obj]:
            # pass the value set by who to the subscriptors
            if not whom or whom is not who:  # only for those who are not "who"
                # if the pointed to value is wished, retrieve it
                pval = val if ptd is None else getattr(val, ptd)
                cb(pval, whom)

    def _notify(self, obj, val, who, ptd):
        # Used by ObservablePointed points to a final value. After the final
        # value is set, ObservablePointed lets the descriptor know which value
        # vas set and for which pointed value. If subscriptors for that ptd
        # value are available they are notified
        for cb, _ptd, whom, in self.subs.get(obj, []):
            if _ptd == ptd and whom is not who:
                cb(val, whom)

    def subscribe(self, obj, cb, ptd=None, who=None):
        # A subscription has the following attributes
        #   - obj: the object hosting this descriptor (instance)
        #   - who: the subscriptor, which must be a callable
        #   - ptd: if not None, the subscription is not looking for the value
        #   of this descriptor, but rather an attribute held by value stored by
        #   this descriptor for obj
        #   - *args, **kwargs, the arguments to pass back to the subscriptor
        self.subs[obj].append((cb, ptd, who))

        ret = self.__get__(obj)  # return the current value held for obj
        if ptd is not None:
            ret = getattr(ret, ptd)

        return ret


# Name of the attribute in "DataBindings" which contains _Binding(s)
_BINDINGS = 'bindings'


class MetaDataBindings(type):
    '''
    Metaclass which prepares a DataBindings class by replacing "bindings" (a
    dict or iterables of 2-tuples) with _Bindings
    '''
    def __new__(meta, name, bases, dct, **kwds):
        # Get the _BINDINGS which must be a dict or tuple of 2-tuples
        nattrs = dict(dct.pop(_BINDINGS, {}))
        # replace them with _Binding instances
        dct.update({name: _Binding(name, val) for name, val in nattrs.items()})
        # Go over the base classes and do the same
        battrs = {}
        _ = [battrs.update(getattr(x, _BINDINGS, {})) for x in bases]
        battrs.update(nattrs)
        # update the value in the class dictionary
        dct[_BINDINGS] = battrs
        # let the class be created
        return super().__new__(meta, name, bases, dct, **kwds)


class DataBindings(metaclass=MetaDataBindings):
    '''
    Base class for classes holding "bindings" (values that one can subscribe to
    and can be declared)

    During instance creation the declarations in bindings are created in the
    instance as attributes and as ObservableAttribute (for quick retrieval
    later)
    '''
    def __new__(cls, *args, **kwargs):
        attrs = getattr(cls, _BINDINGS)  # Get the defined bindings
        # scan kwargs for values intended to initialize bindings and remove
        # use default value if not present in kwargs
        defaults = {k: kwargs.pop(k, v) for k, v in attrs.items()}
        self = super().__new__(cls, *args, **kwargs)  # create instance
        for k, v in defaults.items():
            setattr(self, k, v)  # set attribute
            # Set ObservableAttribute to avoid dynamic creation
            setattr(self, '{}_'.format(k), ObservableAttribute(self, k))

        return self


# Small alias for DataBindings for classes which simply hold bindings but are
# not modules or components
Model = DataBindings
