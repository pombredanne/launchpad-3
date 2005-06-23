# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Library functions for use in all scripts.

"""
__metaclass__ = type

import os
import threading
import atexit
import sys
import re
import logging
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
        ns, simplename = name
        if ns == u'http://namespaces.zope.org/browser':
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

def logger(options=None, name=None):
    """Return a logging instance with standard setup.

    If options is not passed, the command line is parsed for the standard
    options specified by logger_options().
    
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

    if name is None:
        # Determine the logger name from the script name
        name = sys.argv[0]
        name = re.sub('.py[oc]?$', '', name)

    level = options.loglevel

    # Clamp the loglevel
    if level < logging.DEBUG:
        level = logging.DEBUG
    elif level > logging.CRITICAL:
        level = logging.CRITICAL

    # Create our logger
    logger = logging.getLogger(name)

    # Make it print output in a standard format, suitable for 
    # both command line tools and cron jobs (command line tools often end
    # up being run from inside cron, so this is a good thing).
    hdlr = logging.StreamHandler(strm=sys.stderr)
    hdlr.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(message)s'
        ))
    logger.addHandler(hdlr)
    logger.setLevel(level)

    return logger

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
    lp.dbuser = None

