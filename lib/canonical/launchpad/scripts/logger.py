# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0702

"""Logging setup for scripts.

Don't import from this module. Import it from canonical.launchpad.scripts.

Parts of this may be moved into canonical.launchpad somewhere if it is
to be used for non-script stuff.
"""

__metaclass__ = type

# Don't import stuff from this module. Import it from canonical.scripts
__all__ = [
    'DEBUG2',
    'DEBUG3',
    'DEBUG4',
    'DEBUG5',
    'DEBUG6',
    'DEBUG7',
    'DEBUG8',
    'DEBUG9',
    'dummy_logger_options',
    'LaunchpadFormatter',
    'log',
    'logger',
    'logger_options',
    'OopsHandler',
    ]


from contextlib import contextmanager
from cStringIO import StringIO
from datetime import (
    timedelta,
    )
import hashlib
import logging
from logging.handlers import WatchedFileHandler
from optparse import OptionParser
import os.path
import re
import sys
import time
from traceback import format_exception_only

from zope.component import getUtility
from zope.exceptions.log import Formatter

from canonical.config import config
from canonical.launchpad.webapp.errorlog import (
    globalErrorUtility,
    ScriptRequest,
    )
from canonical.librarian.interfaces import (
    ILibrarianClient,
    UploadFailed,
    )
from lp.services.log import loglevels
from lp.services.utils import (
    compress_hash,
    utc_now,
    )

# Reexport our custom loglevels for old callsites. These callsites
# should be importing the symbols from lp.services.log.loglevels
DEBUG2 = loglevels.DEBUG2
DEBUG3 = loglevels.DEBUG3
DEBUG4 = loglevels.DEBUG4
DEBUG5 = loglevels.DEBUG5
DEBUG6 = loglevels.DEBUG6
DEBUG7 = loglevels.DEBUG7
DEBUG8 = loglevels.DEBUG8
DEBUG9 = loglevels.DEBUG9


class OopsHandler(logging.Handler):
    """Handler to log to the OOPS system."""

    def __init__(self, script_name, level=logging.WARN):
        logging.Handler.__init__(self, level)
        # Context for OOPS reports.
        self.request = ScriptRequest(
            [('script_name', script_name), ('path', sys.argv[0])])
        self.setFormatter(LaunchpadFormatter())

    def emit(self, record):
        """Emit a record as an OOPS."""
        try:
            info = record.exc_info
            if info is not None:
                info = sys.exc_info()
            msg = record.getMessage()
            with globalErrorUtility.oopsMessage(msg):
                globalErrorUtility.raising(info, self.request)
        except Exception:
            self.handleError(record)


class LaunchpadFormatter(Formatter):
    """logging.Formatter encoding our preferred output format."""

    def __init__(self, fmt=None, datefmt=None):
        if fmt is None:
            if config.isTestRunner():
                # Don't output timestamps in the test environment
                fmt = '%(levelname)-7s %(message)s'
            else:
                fmt = '%(asctime)s %(levelname)-7s %(message)s'
        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S"
        logging.Formatter.__init__(self, fmt, datefmt)
        # Output should be UTC.
        self.converter = time.gmtime


class LibrarianFormatter(LaunchpadFormatter):
    """A logging.Formatter that stores tracebacks in the Librarian and emits
    a URL rather than emitting the traceback directly.

    The traceback will be emitted as a fallback if the Librarian cannot be
    contacted.

    XXX bug=641103 StuartBishop -- This class should die. Remove it and
    replace with LaunchpadFormatter, fixing the test fallout.
    """

    def formatException(self, ei):
        """Format the exception and store it in the Librian.

        Returns the URL, or the formatted exception if the Librarian is
        not available.
        """
        traceback = LaunchpadFormatter.formatException(self, ei)
        # Uncomment this line to stop exception storage in the librarian.
        # Useful for debugging tests.
        # return traceback
        try:
            librarian = getUtility(ILibrarianClient)
        except LookupError:
            return traceback

        exception_string = ''
        try:
            exception_string = str(ei[1]).encode('ascii')
        except:
            pass
        if not exception_string:
            exception_string = ei[0].__name__

        expiry = utc_now() + timedelta(days=90)
        try:
            filename = compress_hash(hashlib.sha1(traceback)) + '.txt'
            url = librarian.remoteAddFile(
                    filename, len(traceback), StringIO(traceback),
                    'text/plain;charset=%s' % sys.getdefaultencoding(),
                    expires=expiry)
            return ' -> %s (%s)' % (url, exception_string)
        except UploadFailed:
            return traceback
        except Exception:
            # Exceptions raised by the Formatter get swallowed, but we want
            # to know about them. Since we are already spitting out exception
            # information, we can stuff our own problems in there too.
            return '%s\n\nException raised in formatter:\n%s\n' % (
                    traceback,
                    LaunchpadFormatter.formatException(self, sys.exc_info()))


