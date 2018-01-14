###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from browser import document, window
import browser.ajax

from . import binding
from . import html
from .observable import Observable
from .promise import Promise
from .service import Service
from . import stacks
from . import utils

from .modbase import _MetaMod, _ModBase

__all__ = ['Component', 'ComponentInline']


_COMPCOUNT = utils.count(1)

_CIDCOUNT = utils.count(1)


class _MetaComponent(_MetaMod):
    def __init__(cls, name, bases, dct, **kwds):
        # Must be done here, because in new the factory is not there ... only
        # the class dict. This is a "particularity" of brython
        super().__init__(name, bases, dct, **kwds)

        cid = str(next(_COMPCOUNT))
        setattr(cls, '_cid', cid)

        selector = dct.get('selector', None)
        if not selector:
            autosel = []
            lastlower = False
            for x in name:
                if x.isupper():
                    if lastlower:
                        autosel.append('-')
                    autosel.append(x.lower())
                    lastlower = False
                else:
                    autosel.append(x)
                    lastlower = x.islower()

            # Add counter to make unique (same class name in diff module)
            autosel.append('-')
            autosel.append(cid)

            dct['selector'] = selector = ''.join(autosel)
            setattr(cls, 'selector', selector)

        html._customize_tag(selector, dotag=True, component=cls)

    def __call__(cls, *args, **kwargs):
        htmlnode = stacks.htmlnodes[-1]
        if htmlnode._comp is not None:
            # rendered inside another component, send tagout which will
            # piggyback on this
            tag = cls._tagout(_compargs=args, _compkwargs=kwargs)
            return tag._comp

        # scan for kwargs that meet class attributes
        autokwargs = {k: v for k, v in kwargs.items() if hasattr(cls, k)}
        for k in autokwargs:
            kwargs.pop(k)

        self = cls.__new__(cls, *args, **kwargs)  # create

        self._children = []

        # Find enclosing nodes, module and parent component
        self._htmlnode = htmlnode
        self._module = stacks.modules[-1]
        self._parent = htmlnode._elparent._comp
        parent_module = self._parent._module
        if self._module != parent_module:
            self._parent = self._module

        self._parent._children.append(self)

        for k, v in autokwargs.items():  # set the values in the instance
            setattr(self, k, v)  # before going to init

        # choose the namespace under which services will be placed
        if not self.service_ns:
            service_ns = self
        else:
            class Service_PlaceHolder:
                pass  # simple attribute placeholder

            service_ns = Service_PlaceHolder()
            if self.service_ns is True:  # specific check for True
                self._s = service_ns
            else:
                setattr(self, self.service_ns, service_ns)

        # Instantiate and place services under the selected namespace
        for name, service in self.services.items():
            if issubclass(service, (Service,)):
                s = service(self, self._module)
            else:
                s = service()
                s._module = self._module
                s._parent = self

            setattr(service_ns, name, s)

        _cachename = self.cachename
        if not _cachename:
            _cachename = '{}.{}'.format(self.__class__.__module__,
                                        self.__class__.__name__)

        self._cachename_style = '{}.{}'.format(_cachename, 'style')
        self._cachename_html = '{}.{}'.format(_cachename, 'html')

        self.__init__(*args, **kwargs)

        return self


