###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from .future import Future, CatchError
from .timer import call_delayed


__all__ = ['Promise', 'Future']


class Promise(Future):
    '''
    A Promise modelled after the Promises/A+ standard
    '''
    def __init__(self, executor=None, reject=None):
        '''This creates a Promise:

          - if ``reject`` is ``None``, then executor is called with
            ``executor(promise_resolve, promise_reject)`` where reject and
            resolve are the callables to be invoked to indicate if the promise
            has to be resolved or rejected.

          - if ``reject`` is not ``None`` the invocation will be:

            - ``executor(promise_resolve)``
            - ``reject(promise_reject)``

        If the execution during creation raises an ``Exception``, the promise
        will be immediately rejected
        '''
        super().__init__()
        if executor:
            try:
                if reject is None:
                    executor(self._resolve, self._reject)
                else:
                    executor(self._resolve)
                    reject(self._reject)

            except Exception as e:
                self.set_exception(e)

    def _resolve(self, result, timeout=None):
        if isinstance(result, Future):
            self._chain(result, timeout)  # add next to chain
        elif timeout:
            call_delayed(timeout, lambda: self.set_result(result))
        else:
            self.set_result(result)

        return self

    def _reject(self, exception, timeout=None):
        if isinstance(exception, Future):
            return self._chain(exception, timeout)  # add next to chain
        elif timeout:
            call_delayed(timeout, lambda: self.set_exception(exception))
        else:
            self.set_exception(exception)

        return self

    @staticmethod
    def resolve(value):
        '''This creates a Promise which is immediately resolved with
        ``value``'''
        return Promise(lambda resolve, reject: resolve(value))

    @staticmethod
    def reject(value):
        '''This creates a Promise which is immediately rejected with
        ``value``'''
        return Promise(lambda resolve, reject: reject(value))

    @staticmethod
    def all(*promises):
        '''This creates a Promise which awaits the resolution of all promises
        passed as arguments. Anything which is not a *promise* is
        considered to be immediately resolved and the face value taken as the
        resolution value

        If any of the promises is rejected, the promise will also be rejected
        with the value of the rejected promise.
        '''
        if not promises:
            return Promise.resolve([])

        count = [None] * len(promises)
        results = count[:]  # copy

        # Promise that does nothing to start with
        retpromise = Promise()

        def thener(result, i):
            results[i] = result
            count.pop()
            if not count:  # all have delivered
                retpromise._resolve(results)

        def catcher(error):
            retpromise._reject(error)

        for i, promise in enumerate(promises):
            if isinstance(promise, Promise):
                promise \
                    .then(lambda x, i=i: thener(x, i)) \
                    .catch(catcher)
            else:
                count.pop()
                results[i] = promise

        if not count:  # no promises in iterable, resolve immediately
            return Promise.resolve(results)

        return retpromise  # await resolution

    @staticmethod
    def race(*promises):
        '''This creates a Promise which waits until one of the ``promises``
        passed as arguments ``*promises`` is resolved/rejected and takes the
        corresponding value for resolution/rejection

        If no arguments are given, the promise will wait forever (because there
        is no meaningful value for either resolution or rejection)

        If any of the arguments is not a promise, its value will be immediately
        used for resolving the returned promise.

        Returns a promise
        '''
        # Promise that does nothing to start with
        retpromise = Promise()

        def thener(result):
            if not retpromise.done():
                retpromise._resolve(result)

        def catcher(error):
            if not retpromise.done():
                retpromise._reject(error)

        to_wait = []

        for promise in promises:
            if isinstance(promise, Promise):
                if promise.cancelled():
                    continue  # no need to wait on this

                if promise.done():
                    try:
                        result = promise.result()
                    except CatchError:
                        retpromise._reject(promise.exception())
                    else:
                        retpromise._resolve(result)

                    # promise is done and has result/exception
                    to_wait = []  # avoid waiting on any other promise
                    break  # bail out

                # else wait for the promise
                to_wait.append(promise)
            else:
                # non-promise, resolve and go
                retpromise._resolve(promise)
                to_wait = []  # avoid waiting on any promise
                break  # bail out

        for promise in to_wait:  # to_wait may be empty if resolved/rejected
            promise.then(thener).catch(catcher)

        return retpromise  # return the promise to wait on

    def then(self, then, catch=None):
        '''Takes 1 or 2 arguments.

          - If only the argument ``then`` is provided, it will be invoked with
            the resolution value if the promise is resolved

          - If ``catch`` is provided, it will be invoked with the rejection
            value if the promise is rejected

        It returns a promise, to allow chaining
        '''
        promise = Promise()  # return a standard promise

        def done_callback(fut):
            if fut.cancelled():
                self.cancel()  # copy state
                return

            try:
                result = fut.result()  # it's done, we can retrieve
                if then:
                    result = then(result)

                if isinstance(result, Future):
                    promise._chain(result)  # add next to chain
                else:
                    promise.set_result(result)  # end of chain, copy

            except (CatchError, Exception) as result:
                if isinstance(result, CatchError):
                    result = result.args[0]
                if catch:
                    try:
                        result = catch(result)
                    except Exception as result:
                        pass

                    if not isinstance(result, Exception):
                        promise.set_result(result)
                    else:
                        promise.set_exception(result)
                else:
                    promise.set_exception(result)

        self.add_done_callback(done_callback)
        return promise

    def catch(self, catch):
        '''It invokes internally ``then(None, catch)`` to register the callable
        ``catch`` for invocation in case the promise is rejected

        It returns a promise, to allow chaining
        '''
        return self.then(None, catch)

    def _chain(self, promise, timeout=None):
        def done_callback(fut):
            if fut.cancelled():
                self.cancel()  # copy state
                return

            try:
                result = fut.result()  # it's done, we can retrieve
                if isinstance(result, Future):
                    self._chain(result, timeout)  # add next to chain

                elif timeout is not None:
                    call_delayed(timeout, lambda: self.set_result(result))
                else:
                    self.set_result(result)

            except Exception as e:
                if timeout is not None:
                    call_delayed(timeout, lambda: self.set_exception(e))
                else:
                    self.set_exception(e)  # end of chain ... exception

        promise.add_done_callback(done_callback)