class LogLevelNudger:
    """Callable to adjust the global log level.

    Use instances as callbacks for `optparse`.
    """

    def __init__(self, default, increment=True):
        """Initialize nudger to increment or decrement log level.

        :param default: Default starting level.
        :param increment: Whether to increase the log level (as when
            handling the --verbose option).  If not, will decrease
            instead (as with the --quiet option).
        """
        self.default = default
        self.increment = increment

    def getIncrement(self, current_level):
        """Figure out how much to increment the log level.

        Increment is negative when decreasing log level, of course.
        """
        if self.increment:
            if current_level < 10:
                return 1
            else:
                return 10
        else:
            if current_level <= 10:
                return -1
            else:
                return -10

    def __call__(self, option, opt_str, value, parser):
        """Callback for `optparse` to handle --verbose or --quiet option."""
        current_level = getattr(parser.values, 'loglevel', self.default)
        increment = self.getIncrement(current_level)
        parser.values.loglevel = current_level + increment
        parser.values.verbose = (parser.values.loglevel < self.default)
        # Reset the global log.
        log._log = _logger(parser.values.loglevel, out_stream=sys.stderr)


def define_verbosity_options(parser, default, verbose_callback,
                             quiet_callback):
    """Define the -v and -q options on `parser`."""
    # Only one of these specifies dest and default.  That's because
    # that's enough to make the parser create the option value; there's
    # no need for the other option to specify them as well.
    parser.add_option(
        "-v", "--verbose", dest="loglevel", default=default,
        action="callback", callback=verbose_callback,
        help="Increase stderr verbosity. May be specified multiple times.")
    parser.add_option(
        "-q", "--quiet", action="callback", callback=quiet_callback,
        help="Decrease stderr verbosity. May be specified multiple times.")


def do_nothing(*args, **kwargs):
    """Do absolutely nothing."""


def dummy_logger_options(parser):
    """Add dummy --verbose and --quiet options to `parser`."""
    define_verbosity_options(parser, None, do_nothing, do_nothing)


def logger_options(parser, default=logging.INFO):
    """Add the --verbose and --quiet options to an optparse.OptionParser.

    The requested loglevel will end up in the option's loglevel attribute.
    Note that loglevel is not clamped to any particular range.

    >>> from optparse import OptionParser
    >>> parser = OptionParser()
    >>> logger_options(parser)
    >>> options, args = parser.parse_args(['-v', '-v', '-q', '-qqqqqqq'])
    >>> options.loglevel > logging.CRITICAL
    True
    >>> options.verbose
    False

    >>> parser = OptionParser()
    >>> logger_options(parser)
    >>> options, args = parser.parse_args([])
    >>> options.loglevel == logging.INFO
    True
    >>> options.verbose
    False

    >>> from optparse import OptionParser
    >>> parser = OptionParser()
    >>> logger_options(parser, logging.WARNING)
    >>> options, args = parser.parse_args(['-v'])
    >>> options.loglevel == logging.INFO
    True
    >>> options.verbose
    True

    Cleanup:
    >>> from canonical.testing import reset_logging
    >>> reset_logging()

    As part of the options parsing, the 'log' global variable is updated.
    This can be used by code too lazy to pass it around as a variable.
    """

    # Raise an exception if the constants have changed. If they change we
    # will need to fix the arithmetic
    assert logging.DEBUG == 10
    assert logging.INFO == 20
    assert logging.WARNING == 30
    assert logging.ERROR == 40
    assert logging.CRITICAL == 50

    # Undocumented use of the optparse module
    parser.defaults['verbose'] = False

    define_verbosity_options(
        parser, default,
        LogLevelNudger(default, False), LogLevelNudger(default, True))

    debug_levels = ', '.join([
        v for k, v in sorted(logging._levelNames.items(), reverse=True)
            if isinstance(k, int)])

    def log_file(option, opt_str, value, parser):
        try:
            level, path = value.split(':', 1)
        except ValueError:
            level, path = logging.INFO, value

        if isinstance(level, int):
            pass
        elif level.upper() not in logging._levelNames:
            parser.error(
                "'%s' is not a valid logging level. Must be one of %s" % (
                    level, debug_levels))
        else:
            level = logging._levelNames[level.upper()]

        if not path:
            parser.error("Path to log file not specified")

        path = os.path.abspath(path)
        try:
            open(path, 'a')
        except Exception:
            parser.error("Unable to open log file %s" % path)

        parser.values.log_file = path
        parser.values.log_file_level = level

        # Reset the global log.
        log._log = _logger(parser.values.loglevel, out_stream=sys.stderr)

    parser.add_option(
        "--log-file", type="string", action="callback", callback=log_file,
        metavar="LVL:FILE", default=None,
        help="Send log messages to FILE. LVL is one of %s" % debug_levels)
    parser.set_default('log_file_level', None)

    # Set the global log
    log._log = _logger(default, out_stream=sys.stderr)


