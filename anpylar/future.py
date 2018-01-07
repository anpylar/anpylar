###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
from .timer import call_soon


__all__ = ['Future']


class InvalidStateError(Exception):
    pass


class CancelledError(Exception):
    pass


class TimeoutError(Exception):
    pass


class CatchError(Exception):
    pass


class Future:
    """
        A class representing the future result of an async action.
        Implementations should override the :method:`start` method
        which should start the asynchronous operation. The class will
        typically register a handler to be run when the operation finishes.
        This handler then needs to call the base :method:`_finish` method
        providing it with the :parameter:`result` parameter and
        :parameter:`status` (which should either be ``Promise.STATUS_FINISHED``
        in case the operation finished successfully or ``Promise.STATUS_ERROR``
        if an error happened).
    """
    STATUS_STARTED = 0
    STATUS_CANCELED = 1
    STATUS_FINISHED = 2
    STATUS_ERROR = 3

    def __init__(self):
        # self._loop = get_event_loop()
        self._status = Future.STATUS_STARTED
        self._result = None
        self._exception = None
        self._callbacks = []

    def _schedule_callbacks(self):
        cbs = self._callbacks[:]  # copy list content
        self._callbacks = []
        for cb in cbs:
            # self._loop.call_soon(cb, self)
            call_soon(cb, self)

    def cancel(self):
        """Cancel the future and schedule callbacks.

        If the future is already done or cancelled, return False. Otherwise,
        change the future’s state to cancelled, schedule the callbacks and
        return True.

        """
        if self._status != Future.STATUS_STARTED:
            return False
        self._status = Future.STATUS_CANCELED
        self._schedule_callbacks()
        return True

    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._status == Future.STATUS_CANCELED

    def done(self):
        """Return True if the future is done.

        Done means either that a result / exception are available, or that the
        future was cancelled.

        """
        return self._status != Future.STATUS_STARTED

    def result(self):
        """Return the result this future represents.

        If the future has been cancelled, raises CancelledError. If the
        future’s result isn’t yet available, raises InvalidStateError. If the
        future is done and has an exception set, this exception is raised.

        """
        if self._status == Future.STATUS_STARTED:
            raise InvalidStateError()
        if self._status == Future.STATUS_CANCELED:
            raise CancelledError()
        if self._status == Future.STATUS_ERROR:
            raise CatchError(self._exception)
        return self._result

    def exception(self):
        """Return the exception that was set on this future.

        The exception (or None if no exception was set) is returned only if the
        future is done. If the future has been cancelled, raises
        CancelledError. If the future isn’t done yet, raises InvalidStateError.

        """
        if self._status == Future.STATUS_STARTED:
            raise InvalidStateError()
        if self._status == Future.STATUS_CANCELED:
            raise CancelledError()
        if self._status == Future.STATUS_ERROR:
            return self._exception

    def add_done_callback(self, fn):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon().

        Use functools.partial to pass parameters to the callback. For example,
        fut.add_done_callback(functools.partial(print, "Future:", flush=True))
        will call print("Future:", fut, flush=True).

        """
        if self.done():
            # self._loop.call_soon(fn,self)
            call_soon(fn, self)
        else:
            self._callbacks.append(fn)

    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the “call when done” list.

        Returns the number of callbacks removed.

        """
        lcbs = len(self._callbacks)
        self._callbacks = cbs = [cb for cb in self._callbacks if cb != fn]
        return lcbs - len(cbs)

    def set_result(self, result, noexceptions=False):
        """Mark the future done and set its result.

        If the future is already done when this method is called, raises
        InvalidStateError.

        """
        if self._status != Future.STATUS_STARTED:
            if noexceptions:
                return
            raise InvalidStateError()
        self._result = result
        self._status = Future.STATUS_FINISHED
        self._schedule_callbacks()

    def set_exception(self, exception, noexceptions=False):
        """Mark the future done and set an exception.

        If the future is already done when this method is called, raises
        InvalidStateError.

        """
        if self._status != Future.STATUS_STARTED:
            if noexceptions:
                return
            raise InvalidStateError()
        self._exception = exception
        self._status = Future.STATUS_ERROR
        self._schedule_callbacks()
