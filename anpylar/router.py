###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from browser import document, window

from . import config as aconfig
from . import html as html
from . promise import Promise
from . import stacks
from .utils import defaultdict


__all__ = ['Route', 'Router']


class RouteSnapshot(object):
    '''
    Contains the details of a route. Used to keep the details of the active
    route at each moment in time

    Attributes:

      - ``path``: the requested path

      - ``abspath``: the absolute path which is the base href + path

      - ``route_comps``: a list containing the current ``Route`` chain

      - ``params``: a dictionary containing the params for the route
    '''

    def __init__(self, path, abspath, rcomps, module, **kwargs):
        self.path = path
        self.abspath = abspath
        self.route_comps = rcomps
        self.module = module
        self.params = kwargs


class Route(object):
    '''
    Contains the details of a route. Used to keep the details of the active
    route at each moment in time

    Attributes:

      - ``path``: the requested path

      - ``abspath``: the absolute path which is the base href + path

      - ``route_comps``: a list containing the current ``Route`` chain

      - ``params``: a dictionary containing the params for the route
    '''

    _RIDX = 1

    base = None
    path = None
    _rsplit = None
    redirect_to = None
    _redir = None
    path_match = None
    component = None
    params = {}
    active = False
    can_activate = None
    outlet = None

    def __str__(self):
        out = []
        out.append('-' * 10)
        out.append('idx:' + str(self.idx))
        out.append('path:' + self.path)
        out.append('params:' + str(self.params))
        out.append('runsplit:' + self._runsplit)
        out.append('')
        return '(' + ' ; '.join(out) + ')'

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.idx == other.idx

    def __hash__(self):
        return self.idx

    def __init__(self, module, submods, bref, bsplit, **kwargs):
        self.params = {}  # instance specific and not class specific
        self.module = module
        self.children = []

        self.idx = self._RIDX
        self.__class__._RIDX += 1

        self.bref = bref
        self.bsplit = bsplit  # path already split

        for submod in submods:
            for cr in getattr(submod, 'routes', []):
                r = Route(submod, [], '', [], **cr)
                self.children.append(r)

        for k, v in kwargs.items():
            if k in ['load_children', 'children']:
                continue

            setattr(self, k, v)

        if self.can_activate:
            self.can_activate = self.can_activate()

        for cr in kwargs.get('children', []):
            self.children.append(Route(module, [], '', [], **cr))

        for lchild in kwargs.get('load_children', []):
            childmod = lchild()
            for cr in getattr(lchild, 'routes', []):
                r = Route(childmod, [], '', [], **cr)
                self.children.append(r)

        self._rsplit = bsplit + self.path.split('/')

        if not self._rsplit[-1]:  # remove trailing / in split
            self._rsplit.pop(-1)

        self._runsplit = '/'.join(self._rsplit)

        if self.redirect_to:
            if self.redirect_to[0] != '/':
                self._redirsplit = bsplit + self.redirect_to.split('/')
            else:
                self._redirsplit = self.redirect_to.split('/')

            if not self._redirsplit[-1]:    # remove trailing / in split
                self._redirsplit.pop(-1)

            self._redir = '/'.join(self._redirsplit)

    def match(self, url, **kwargs):
        if self.path in ['*', '**']:
            return [self]

        if not url.startswith(self._runsplit):
            return []

        rem_url = url[len(self._runsplit):]
        if rem_url and rem_url[0] == '/':
            rem_url = rem_url[1:]

        for child in self.children:
            ret = child.match(rem_url, **kwargs)
            if ret:
                return [self] + ret

        # no child took it ... check if the appropriate params are given
        for p in self.params or {}:
            if p not in kwargs:
                return []

        # params check passed ... take it
        if self.path_match and rem_url:
            return []

        return [self]


