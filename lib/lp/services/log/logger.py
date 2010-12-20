# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Simple loggers."""

__metaclass__ = type
__all__ = [
    'BufferLogger',
    'DevNullLogger',
    'FakeLogger',
    ]

from cStringIO import StringIO
import sys
import traceback


class FakeLogger:
    """Emulates a proper logger, just printing everything out the given file.
    """

    def __init__(self, output_file=None):
        """The default output_file is sys.stdout."""
        self.output_file = output_file

    def message(self, prefix, msg, *stuff, **kw):
        # We handle the default output file here because sys.stdout
        # might have been reassigned. Between now and when this object
        # was instantiated.
        if self.output_file is None:
            output_file = sys.stdout
        else:
            output_file = self.output_file
        print >> output_file, prefix, str(msg) % stuff

        if 'exc_info' in kw:
            traceback.print_exc(file=output_file)

    def log(self, *stuff, **kw):
        self.message('log>', *stuff, **kw)

    def warning(self, *stuff, **kw):
        self.message('WARNING', *stuff, **kw)

    warn = warning

    def error(self, *stuff, **kw):
        self.message('ERROR', *stuff, **kw)

    exception = error

    def critical(self, *stuff, **kw):
        self.message('CRITICAL', *stuff, **kw)

    fatal = critical

    def info(self, *stuff, **kw):
        self.message('INFO', *stuff, **kw)

    def debug(self, *stuff, **kw):
        self.message('DEBUG', *stuff, **kw)


class DevNullLogger(FakeLogger):
    """A logger that drops all messages."""

    def message(self, *args, **kwargs):
        """Do absolutely nothing."""


class BufferLogger(FakeLogger):
    """A logger that logs to a StringIO object."""

    def __init__(self):
        self.buffer = StringIO()

    def message(self, prefix, msg, *stuff, **kw):
        self.buffer.write('%s: %s\n' % (prefix, str(msg) % stuff))

        if 'exc_info' in kw:
            exception = traceback.format_exception(*sys.exc_info())
            for thing in exception:
                for line in thing.splitlines():
                    self.log(line)

    def getLogBuffer(self):
        """Return the existing log messages."""
        return self.buffer.getvalue()

    def clearLogBuffer(self):
        """Clear out the existing log messages."""
        self.buffer = StringIO()

    def getLogBufferAndClear(self):
        """Return the existing log messages and clear the buffer."""
        messages = self.getLogBuffer()
        self.clearLogBuffer()
        return messages
