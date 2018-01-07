;function anpylar_load($B) {
    ;(function($B){
        var _b_ = $B.builtins

        function parent_package(mod_name) {
            var parts = mod_name.split('.')
            parts.pop()
            return parts.join('.')
        }

        function sfs_hook(path, vfs) {
            if (path.substr(-1) == '/')
                path = path.slice(0, -1)

            // it doesn't really make sense to check for a extension, because we
            // know the code is wrapped in a variable which is available
            var ext = path.substr(-7)
            if(ext != '.vfs.js')
                throw _b_.ImportError('VFS file URL must end with .vfs.js extension')

            self = {__class__: sfs_hook.$dict, path: path}
            sfs_hook.$dict.load_vfs(self, vfs)
            return self
        }

        sfs_hook.__class__ = $B.$factory

        sfs_hook.$dict = {
            $factory: sfs_hook,
            __class__: $B.$type,
            __name__: 'VFSAutoPathFinder',

            load_vfs: function(self, vfs) {
                self.vfs = vfs
                $B.path_importer_cache[self.path + '/'] = self
            },
            find_spec: function(self, fullname, module) {
                var stored = self.vfs[fullname]
                if (stored === undefined)
                    return _b_.None

                var is_package = stored[2]
                return {
                    name : fullname,
                    // newspec function in original does simply __class__ ...
                    __class__: $B.$ModuleDict,
                    loader: $B.imported['_importlib'].VFSFinder,  // finder_VFS
                    // FIXME : Better origin string.
                    origin: self.path + '#' + fullname,
                    // FIXME: Namespace packages ?
                    submodule_search_locations: is_package ? [self.path] : _b_.None,
                    loader_state: {stored: stored},
                    // FIXME : Where exactly compiled module is stored ?
                    cached: _b_.None,
                    parent: is_package ? fullname : parent_package(fullname),
                    has_location: _b_.True
                }
            },
            invalidate_caches: function(self) {
            }
        }

        sfs_hook.$dict.__mro__ = [_b_.object.$dict]

        $B.imported['_importlib'].VFSAutoPathFinder = sfs_hook
    })($B)

    // define __ANPYLAR__ if not defined
    if(window.__ANPYLAR__ === undefined)
        window.__ANPYLAR__ = {autoload: []}

    // autoload packages if any has registered
    var autoload = window.__ANPYLAR__.autoload
    if(autoload !== undefined)
        for(var i=0; i < autoload.length; i++)
            autoload[i]($B)

    var $scripts = document.getElementsByTagName('script'),
        slen = $scripts.length

    for(var i=0, found=false; i < slen && !found; i++) {
        var t = $scripts[i].type
        if(t == 'text/python' || t == 'text/python3')
            found = true
    }
    if(!found) {
        var script = document.createElement("script")
        script.type = 'text/python'
        script.innerHTML = 'import app; app.AppModule()'
        document.getElementsByTagName('head')[0].appendChild(script)
    }
    $B.brython()
};

// BRYTHON must already be in place
var $al = function() {anpylar_load(__BRYTHON__)}
if(document.readyState === 'interactive')
    $al()  // if async ... the DOM will probably be there
else
    window.addEventListener('DOMContentLoaded', $al, true)
