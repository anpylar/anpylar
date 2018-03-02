###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from browser import ajax
from .observable import ObservableSource
from .localdata import LocalData

__all__ = ['Http', 'HttpException']


class HttpException(Exception):
    '''
        A class representing a HTTPRequest error
    '''
    def __init__(self, request):
        super().__init__(request)  # allow storage in args
        self.req = request


class HttpRequest(ObservableSource):
    '''
        A class representing a Future HTTPRequest result.
    '''
    def __init__(self, caller, method, url, headers=None, data=None,
                 fullresp=False):
        # self._caller = caller  # not used
        self._method = method
        self._url = url
        self._headers = headers
        self._data = data
        self._sid = None
        self._fullresp = fullresp

    def _subscribed(self, sid, **kwargs):
        self._sid = sid
        self._req = req = ajax.ajax()
        req.bind('complete', lambda r: self._complete_handler(r, sid))
        req.open(self._method, self._url, True)  # True for async
        if self._headers:
            for k, v in self._headers.items():
                req.set_header(k, v)

        if self._data:
            req.send(self._data)
        else:
            req.send()

    def cancel(self):
        self._req.abort()
        self.on_error(False, self._sid)

    def _complete_handler(self, resp, sid):
        if self._fullresp:
            if resp.status:
                self.on_next(resp, sid)
            else:
                self.on_error(resp, sid)

        elif 200 <= resp.status < 300:
            self.on_next(resp.text, sid)
        else:
            # self.on_error(HttpException(resp), sid)
            self.on_error(resp.text, sid)


class HttpRequestLocalData(ObservableSource):
    '''
        A class representing a Future HTTPRequest result.
    '''
    def __init__(self, caller, method, url, headers=None, data=None,
                 fullresp=False):
        self._caller = caller
        self._method = method
        self._url = url
        self._data = data
        self._headers = headers
        self._fullresp = fullresp

    def _subscribed(self, sid, **kwargs):
        ldata = self._caller._ldata
        if ldata is None:
            for k, v in self._caller._LocalData.items():
                if self._url.startswith(k):
                    self._caller._ldata = ldata = v
                    break

            if ldata is None:
                self.on_error(
                    HttpException('No data for path: {}'.format(self._url))
                )
                return

        response = ldata(self._method, self._url, self._headers, self._data)
        self.on_next(response, sid)


class Http:
    _RequestClass = HttpRequest
    _LocalData = {}

    @classmethod
    def serve(cls, data, index, url='', datacls=LocalData):
        cls._LocalData[url] = datacls(data, index, url)
        cls._RequestClass = HttpRequestLocalData

    _ldata = None

    def __init__(self, url='', headers=None, fullresp=False):
        self._fullresp = fullresp
        self.url = url
        if headers:
            self.headers = {k.lower(): v for k, v in headers.items()}
        else:
            self.headers = {}

    def _send(self, method, url, headers, data, fullresp=False):
        if self.url:
            if url:
                url = '/'.join((self.url, url))
            else:
                url = self.url

        if method == 'GET' and data is not None:
            q = ('='.join((str(k), str(v))) for k, v in data.items())
            qs = '&'.join(q)
            url += '?' + qs

        if headers:
            h = self.headers.copy()
            h.update({k.lower(): v for k, v in headers.items()})
        else:
            h = self.headers  # no need to copy and update

        return self._RequestClass(self, method, url, h, data,
                                  fullresp=self._fullresp)

    def get(self, url='', headers=None, data=None):
        return self._send('GET', url, headers, data)

    def post(self, url='', headers=None, data=None):
        return self._send('POST', url, headers, data)

    def put(self, url='', headers=None, data=None):
        return self._send('PUT', url, headers, data)

    def delete(self, url='', headers=None, data=None):
        return self._send('DELETE', url, headers, data)
