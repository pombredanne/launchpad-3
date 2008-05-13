# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Helpers to time out external operations."""

__metaclass__ = type
__all__ = [
    "TimeoutError",
    "with_timeout",
    ]


from threading import Thread


class TimeoutError(Exception):
    """Exception raised when a function doesn't complete within time."""


class ThreadCapturingResult(Thread):
    """Thread subclass that saves the return value of its target."""

    def __init__(self, target, args, kwargs, **opt):
        super(ThreadCapturingResult, self).__init__(**opt)
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """See `Thread`."""
        self.result = self.target(*self.args, **self.kwargs)


class with_timeout:
    """Make sure the decorated function doesn't exceed a time out.

    This will execute the function in a separate thread. If the function
    doesn't complete in the timeout, a TimeoutError is raised. The clean-up
    function will be called to "stop" the thread. (If it's possible to do so.)
    """

    def __init__(self, cleanup=None, timeout=None):
        """Creates the function decorator.

        :param cleanup: That may be a callable or a string. If it's a string,
            a method under that name will be looked up. That callable will
            be called if the timeout is exceeded.
        :param timeout: The number of seconds to wait for. Defaults is 5.
        """
        self.cleanup = cleanup
        self.timeout = timeout

    def __call__(self, f):
        """Wraps the method."""
        def call_with_timeout(*args, **kwargs):
            t = ThreadCapturingResult(f, args, kwargs)
            t.start()
            t.join(self.timeout)
            if t.isAlive():
                raise TimeoutError("timeout exceeded.")
            return t.result

        return call_with_timeout
