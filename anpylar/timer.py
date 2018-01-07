###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import browser.timer as timer


__all__ = ['call_soon', 'call_delayed', 'call_cancel']


def call_soon(cb, *args, **kwargs):
    if not args and not kwargs:
        return timer.set_timeout(cb, 0)

    return timer.set_timeout(lambda: cb(*args, **kwargs), 0)


def call_delayed(tout, cb, *args, **kwargs):
    if not args and not kwargs:
        return timer.set_timeout(cb, tout)

    return timer.set_timeout(lambda: cb(*args, **kwargs), tout)


def call_cancel(t):
    return timer.clear_timeout(t)
