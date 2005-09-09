# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Library functions for use in all scripts.

"""
__metaclass__ = type

__all__ = [
    'executezcmlforscripts',
    'logger_options',
    'logger',
    'log',
    'db_options',
    ]

import os
import threading
import atexit
import sys
import re
import logging
import time
from optparse import OptionParser

import zope.app.appsetup
import zope.app.mail.delivery
from zope.configuration.config import ConfigurationMachine
from zope.configuration.config import GroupingContextDecorator
from zope.security.management import setSecurityPolicy
from zope.security.simplepolicies import PermissiveSecurityPolicy

from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy

from canonical import lp
from canonical.config import config

# XXX: We should probably split out all the stuff in this directory that
# doesn't rely on Zope and migrate it to canonical/scripts.
# -- StuartBishop 2005-06-02

# XXX: This is a total mess.  I need to work out what this all means.
# -- SteveAlexander, 2005-04-11

class NullItem:
    def __init__(self, context, handler, info, *argdata):
        newcontext = GroupingContextDecorator(context)
        newcontext.info = info
        self.context = newcontext
        self.handler = handler
        self.argdata = argdata

    def contained(self, name, data, info):
        return NullItem(self.context, None, None)

    def finish(self):
        pass


def NullFactory(context, data, info):
    return NullItem(context, data, info)


class CustomMachine(ConfigurationMachine):

    def factory(self, context, name):
        # Hackery to remove 'browser:xxx' directives from being processed.
        # This is needed to avoid page directives, which screw up when you
        # parse the zcml from a cwd that isn't the launchpad root.
        # XXX: I added a workaround so that browser:url directives get
        #      processed, though. SteveA said he will fix it better when
        #      he lands the navigation stuff.
        #      -- Bjorn Tillenius, 2005-07-14
        ns, simplename = name
        if ns == u'http://namespaces.zope.org/browser' and simplename != 'url':
            return NullFactory
        else:
            f = ConfigurationMachine.factory(self, context, name)
            return f


def execute_zcml_for_scripts(use_web_security=False):
    """Execute the zcml rooted at launchpad/script.zcml
    
    If use_web_security is True, the same security policy as the web
    application uses will be used. Otherwise everything protected by a
    permission is allowed, and everything else denied.
    """
    scriptzcmlfilename = os.path.normpath(
        os.path.join(os.path.dirname(__file__),
                     os.pardir, os.pardir, os.pardir, os.pardir,
                     'script.zcml'))

    scriptzcmlfilename = os.path.abspath(scriptzcmlfilename)
    from zope.configuration import xmlconfig

    # Hook up custom component architecture calls
    zope.app.component.hooks.setHooks()

    # Load server-independent site config
    context = CustomMachine()
    xmlconfig.registerCommonDirectives(context)
    context = xmlconfig.file(scriptzcmlfilename, execute=True, context=context)

    if use_web_security:
        setSecurityPolicy(LaunchpadSecurityPolicy)
    else:
        setSecurityPolicy(PermissiveSecurityPolicy)

    # Register atexit handler to kill off mail delivery daemon threads, and
    # thus avoid spew at exit.  See:
    # http://mail.python.org/pipermail/python-list/2003-October/192044.html
    # http://mail.python.org/pipermail/python-dev/2003-September/038151.html
    # http://mail.python.org/pipermail/python-dev/2003-September/038153.html

    def kill_queue_processor_threads():
        for thread in threading.enumerate():
            if isinstance(thread, zope.app.mail.delivery.QueueProcessorThread):
                thread.stop()
                thread.join(30)
                if thread.isAlive():
                    raise RuntimeError("QueueProcessorThread did not shut down")
    atexit.register(kill_queue_processor_threads)

    # This is a convenient hack to set up a zope interaction, before we get
    # the proper API for having a principal / user running in scripts.
    # The script will have full permissions because of the
    # PermissiveSecurityPolicy set up in script.zcml.
    from canonical.launchpad.ftests import login
    login('launchpad.anonymous')


def logger_options(parser, default=logging.INFO):
    """Add the --verbose and --quiet options to an optparse.OptionParser.

    The requested loglevel will end up in the option's loglevel attribute.

    >>> from optparse import OptionParser
    >>> parser = OptionParser()
    >>> logger_options(parser)
    >>> options, args = parser.parse_args(['-v', '-v', '-q', '-q', '-q'])
    >>> options.loglevel == logging.WARNING
    True

    >>> options, args = parser.parse_args([])
    >>> options.loglevel == logging.INFO
    True

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

    def counter(option, opt_str, value, parser, inc):
        parser.values.loglevel = (
                getattr(parser.values, 'loglevel', default) + inc
                )
        # Reset the global log
        global log
        log._log = _logger(parser.values.loglevel)

    parser.add_option(
            "-v", "--verbose", dest="loglevel", default=default,
            action="callback", callback=counter, callback_args=(-10, ),
            help="Increase verbosity. May be specified multiple times."
            )
    parser.add_option(
            "-q", "--quiet",
            action="callback", callback=counter, callback_args=(10, ),
            help="Decrease verbosity. May be specified multiple times."
            )

    # Set the global log
    global log
    log._log = _logger(default)