def logger(options=None, name=None):
    """Return a logging instance with standard setup.

    options should be the options as returned by an option parser that
    has been initilized with logger_options(parser)

    >>> from optparse import OptionParser
    >>> parser = OptionParser()
    >>> logger_options(parser)
    >>> options, args = parser.parse_args(['-v', '-v', '-q', '-q', '-q'])
    >>> log = logger(options)
    >>> log.debug('Not shown - too quiet')

    Cleanup:

    >>> from canonical.testing import reset_logging
    >>> reset_logging()
    """
    if options is None:
        parser = OptionParser()
        logger_options(parser)
        options, args = parser.parse_args()

    log_file = getattr(options, 'log_file', None)
    log_file_level = getattr(options, 'log_file_level', None)

    return _logger(
        options.loglevel, out_stream=sys.stderr, name=name,
        log_file=log_file, log_file_level=log_file_level)


def reset_root_logger():
    root_logger = logging.getLogger()
    for hdlr in root_logger.handlers[:]:
        hdlr.flush()
        try:
            hdlr.close()
        except KeyError:
            pass
        root_logger.removeHandler(hdlr)


def _logger(
    level, out_stream, name=None,
    log_file=None, log_file_level=logging.DEBUG):
    """Create the actual logger instance, logging at the given level

    if name is None, it will get args[0] without the extension (e.g. gina).
    'out_stream must be passed, the recommended value is sys.stderr'
    """
    if name is None:
        # Determine the logger name from the script name
        name = sys.argv[0]
        name = re.sub('.py[oc]?$', '', name)

    # We install our custom handlers and formatters on the root logger.
    # This means that if the root logger is used, we still get correct
    # formatting. The root logger should probably not be used.
    root_logger = logging.getLogger()

    # reset state of root logger
    reset_root_logger()

    # Make it print output in a standard format, suitable for
    # both command line tools and cron jobs (command line tools often end
    # up being run from inside cron, so this is a good thing).
    hdlr = logging.StreamHandler(out_stream)
    # We set the level on the handler rather than the logger, so other
    # handlers with different levels can be added for things like debug
    # logs.
    root_logger.setLevel(0)
    hdlr.setLevel(level)
    formatter = LibrarianFormatter()
    hdlr.setFormatter(formatter)
    root_logger.addHandler(hdlr)

    # Add an optional aditional log file.
    if log_file is not None:
        handler = WatchedFileHandler(log_file, encoding="UTF8")
        handler.setFormatter(formatter)
        handler.setLevel(log_file_level)
        root_logger.addHandler(handler)

    # Create our logger
    logger = logging.getLogger(name)

    # Set the global log
    log._log = logger

    # Inform the user the extra log file is in operation.
    if log_file is not None:
        log.info(
            "Logging %s and higher messages to %s" % (
                logging.getLevelName(log_file_level), log_file))

    return logger


class _LogWrapper:
    """Changes the logger instance.

    Other modules will do 'from canonical.launchpad.scripts import log'.
    This wrapper allows us to change the logger instance these other modules
    use, by replacing the _log attribute. This is done each call to logger()
    """

    def __init__(self, log):
        self._log = log

    def __getattr__(self, key):
        return getattr(self._log, key)

    def __setattr__(self, key, value):
        if key == '_log':
            self.__dict__['_log'] = value
            return value
        else:
            return setattr(self._log, key, value)

    @contextmanager
    def use(self, log):
        """Temporarily use a different `log`."""
        self._log, log = log, self._log
        try:
            yield
        finally:
            self._log = log

    def shortException(self, msg, *args):
        """Like Logger.exception, but does not print a traceback."""
        exctype, value = sys.exc_info()[:2]
        report = ''.join(format_exception_only(exctype, value))
        # _log.error interpolates msg, so we need to escape % chars
        msg += '\n' + report.rstrip('\n').replace('%', '%%')
        self._log.error(msg, *args)


log = _LogWrapper(logging.getLogger())
