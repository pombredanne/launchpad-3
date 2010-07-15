# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Storm tracers for debugging."""

__metaclass__ = type
__all__ = [
    'BaseTracer',
    'CountAllTracer',
    'StderrDebugTracer',
    ]


import sys
import storm.tracer


class BaseTracer:
    """Base class for all tracers."""

    def __init__(self):
        # A flag indicating whether tracing should be enabled or not.
        self.trace = False

    def install(self, only=False):
        """Install this tracer.

        :param only: When True, remove all existing tracers before adding this
            one.
        :type only: boolean
        """
        if only:
            storm.tracer.remove_all_tracers()
        storm.tracer.install_tracer(self)

    def uninstall(self):
        """Uninstall all tracers of this instance's type."""
        storm.tracer.remove_tracer_type(type(self))

    # The trace API
    def connection_raw_execute(self, *args):
        pass

    def connection_raw_execute_error(self, *args):
        pass

    def set_statement_timeout(self, *args):
        pass
    


class CountAllTracer(BaseTracer):
    """A counter of all SQL statements executed by Storm."""

    def __init__(self):
        super(CountAllTracer, self).__init__()
        self.count = 0

    def connection_raw_execute(self, *args):
        if self.trace:
            self.count += 1


class StderrDebugTracer(BaseTracer):
    """Print all executed SQL statements to a stream.

    By default, print to the real stderr (e.g. not a possibly
    doctest-redirected stderr).
    """

    def __init__(self, stream=None):
        super(StderrDebugTracer, self).__init__()
        if stream is None:
            self.stream = sys.__stderr__
        else:
            self.stream = stream

    def connection_raw_execute(self, connection, cursor, statement, params):
        if self.trace:
            print >> self.stream, statement
