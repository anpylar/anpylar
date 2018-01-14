###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################


class observable:
    # log errors if no on_error has been provided
    log_error = True
    # raise errors as exception if no on_error has been provided
    raise_error = False
    # log as soon as it happens
    log_error_early = False


class router:
    # log if waiting for components to render failes
    log_comprender = True


class module:
    loading_overlay_id = 'anpylar-loading-overlay'
