# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Simple loggers."""

__metaclass__ = type
__all__ = [
    'BufferLogger',
    'DevNullLogger',
    'FakeLogger',
    ]

from StringIO import StringIO
import sys
import traceback

from lp.services.log import loglevels


LEVEL_PREFIXES = dict(
    (debug_level, "DEBUG%d" % (1 + debug_level - loglevels.DEBUG))
    for debug_level in xrange(loglevels.DEBUG9, loglevels.DEBUG))

LEVEL_PREFIXES.update({
    None: 'log>',
    loglevels.DEBUG: 'DEBUG',
    loglevels.INFO: 'INFO',
    loglevels.WARNING: 'WARNING',
    loglevels.ERROR: 'ERROR',
    loglevels.CRITICAL: 'CRITICAL',
})


class FakeLogger:
    """Emulates a proper logger, just printing everything out the given file.
    """

    loglevel = loglevels.DEBUG

    def __init__(self, output_file=None):
        """The default output_file is sys.stdout."""
        self.output_file = output_file

    def setLevel(self, loglevel):
        self.loglevel = loglevel

    def getEffectiveLevel(self):
        return self.loglevel

    def _format_message(self, msg, *args):
        if not isinstance(msg, basestring):
            msg = str(msg)
        # To avoid type errors when the msg has % values and args is empty,
        # don't expand the string with empty args.
        if len(args) > 0:
            msg %= args
        return msg

    def message(self, level, msg, *stuff, **kw):
        if level < self.loglevel:
            return

        # We handle the default output file here because sys.stdout
        # might have been reassigned. Between now and when this object
        # was instantiated.
        if self.output_file is None:
            output_file = sys.stdout
        else:
            output_file = self.output_file
        prefix = LEVEL_PREFIXES.get(level, "%d>" % level)
        print >> output_file, prefix, self._format_message(msg, *stuff)

        if 'exc_info' in kw:
            traceback.print_exc(file=output_file)

    def log(self, level, *stuff, **kw):
        self.message(level, *stuff, **kw)

    def warning(self, *stuff, **kw):
        self.message(loglevels.WARNING, *stuff, **kw)

    warn = warning

    def error(self, *stuff, **kw):
        self.message(loglevels.ERROR, *stuff, **kw)

    exception = error

    def critical(self, *stuff, **kw):
        self.message(loglevels.CRITICAL, *stuff, **kw)

    fatal = critical

    def info(self, *stuff, **kw):
        self.message(loglevels.INFO, *stuff, **kw)

    def debug(self, *stuff, **kw):
        self.message(loglevels.DEBUG, *stuff, **kw)


class DevNullLogger(FakeLogger):
    """A logger that drops all messages."""

    def message(self, *args, **kwargs):
        """Do absolutely nothing."""


class BufferLogger(FakeLogger):
    """A logger that logs to a StringIO object."""

    def __init__(self):
        super(BufferLogger, self).__init__(StringIO())

    def getLogBuffer(self):
        """Return the existing log messages."""
        return self.output_file.getvalue()

    def clearLogBuffer(self):
        """Clear out the existing log messages."""
        self.output_file = StringIO()

    def getLogBufferAndClear(self):
        """Return the existing log messages and clear the buffer."""
        messages = self.getLogBuffer()
        self.clearLogBuffer()
        return messages
