###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import json


__all__ = ['LocalData']


class LocalData:

    def __init__(self, data, index, url):
        # data is a list of dictionaries
        # each dict instance represents the object
        # index is the name of the key which acts as the database index
        self.index = index
        self.url = url

        self.idata = {d[index]: d for d in data}
        self.hidx = max(self.idata.keys())

    def __call__(self, method, url, headers, data):
        dmethod = getattr(self, method.lower())
        url = url.lstrip(self.url)  # remove base url
        return dmethod(url, headers, data)

    def get(self, url, headers, data):
        if data:  # searching
            result = []
            search = data
            for k, v in search.items():
                v = v.lower()
                for d in self.idata.values():
                    val = d[k]
                    if v in val.lower():
                        result.append(d)

            return json.dumps(result)

        if not url:  # return all
            return json.dumps(list(self.idata.values()))

        # return the id (only thing left in url)
        return json.dumps(self.idata.get(int(url), {}))

    def post(self, url, headers, data):
        d = json.loads(data)
        self.hidx = idx = self.hidx + 1  # inc id
        d[self.index] = idx
        self.idata[idx] = d
        return json.dumps(d)

    def put(self, url, headers, data):
        key = int(url)
        d = json.loads(data)
        self.idata[key].update(**d)
        return json.dumps(d)

    def delete(self, url, headers, data):
        key = int(url)
        del self.idata[key]
        return json.dumps({})