class Router(object):
    '''
    Almighty class controlling the routing internals. It is automatically
    instantiated by the main application *Module*

    Attributes:

      - ``autorouter (True)``:

        If ``True`` and the application components have not issued a
        *router-outlet*, the router instance will do it.

      - ``selector ('router-outlet')``:

        If ``autorouter`` is ``True`` and the components define no
        *router-outlet* for the output of a route, the ``selector`` will be
        issued automatically

      - ``route``

        Contains the ``RouteSnapshot`` corresponding to the active route

      - ``routes``

        A list of the defined ``Routes`` (children routes are reachable inside
        the ``Route``)

      - ``basehref``

        The automatically calculated base href for the app

    '''
    autorouter = True  # create router tags automatically (if not present)
    selector = 'router-outlet'

    _routedivs = {}  # cache components
    _rreg = defaultdict(list)  # register callbacks for ractive

    def __init__(self, module, submods, routes):
        self.module = module  # keep reference to main module

        # Find out the root of the main script. This is the href
        pymodpath = getattr(__BRYTHON__, '$py_module_path')
        pathname = pymodpath.__main__
        if pathname is not None:
            _psplit = pathname.split('//', 1)  # skip scheme
            if len(_psplit) > 1:
                urlsplit = _psplit[1]
            else:
                urlsplit = '/'

            psplit = urlsplit.split('/')[1:-1]  # skip network loc & filenamee
        else:
            psplit = []  # no href is possible

        psplit.insert(0, '')  # add leading /
        self._basehref = self.basehref = bhref = '/'.join(psplit)
        self._basesplit = psplit

        # Time to process the routes - use class arg
        self.routes = rt = []

        for submod in submods:
            for cr in getattr(submod, 'routes', []):
                r = Route(submod, [], bhref, psplit, **cr)
                rt.append(r)

        notfound = None
        for r in routes:
            if r.get('path', '') in ['*', '**']:
                notfound = Route(module, [], bhref, psplit, **r)
            rt.append(Route(module, [], bhref, psplit, **r))

        if notfound:  # make sure notfound is always last
            rt.append(notfound)

        self._ractive = None  # no route active - module just started
        self._ractives = []  # route instances

        # register itself to manage state events
        window.onpopstate = self._onpopstate

    def _onpopstate(self, evt):
        # pushstate is delicate in what's accepted as state. If there were no
        # params an empty string (evaluates to False) was passed and we use the
        # false evaluation to replace it with an empty dict
        kwargs = {}
        if evt.state:
            # a dict(*evt.state) fails with $nat undefined
            kwargs.update({x: y for x, y in evt.state})

        self._routing(popstate=True, params=((), kwargs))

    def _routeregister(self, pathname, cb, *args, **kwargs):
        # route = self._routecalc(pathname)
        self._rreg[pathname].append((cb, args, kwargs))

    def _routecalc(self, *args):
        tail = '/'.join(args)
        if tail and tail[0] == '/':
            return '/'.join((self._basehref, tail[1:]))

        # return '/'.join((self._basehref, tail))

        if tail:
            if self._ractive:
                return '/'.join((self._ractive, tail))

            return tail

        return self._ractive

    def _route_to(self, cango, pathname, _recalc=True, *args, **kwargs):
        if not cango:
            return

        if _recalc:
            route = self._routecalc(pathname)
        else:
            route = pathname

        pparts = route.split('/')
        skip = False
        fpparts = []
        for p in reversed(pparts):
            if p == '..':
                skip = True
            elif skip:
                skip = False
            elif p != '.':
                fpparts.append(p)

        route = '/'.join(reversed(fpparts))

        self._routing(redir=route, params=(args, kwargs))

    def _routing(self, popstate=False, redir=None, recalc=False, params=()):
        if stacks.comprender:
            def reroute(val):
                self._routing(popstate=popstate, redir=redir,
                              recalc=recalc, params=params)

            comprender = stacks.comprender[:]  # copy list
            stacks.comprender.clear()  #
            p = Promise.all(*comprender).then(reroute)
            if aconfig.router.log_comprender:
                p.catch(
                    lambda x: print(
                        'Router: Waiting for component rendering failed:', x
                    )
                )
            return

        if not redir:
            pathname = document.location.pathname
            psplit = pathname.split('/')
            if pathname[-1] == '/':
                psplit.pop(-1)
            elif pathname.endswith('.html'):
                psplit.pop(-1)

            punsplit = '/'.join(psplit)
        else:
            if recalc:  # redir has been supplied
                redir = self._routecalc(redir)

            punsplit = redir

        # Get the actual requested path without the baseref
        punpath = punsplit[len(self._basehref):]

        if params:
            args, kwargs = params
        else:
            args = ()
            kwargs = {}

        if ';' in punsplit:  # params are being sent
            # remove before route matching
            lcolons = punsplit.split(';')
            punsplit = lcolons[0]  # [:-1]  # remove final /
            for colon in lcolons[1:]:
                name, value = colon.split('=')
                kwargs[name] = value

        for r in self.routes:
            route_path = r.match(punsplit, **kwargs)
            if not route_path:
                continue

            r0 = route_path[0]
            outlet = r0.outlet

            if not outlet:
                comp, rout = None, None
                while self._ractives:
                    r = self._ractives.pop()
                    if r in route_path:
                        self._ractives.append(r)
                        # comp, rout = self._routedivs.get(r.idx, (None, None))
                        break  # this doesn't need refresh

                    r.active = False
                    newcomp, newrout = self._routedivs.get(r.idx, (None, None))
                    if newcomp:
                        comp, rout = newcomp, newrout

                if comp is not None:
                    comp._load(loading=False)
                    rout.parentNode.clear()  # clear the outlet, not the div

                next_r = route_path[-1]
                pstate = punsplit
                if kwargs:
                    paramstate = ';'.join(
                        ('='.join((str(k), str(v))) for k, v in kwargs.items()
                         if k in next_r.params)
                    )

                    if paramstate:
                        pstate += ';' + paramstate

                # Passing an empty dict as state (1st arg) later returns an
                # <Object object> which cannot be used anywhere, hence passing
                # an empty string
                if not popstate and not next_r.redirect_to:
                    pstate = pstate  # punsplit for no query string
                    if kwargs:
                        lkwargs = list(kwargs.items())
                        window.history.pushState(lkwargs, '', pstate)
                    else:
                        window.history.pushState('', '', pstate)

                r = next_r  # r is now the route to be activated
                if r.params:  # transformations may be needed
                    for name, transform in r.params.items():
                        if name in kwargs:
                            kwargs[name] = transform(kwargs[name])

                active_route = RouteSnapshot(punpath, punsplit,
                                             route_path, r.module, **kwargs)

                self.module.route = self.module.r = self.route = active_route
                self.module.params = self.module.p = active_route.params

                if len(route_path) == len(self._ractives):
                    # params update
                    route = route_path[-1]
                    # won't loop, route must be active
                    if route.idx in self._routedivs:
                        comp, rdiv = self._routedivs[route.idx]
                        if comp is not None:
                            comp._load(dochildren=False)

                    return

                lastroute = route_path[-1]
                if lastroute.redirect_to:
                    self._routing(redir=lastroute._redir, recalc=True,
                                  params=params)
                    return

                node = document  # position 0
                for route in route_path[1:len(self._ractives)]:
                    if route.idx in self._routedivs:
                        _, node = self._routedivs[route.idx]

                if self._ractive in self._rreg:
                    rreg = self._rreg[self._ractive]
                    for cb, a, kw in self._rreg[self._ractive]:
                        cb(False, *a, **kw)

                self._ractive = punsplit

                if punsplit in self._rreg:
                    for cb, a, kw in self._rreg[punsplit]:
                        cb(True, *a, **kw)

                rpath = route_path[len(self._ractives):]
            else:
                node = document.body  # position 0
                rpath = route_path

            isoutlet = bool(outlet)
            for route in rpath:
                if route.can_activate:
                    if not route.can_activate.can_activate(active_route):
                        return

                outlet = route.outlet
                if not isoutlet:
                    self._ractives.append(route)

                selector = self.selector
                if outlet:
                    selector += '[name="{}"]'.format(outlet)
                routlet = node.select_one(selector)
                if not routlet:
                    if not self.autorouter:
                        return  # nothing can be done

                    if not outlet:
                        routlet = html._routeout(self.selector)
                    else:
                        routlet = html._routeout(self.selector, name=outlet)

                # load (or reload) the node
                rdiv = None
                if route.idx in self._routedivs:
                    comp, rdiv = self._routedivs[route.idx]
                    if comp is not None:
                        comp._load(dochildren=False)
                        routlet._comp._children = [rdiv._comp]
                        routlet <= rdiv
                else:
                    # With auto-instantiation, the code from above would
                    # duplicate a component. Once due to instantiation and a
                    # 2nd one because of the tagout
                    stacks.modules.append(route.module)
                    if route.component is not None:
                        with html.render_node(routlet):
                            rdiv = html._routeout(route.component.selector)
                        comp = rdiv._comp
                        # children do it for themselves during creation
                        routlet._comp._children = [comp]
                        comp._routlet = routlet
                        comp._rdiv = rdiv
                        comp._load(dochildren=False)
                        if comp.cacheable:
                            self._routedivs[route.idx] = (comp, rdiv)

                    stacks.modules.pop()

                if rdiv:
                    node = rdiv  # update routlet to search only below

            return

    # End user methods
    def route_to(self, pathname, *args, **kwargs):
        '''
        As the name indicates, this method routes to: ``pathname``

          - ``pathname``

            Absolute or relative path. ``.`` and ``..`` are supported as path
            elements

          - ``args`` and ``kwargs`` will be passed as arguments to the route
        '''
        _recalc = kwargs.pop('_recalc', True)
        ractive = self._ractives[-1] if self._ractives else None
        if ractive:
            comp, rout = self._routedivs.get(ractive.idx, (None, None))
            if comp:
                ret = comp._can_deactivate()
                ret.subscribe(
                    lambda x: self._route_to(
                        x, pathname, _recalc=_recalc, *args, **kwargs
                    )
                )
                return

        self._route_to(True, pathname, *args, **kwargs)

    def back(self):
        '''Navigate once backwards'''
        window.history.back()

    def forward(self):
        '''Navigate once forward'''
        window.history.forward()