class Component(_ModBase, metaclass=_MetaComponent):
    '''A *Component* controls the appearance and elements inside a patch of the
    screen

    It can render the elements programatically or directly with html content

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

      - ``router``

        Attribute which points to the router instance in charge of the
        application

      - ``route``

        Attribute which contains the current active route snapshot

      - ``selector (None)``

        The selector is the name of the html tag under which the component is
        rendered and controls elements.

        If ``None``, the name will be automatically derived from the name of
        the class

      - ``htmlpath (True)``

        Path to a file containing the html content.

        If ``True`` the name of the file will be derived automatically from the
        class name, i.e.: *MyComponent* -> *my_component.html*. In this case
        the file has to be placed at the same level in the file hierarchy as
        the python module in which the component class is defined.

        To derive the name: underscores will be placed in the upper/lower-case
        boundaries, everything will be lowercased and the extension ``.html``
        will be appended.

        If it contains a *name* (string), this will be used to fetch the file
        from the server (or from a virtual file system if the app is delivered
        as a package)

        This takes precedence over the ``render`` method.

        After loading, the ``render`` method will be called with the node under
        which the content has been loaded

      - ``htmlsheet (None)``

        **This takes precedence over ``htmlpath``.**

        If not ``None``, this will then contain html content in text format,
        which will be used to render the patch

        If ``None``, the name will be automatically derived from the name of
        the class.

        After loading, the ``render`` method will be called with the node under
        which the content has been loaded

      - ``stylepath (True)``

        Path to a file containing the style sheet.

        If ``True`` the name of the file will be derived automatically from the
        class name, i.e.: *MyComponent* -> *mycomponent.css*. In this case the
        file has to be placed at the same level in the file hierarchy as the
        python module in which the component class is defined

        To derive the name: underscores will be placed in the upper/lower-case
        boundaries, everything will be lowercased and the extension ``.css``
        will be appended.

        If it contains a *name* (string), this will be used to fetch the file
        from the server (or from a virtual file system if the app is delivered
        as a package)

        This takes precedence over the ``stlyer`` method.

        After loading, the ``html`` method will be called with the node under
        which the content has been loaded

      - ``stylesheet (None)``

        If not ``None``, this will then contain a style sheet in text format,
        which will be used to control the styles of the elements rendered by
        the component

        **This takes precedence over ``stylepath``**

      - ``cachesheets (True)``

        If ``True``, loaded html content and style sheets will be cached,
        rather than fetched again

      - ``cacheable (True)``

        If ``True``, the component will not be destroyed and recreated each
        time. Setting it to ``False`` forces destruction and recreation

    '''
    cacheable = True  # kept as in between routing or re-created
    cachesheets = True  # keep internal cache of the fetched stylepath
    _styled = set()  # Flag for style delivered to the head
    cachename = None
    selector = None  # selector tag to apply if any
    htmlpath = True  # name or autoname (True) of htmlpath
    htmlsheet = None  # html template
    stylesheet = None  # name or autoname (True) of stylepath
    stylepath = True  # name or autoname (True) of stylepath

    service_ns = False
    services = {}  # name:service of services at component level

    _parent = None  # parent component or module
    _module = None  # module in which the component lives

    _cid = 0  # component id

    def __getattr__(self, name):
        if name.startswith('__'):
            return super().__getattr__(name)

        # During __init__ attributes that have to up the chain may be sought,
        # but the parent may be unknown. This forces this check to make sure it
        # makes it up to the module
        try:
            return getattr(self._parent, name)
        except AttributeError:
            pass

        e = '{} not found in {} nor in its services or hierarchy'. \
            format(name, self.__class__.__name__)
        raise AttributeError(e)

    def __setattr__(self, name, value):
        # Attribute not found using the regular methods
        if name[-1] == '_':
            if isinstance(value, Observable):
                super().__setattr__(name, value)  # special: pointer creation
                return

            name1 = name[:-1]
            if name1 in self.bindings:  # see if it belongs to bindings
                setattr(self, name1, value)  # set in own bindings
                return

            # send to parent
            setattr(self._parent, name, value)
            return

        # new attribute being set, delegate up the chain
        super().__setattr__(name, value)

    @classmethod
    def _tagout(cls, *args, **kwargs):
        return html._tagout(cls.selector, *args, **kwargs)

    def _loaded(self, dochildren=True):
        self.loaded()
        if dochildren:
            for child in self._children:
                child._loaded(dochildren=dochildren)

    def loaded(self):
        pass

    def _load(self, loading=True, dochildren=True):
        self.load(loading=loading)
        if dochildren:
            for child in self._children:
                child._load(loading=loading)

    def _renderer(self, node):
        self._stylerer(node)
        with html.render_node(node):
            promise = self._htmlerer(node)
            if promise:
                stacks.comprender.append(promise)

    def _set_html(self, node, text, cache=True, render=True):
        if text is None:
            return

        node.set_html(text)
        with node:  # be parent of domnodes
            self._visit_nodes(node)  # generate domnode objects

        if cache:
            if self.cachesheets:
                self._module.cache_add(self._cachename_html, text)

        # need to reappend to stack, because it is async
        if render:
            self.render(node)

    def _htmlerer(self, node):
        # 1. checked if html was cached and deliver if possible
        if self.cachesheets:
            cached_html = self._module.cache_get(self._cachename_html)
            if cached_html is not None:
                return self._set_html(node, cached_html, cache=False)

        # Check if html is defined with the component and apply it
        if self.htmlsheet:
            return self._set_html(node, self.htmlsheet)  # rets actually "None"

        # Check if html has to be fetched, if not render programatically
        if not self.htmlpath:
            return self._set_html(node, self.render(node), render=False)

        # prepare the url
        urlpath = self._get_urlcomps(self.htmlpath, '.html')

        # Check paketized versions
        txt = self._get_paketized_file(urlpath)
        if txt is not None:  # paketized forever!
            return self._set_html(node, txt)

        # render is delayed until a download happenes
        promise = Promise()

        # Fetch the html
        def complete(resp):
            if resp.status == 200 or resp.status == 0:  # 0 from example
                with html.render_node(node):  # async call, need to insert
                    self._set_html(node, resp.text)

                promise._resolve(True)
            else:
                promise._reject(resp)

        # The URLs in the browser will be those of the "routes" (if defined),
        # that's why the final url has to be a complete one and not simply a
        # relative one. Hence the call to the router to get it
        url = self.router._routecalc('', urlpath)

        a = browser.ajax.ajax()
        a.bind('complete', complete)
        url += '?v=' + str(window.Date.new().getTime())
        a.open('GET', url, True)
        a.send()
        return promise

    def _can_deactivate(self):
        # Takes care of calling deactivate and returning an Observable if the
        # end user method did not
        ret = self.can_deactivate()
        if not isinstance(ret, Observable):
            ret = Observable.of(ret)

        return ret

    def _binder(self, binder, binding, lambdize=True):
        # To bind binder with binding, but in the local context, so that self,
        # will actually be this "self" and not that belonging to the binder
        if lambdize:
            k = {'self': self}
            exec('_l = lambda: self.{}'.format(binding), k)
            binder(k['_l'])
        else:
            # This supports many more use cases like adding operators to an
            # observable to subscribe, which should be specifically sought
            # below, including having to execute calls
            binder(eval('self.{}'.format(binding), globals()))
            # s = self
            # for a in binding.split('.'):
            #     attr = getattr(s, a)
            #     s = attr
            # binder(attr)

    def _fmtter(self, fmtter, *args, **kwargs):
        # To bind binder with binding, but in the local context, so that self,
        # will actually be this "self" and not that belonging to the binder
        selfargs = []
        for a in args:
            selfargs.append(eval('self.{}'.format(a)))

        # self evaluation in the dictionary comprehension fails if no prev
        # evaluation has taken part outside, like in _binder above
        # selfkw = {k: eval('self.{}'.format(v)) for k, v in kwargs.items()}
        selfkw = {}
        for k, v in kwargs.items():
            selfkw[k] = eval('self.{}'.format(v))

        fmtter(*selfargs, **selfkw)

    # End user methods
    @classmethod
    def selector_render(cls, *args, **kwargs):
        '''Used for rendering inside another component'''
        return cls._tagout(_compargs=args, _compkwargs=kwargs)

    def load(self, loading=True):
        '''
        Called when the component is being loaded/unloaded to/from the DOM

        If not overridden, it will

          - call self.loading() when ``loading=True``

          - call self.unloading() when ``loading=False``
        '''
        if loading:
            self.loading()
        else:
            self.unloading()

    def loading(self):
        '''
        If the method ``load`` is not overridden, this will be called when the
        component is about to be loaded to the DOM
        '''
        pass

    def unloading(self):
        '''
        If the method ``load`` is not overridden, this will be called when the
        component is about to be unloaded from the DOM
        '''
        pass

    def styler(self):
        '''
        Override this method to return the css to apply to the component. The
        returned format is just plain text
        '''
        pass

    def render(self, node):
        '''
        Render programmatically or manipulate loaded html content.

        If ``htmlsheet`` or ``htmlpath`` are defined, this method will
        be called after the html content has been loaded. The content lives
        under node.

        In any other case the method is expected to either:

          - render the html content programmatically

        or

          - return text content which will be the html content to be added to
            the DOM

        The parameter ``node`` is the DOM element under which either the loaded
        html content can be found or under which the programmatic rendering or
        returned text will be inserted.
        '''
        pass

    def can_deactivate(self):
        '''
        Override this method to disallow navigating away from this component
        (and the associated route)

        Returns: ``True/False`` or an ``Observable`` which will
        deliver those values.

        If the final evaluated value is ``True`` navigating away is allowed
        '''
        return True

    def close_outlet(self):
        '''
        To be used to navigate away from the component when it is loaded in a
        named outlet
        '''
        self._load(loading=False)
        self._routlet.clear()


class ComponentInline(Component):
    '''This is a simple subclass of ``Component`` which defines
    ``htmlpath=None`` and ``stylepath=None`` for components that don't have
    external html and css resources
    '''
    stylepath = None
    htmlpath = None
