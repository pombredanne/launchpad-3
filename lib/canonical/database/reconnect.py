
# TODO:
#  - geometric backoff to ~ 1 minute.
#  - after that, log message every minute ("error" level message)

import psycopg
import time

__all__ = ['install', 'uninstall', 'AlreadyInstalledError', 'NotInstalledError']

_orig_connect = None

def install():
    global _orig_connect
    if _orig_connect is not None:
        raise AlreadyInstalledError, 'reconnector already installed'
    _orig_connect = psycopg.connect
    psycopg.connect = _connect

def uninstall():
    if _orig_connect is None:
        raise NotInstalledError, 'reconnector not installed'
    psycopg.connect = _orig_connect


def _connect(*args, **kwargs):
    return ConnectionWrapper(_orig_connect, *args, **kwargs)


class AlreadyInstalledError(Exception):
    pass


class NotInstalledError(Exception):
    pass


class ConnectionWrapper:
    orig = None
    closed = False
    def __init__(self, connectFn, *args, **kwargs):
        self.connectFn = connectFn
        self.args = args
        self.kwargs = kwargs
        self._reconnect()

    def __getattr__(self, name):
        return getattr(self.orig, name)

    def cursor(self, *args, **kwargs):
        return CursorWrapper(self, *args, **kwargs)

    def close(self):
        self.closed = True
        return self.orig.close()

    def _reconnect(self):
        if self.closed:
            return # Don't reconnect if we have been explicitly closed
        if self.orig is not None:
            self.orig.close()
        self.orig = self.connectFn(*self.args, **self.kwargs)


class CursorWrapper:
    def __init__(self, connection, *args, **kwargs):
        self.connection = connection
        self.args = args
        self.kwargs = kwargs
        self._reconnect()

    def __getattr__(self, name):
        return getattr(self.orig, name)

    def execute(self, *args, **kwargs):
        while True:
            try:
                return self.orig.execute(*args, **kwargs)
            except (psycopg.ProgrammingError, psycopg.OperationalError), e:
                msg = e.args[0]
                if not (msg.startswith(
                            'server closed the connection unexpectedly') or
                        msg.startswith('could not connect to server')):
                    raise
            except psycopg.InterfaceError, e:
                # Our cursor might still be pointing to a connection closed
                # during connection._reconnect.  Catch this and retry - unless
                # the connection really was closed explicitly.
                msg = e.args[0]
                if msg != 'already closed' or self.connection.closed:
                    raise

            # Avoid looping insanely fast.
            time.sleep(0.1)

            try:
                self._reconnect()
            except psycopg.OperationalError:
                pass

    def _reconnect(self):
        try:
            # Try make a new cursor...
            self.orig = self.connection.orig.cursor(*self.args, **self.kwargs)
            # ...and check that it really works!
            self.orig.execute('select 1;')
        except psycopg.Error:
            # If it fails, reconnect the connection, and try again.
            self.connection._reconnect()
            self.orig = self.connection.orig.cursor(*self.args, **self.kwargs)

