###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from browser import document, window
import browser.ajax

from . import binding
from .component import Component
from . import html
from .service import Service
from . import router
from . import stacks

from .modbase import _MetaMod, _ModBase

__all__ = ['Module']


def logout(*args, **kwargs):
    if 0:
        print(*args, **kwargs)


class _MetaModule(_MetaMod):
    '''
    Metaclass for Module which prepares the class during creation (for example
    looking for defined services and instantiation by using the appropriate
    kwargs automatically for the pre-defined values in the class
    '''

    def __call__(cls, *args, **kwargs):
        # scan for kwargs that meet class attributes
        autokwargs = {k: v for k, v in kwargs.items() if hasattr(cls, k)}
        for k in autokwargs:
            kwargs.pop(k)

        self = cls.__new__(cls, *args, **kwargs)  # create

        self._module = self  # to mimic components
        self._children = []

        child = bool(stacks.modules)
        if not child:
            stacks.modules.append(self)  # add as last created module
            self._parent = None
        else:
            self._parent = stacks.modules[-1]

        for k, v in autokwargs.items():  # set the values in the instance
            setattr(self, k, v)  # before going to init

        # choose the namespace under which services will be placed
        if not self.service_ns:
            service_ns = self
            self._service_ns = None
        else:
            class Service_PlaceHolder:
                pass  # simple attribute placeholder

            self._service_ns = service_ns = Service_PlaceHolder()
            if self.service_ns is True:  # specific check for True
                self._s = service_ns
            else:
                setattr(self, self.service_ns, service_ns)

        # Instantiate and place services under the selected namespace
        for name, service in self.services.items():
            if issubclass(service, (Service,)):
                s = service(self, self)
            else:
                s = service()
                s._module = self._module
                s._parent = self

            setattr(service_ns, name, s)

        self._caching = {}

        if not child:
            if self.modules:
                if not isinstance(self.modules, (list, tuple)):
                    submods = [self.modules]
                else:
                    submods = self.modules

                isubmods = [submod() for submod in submods]
            else:
                isubmods = []

        if not child:
            # over class attr
            self.router = self.router_cls(self, isubmods, self.routes)
            document.body._comp = self  # Set itself as main parent

        _cachename = self.cachename
        if not _cachename:
            _cachename = '{}.{}'.format(self.__class__.__module__,
                                        self.__class__.__name__)

        self._cachename_style = '{}.{}'.format(_cachename, 'style')
        self._stylerer(document.head)  # need router support, not before
        self.render(document.head)

        self.__init__(*args, **kwargs)

        # Auto-generate DOMNodes, which will kick-start any associated comp
        if not child:
            Component._visit_nodes(document.body)

            comps = self.components
            try:
                if issubclass(comps, Component):
                    comps = [comps]
            except TypeError:
                pass  # issubclass failed because "comps" is not a class

            for comp in comps:
                # Check if components in bootstrap have to still be rendered
                if not document.select(comp.selector):
                    t = html._tagout(comp.selector)  # render comp automatically
                    t._comp._loaded()

            redir = document.query.getvalue('route')
            self.router._routing(redir=redir, recalc=bool(redir))

        return self


class Module(_ModBase, metaclass=_MetaModule):
    '''
    A *Module* is the main control unit for several components, which for
    example will all access a shared service defined in the module.

    A *Module* can hosts *sub-Modules* which will be either specified through
    ``Modules`` or with *routes*

    The module is responsible for instantiating the one-and-only ``router``
    instance

    Attributes:

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

      - ``services ({})``:

        A dictionary containing the name and service class for services defined
        for this and any child component of it

            services = {'myservice': MyService}

      - ``service_ns (False)``:

        If ``False``, services will be added as direct attributes of the
        instance with the name specified in the ``services`` declaration.

        If ``service_ns`` is:

            - ``True``: the declared ``services`` will be reachable under the
              attribute ``self._s.myservice``

              This is meant to separate the services from the rest of the
              attributes.

            - A ``string``, the declared ``services`` will be reachable under
              the attribute ``self.{value of the string}.myservice``. I.e.: for
              a value of ``services_here``, then a service would be reachable
              as::

                self.services_here.myservice

      - ``modules ([])``:

        A single item or an iterable (*list/tuple*) containing sub-modules
        which will fall under the control of this module

        Sub-modules won't actually act as full control units for components,
        because they won't, for example, instantiate a ``router`` instance

      - ``components ([])``:

        A single item or an iterable (*list/tuple*) containing components that
        will be instantiated during start-up. This is usually a single
        component or even no component at all to let the router auto-output an
        outlet and decide which components to load with the defined routes

      - ``routes ([])``:

        The list of routes the module will pass to the router. The routes will
        be extended with children routes coming from sub-modules and
        ``load_children`` definitions

      - ``router``

        Attribute which points to the router instance in charge of the
        application. Meant for components.

      - ``router_cls (router.Router)``

        Class attribute which holds the class to be instantiated as the one and
        only *router* instance
    '''
    modules = []
    components = []  # components to bootstrap
    service_ns = False
    services = {}  # services offered to all the ecosystem (name: service)
    routes = []  # routes definition (list of dict)
    router_cls = router.Router

    cachename = None
    cachesheets = True  # keep internal cache of the fetched stylepath
    _styled = set()  # Flag for style delivered to the head

    stylepath = None
    stylesheet = ''

    def render(self, node):
        pass

    def _get_cid_name(self):
        return ''  # to install at the highest level global

    def cache_add(self, name, value):
        # Used by components to cache html and sheets
        self._caching[name] = value

    def cache_get(self, name):
        # Used by components to retrieve cached html and sheets
        return self._caching.get(name, None)

    def __getattr__(self, name):
        if not name.startswith('__'):
            if self._parent is not None:
                return getattr(self._parent, name)

        return super().__getattr__(name)