def logger(options=None, name=None):
    """Return a logging instance with standard setup.

    options should be the options as returned by an option parser that
    has been initilized with logger_options(parser)

    >>> from optparse import OptionParser
    >>> parser = OptionParser()
    >>> logger_options(parser)
    >>> options, args = parser.parse_args(['-v', '-v', '-q', '-q', '-q'])
    >>> log = logger(options)
    >>> log.debug("Not shown - I'm too quiet")
    """
    if options is None:
        parser = OptionParser()
        logger_options(parser)
        options, args = parser.parse_args()

    return _logger(options.loglevel, name)


def _logger(level, name=None):
    """Create the actual logger instance, logging at the given level

    if name is None, it will get args[0] without the extension (e.g. gina).
    """

    if name is None:
        # Determine the logger name from the script name
        name = sys.argv[0]
        name = re.sub('.py[oc]?$', '', name)

    # Clamp the loglevel
    if level < logging.DEBUG:
        level = logging.DEBUG
    elif level > logging.CRITICAL:
        level = logging.CRITICAL

    # Create our logger
    logger = logging.getLogger(name)

    # Trash any existing handlers
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)

    # Make it print output in a standard format, suitable for 
    # both command line tools and cron jobs (command line tools often end
    # up being run from inside cron, so this is a good thing).
    hdlr = logging.StreamHandler(strm=sys.stderr)
    # TODO: Hmm... not sure about the '-7s' daf suggested. Maybe it will
    # grow on me -- StuartBishop 20050705
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-7s %(message)s',
        # Put date back if we need it, but I think just time is fine and
        # saves space.
        datefmt="%H:%M:%S",
        )
    formatter.converter = time.gmtime # Output should be UTC
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(level)

    global log
    log._log = logger

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

log = _LogWrapper(logging.getLogger())


def db_options(parser):
    """Add and handle default database connection options on the command line

    Adds -d (--database), -H (--host) and -U (--user)

    Parsed options provide dbname, dbhost and dbuser attributes.

    Generally, scripts will not need this and should instead pull their
    connection details from launchpad.config.config. The database setup and
    maintenance tools cannot do this however.

    dbname and dbhost are also propagated to config.dbname and config.dbhost.
    dbname, dbhost and dbuser are also propagated to lp.dbname, lp.dbhost
    and lp.dbuser. This ensures that all systems will be using the requested
    connection details.

    To test, we first need to store the current values so we can reset them
    later.

    >>> dbname, dbhost, dbuser = lp.dbname, lp.dbhost, lp.dbuser

    Ensure that command line options propagate to where we say they do

    >>> parser = OptionParser()
    >>> db_options(parser)
    >>> options, args = parser.parse_args(
    ...     ['--dbname=foo', '--host=bar', '--user=baz'])
    >>> options.dbname, lp.dbname, config.dbname
    ('foo', 'foo', 'foo')
    >>> (options.dbhost, lp.dbhost, config.dbhost)
    ('bar', 'bar', 'bar')
    >>> (options.dbuser, lp.dbuser)
    ('baz', 'baz')

    Make sure that the default user is None

    >>> parser = OptionParser()
    >>> db_options(parser)
    >>> options, args = parser.parse_args([])
    >>> options.dbuser, lp.dbuser
    (None, None)

    Reset config

    >>> lp.dbname, lp.dbhost, lp.dbuser = dbname, dbhost, dbuser
    """
    def dbname_callback(option, opt_str, value, parser):
        parser.values.dbname = value
        config.dbname = value
        lp.dbname = value

    parser.add_option(
            "-d", "--dbname", action="callback", callback=dbname_callback,
            type="string", dest="dbname", default=lp.dbname,
            help="PostgreSQL database to connect to."
            )

    def dbhost_callback(options, opt_str, value, parser):
        parser.values.dbhost = value
        config.dbhost = value
        lp.dbhost = value

    parser.add_option(
             "-H", "--host", action="callback", callback=dbhost_callback,
             type="string", dest="dbhost", default=lp.dbhost,
             help="Hostname or IP address of PostgreSQL server."
             )

    def dbuser_callback(options, opt_str, value, parser):
        parser.values.dbuser = value
        lp.dbuser = value

    parser.add_option(
             "-U", "--user", action="callback", callback=dbuser_callback,
             type="string", dest="dbuser", default=None,
             help="PostgreSQL user to connect as."
             )

    # The default user is None for scripts (which translates to 'connect
    # as a PostgreSQL user named the same as the current Unix user').
    # If the -U option was not given on the command line, our callback is
    # never called so we need to set this different default here.
    # Same for dbhost
    lp.dbuser = None
    lp.dbhost = None
