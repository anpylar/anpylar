###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
B = __BRYTHON__

B.DOMNodeDict.select_all = B.DOMNodeDict.select
B.DOMNodeDict.select = B.DOMNodeDict.select_one
