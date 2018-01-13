###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from browser import document, window
import browser.ajax
from . import html

from . import binding


class _MetaMod(binding.MetaDataBindings):
    def __new__(meta, name, bases, dct, **kwds):
        # Scan for services in bases and self and install them
        srv = {}
        for b in bases:
            srv.update(getattr(b, 'services', {}))

        srv.update(dict(dct.pop('services', {})))  # pop/update class services
        dct['services'] = srv  # install in current dictionay

        return super().__new__(meta, name, bases, dct, **kwds)  # create class

    def __init__(cls, name, bases, dct, **kwds):
        super().__init__(name, bases, dct, **kwds)
        # calculate the name for html/css fetching
        urlname = []
        lastlower = False
        for x in name:
            if x.isupper():
                if lastlower:
                    urlname.append('_')
                urlname.append(x.lower())
                lastlower = False
            else:
                urlname.append(x)
                lastlower = x.islower()

        cls._urlname = ''.join(urlname)

    def __call__(cls, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class _ModBase(binding.DataBindings, metaclass=_MetaMod):
    # This javascript insert allows finding the vfs entry in the brython
    # structures, which in turn will be used to locate non-python files for
    # packetized apps
    _anpylar_vfs_finder = '''
    ;(function($B){
        var _b_ = $B.builtins

        $B._anpyl_vfs_finder = function(path, fullname) {
            vpf = $B.path_importer_cache[path] // no path check
            // console.log('vpf is:', vpf)
            vfs = vpf.vfs[fullname]
            // console.log('vfs is:', vfs)
            if(vfs !== undefined)
                return vfs[1]

            return _b_.None
        }
    })(__BRYTHON__)
    '''

    __BRYTHON__.win.eval(_anpylar_vfs_finder)

    @staticmethod
    def _get_paketized_file(name):
        parts = name.split('/')
        bundle_name = '{}.vfs.js/'.format(parts[0])
        for k in __BRYTHON__.path_importer_cache.to_dict():
            if not k.endswith(bundle_name):
                continue

            return __BRYTHON__._anpyl_vfs_finder(k, name)  # found - ret it

        return None

    def _css_transform(self, css):
        cid_name = self._get_cid_name()
        if not cid_name:
            return css

        prefix = '[' + cid_name + ']'
        transformed = []
        for l in css.splitlines():
            ls = l.lstrip()
            if not ls or ls[0] == '@':
                transformed.append(l)
                continue  # skip empty / @xxx / non opening bracket lines

            bracepos = l.find('{')
            if bracepos == -1:
                transformed.append(l)
                continue  # skip empty / @xxx / non opening bracket lines

            lrest = ls[bracepos:]  # brace and anything after it
            l = ls[:bracepos]  # everything before the brace
            ltokens = l.rstrip().split()  # split whitespace
            for i, token in enumerate(ltokens):
                if token == '>':  # token must not be touched
                    continue

                if ':' in token:  # : was found, 2 tokens in place
                    ldots = token.split(':')  # put prefix before :
                    ltokens[i] = ldots[0] + prefix + ':' + ldots[-1]
                    continue

                if token[-1] == ',':  # place before comma if present
                    ltokens[i] = token[:-1] + prefix + ','
                    continue

                ltokens[i] = token + prefix  # regular case

            if not(ltokens):  # only {  - didn't loop
                ltokens.append(prefix)

            ltokens.append(lrest)  # restore the brace (and rest if any)
            transformed.append(' '.join(ltokens))

        return '\n'.join(transformed)

    def _get_urlcomps(self, flag, extension):
        # prepare the url
        modname = self.__class__.__module__
        urlbase = '/'.join(modname.split('.')[:-1])
        urlcomps = [urlbase] * bool(urlbase)  # nullify to avoid leading /
        if flag is True:  # specific check for True not for truthness
            urlcomps.append(self._urlname + extension)
        else:  # has to be str
            urlcomps.append(self.stylepath)

        return '/'.join(urlcomps)

    def _get_cid_name(self):
        return self.__class__.__name__.lower() + '-' + str(self._cid)

    @staticmethod
    def _visit_nodes(node):
        # visiting the nodes generates DOMNode instances using the specific tag
        # classes for each tagname, which guarantees access to the superchared
        # tags defined in the html module
        for elem in node.children:
            Component._visit_nodes(elem)

    def _insert_style(self, style, cache=True):
        if not style:
            return

        txt = self._css_transform(style)
        with html.render_node(document.head):
            k = {self._get_cid_name(): ''}
            with html.style(**k) as this:
                this <= txt

        self._styled.add(self.__class__)  # mark as delivered
        if cache and self.cachesheets:
            self._module.cache_add(self._cachename_style, txt)

    def _stylerer(self, node):
        # class-wide check (in spite of self)
        if self.__class__ in self._styled:
            if self.cachesheets:  # if has to refetch, don't bail out
                return  # already in the head

        if self.cachesheets:
            cached_style = self._module.cache_get(self._cachename_style)
            if cached_style is not None:
                return self._insert_style(cached_style, cache=False)

        if self.stylesheet:
            return self._insert_style(self.stylesheet)

        if not self.stylepath:
            return self._insert_style(self.styler())

        # get the url
        urlpath = self._get_urlcomps(self.stylepath, '.css')

        # Check paketized versions
        # vfspath = '/'.join(urlcomps)
        txt = self._get_paketized_file(urlpath)
        if txt is not None:
            return self._insert_style(txt)

        # Fetch via ajax
        def complete(resp):
            if resp.status == 200 or resp.status == 0:  # 0 from example
                self._insert_style(resp.text)

        # The URLs in the browser will be those of the "routes" (if defined),
        # that's why the final url has to be a complete one and not simply a
        # relative one. Hence the call to the router to get it
        url = self.router._routecalc('', urlpath)

        a = browser.ajax.ajax()
        a.bind('complete', complete)
        url += '?v=' + str(window.Date.new().getTime())
        a.open('GET', url, True)
        a.send()

    def styler(self):
        pass
