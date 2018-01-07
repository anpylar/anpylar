###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from . import binding


__all__ = ['Service']


class _MetaService(binding.MetaDataBindings):
    def __call__(cls, parent, module, *args, **kwargs):
        self = cls.__new__(cls, *args, **kwargs)  # create
        self._parent = parent
        self._module = module
        self.__init__(*args, **kwargs)
        return self


class Service(binding.DataBindings, metaclass=_MetaService):
    '''
    A *Service* is, as the name indicates* a provider of services for other
    components.

    It is declared in the ``services = {name: ServiceClass,}`` directive of
    *Component* and *Module* classes, to enable functionality like for example
    an http client, a search service, a logging facility, etc.

    Directives:

      - ``bindings ({})``:

        A dictionary containing the name and default value of attributes for
        the class which will also automatically add bound ``Observables``

        The observables will have a ``_`` (underscore) character appended.

        Setting the value of the attribute will trigger the observable and
        therefore any actions/subscriptions associated with it. Example:

            bindings = {'myattr': 'myvalue'}

        will create:

          - An attribute ``myattr`` which defaults to ``myvalue``

          - An observable ``myattr_``

    Attributes:

      - ``_parent``: holds the instance of *Component* or *Module* in which the
        service was instantiated (**use with care**)

      - ``_module``: holds the instance of *Module* in which the
        service (somewhere along the hierarchy) is. This will be the same as
        ``_parent`` if the service is declared in a *Module* (**use with
        care**)

    Attribute Searching:

      - Subclasses of ``Service`` will access the attributes of
        ``self._parent`` if the attribute is not found as an instance/class
        attribute.
    '''

    def __getattr__(self, name):
        if name.startswith('__'):
            return super().__getattr__(name)

        return getattr(self._parent, name)
