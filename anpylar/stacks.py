###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import browser

__all__ = []

_stacks = {}


def get(name, default=[]):
    if name in _stacks:
        return _stacks[name]

    _stacks[name] = sname = list(default)
    return sname


modules = get('modules')
htmlnodes = get('html', [browser.document.body])
comprender = get('comprender')
