# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LaunchpadCronScript',
    'LaunchpadScript',
    'LaunchpadScriptFailure',
    'SilentLaunchpadScriptFailure'
    ]

from ConfigParser import SafeConfigParser
from cProfile import Profile
import datetime
import logging
from optparse import OptionParser
import os.path
import sys

from contrib.glock import (
    GlobalLock,
    LockAlreadyAcquired,
    )
import pytz
from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import ISOLATION_LEVEL_DEFAULT
from canonical.launchpad import scripts
from canonical.launchpad.interfaces import IScriptActivitySet
from canonical.launchpad.webapp.interaction import (
    ANONYMOUS,
    setupInteractionByEmail,
    )
from canonical.lp import initZopeless


LOCK_PATH = "/var/lock/"
UTC = pytz.timezone('UTC')


class LaunchpadScriptFailure(Exception):
    """Something bad happened and the script is going away.

    When you raise LaunchpadScriptFailure inside your main() method, we
    do two things:

        - log an error with the stringified exception
        - sys.exit(1)

    Releasing the lock happens as a side-effect of the exit.

    Note that the sys.exit return value of 1 is defined as
    LaunchpadScriptFailure.exit_status. If you want a different value
    subclass LaunchpadScriptFailure and redefine it.
    """
    exit_status = 1


class SilentLaunchpadScriptFailure(Exception):
    """A LaunchpadScriptFailure that doesn't log an error."""
    def __init__(self, exit_status=1):
        Exception.__init__(self, exit_status)
        self.exit_status = exit_status
    exit_status = 1


class LaunchpadScript:
    """A base class for runnable scripts and cronscripts.

    Inherit from this base class to simplify the setup work that your
    script needs to do.

    What you define:
        - main()
        - add_my_options(), if you have any
        - usage and description, if you want output for --help

    What you call:
        - lock_and_run()

    If you are picky:
        - lock_or_die()
        - run()
        - unlock()
        - build_options()

    What you get:
        - self.logger
        - self.txn
        - self.parser (the OptionParser)
        - self.options (the parsed options)

    "Give me convenience or give me death."
    """
    lock = None
    txn = None
    usage = None
    description = None
    lockfilepath = None
    loglevel = logging.INFO

    def __init__(self, name=None, dbuser=None, test_args=None):
        """Construct new LaunchpadScript.

        Name is a short name for this script; it will be used to
        assemble a lock filename and to identify the logger object.

        Use dbuser to specify the user to connect to the database; if
        not supplied a default will be used.

        Specify test_args when you want to override sys.argv.  This is
        useful in test scripts.
        """
        if name is None:
            self.name = self.__class__.__name__.lower()
        else:
            self.name = name

        self.dbuser = dbuser

        if self.description is None:
            description = self.__doc__
        else:
            description = self.description

        # The construction of the option parser is a bit roundabout, but
        # at least it's isolated here. First we build the parser, then
        # we add options that our logger object uses, then call our
        # option-parsing hook, and finally pull out and store the
        # supplied options and args.
        self.parser = OptionParser(usage=self.usage,
                                   description=description)
        scripts.logger_options(self.parser, default=self.loglevel)
        self.parser.add_option(
            '--profile', dest='profile', metavar='FILE', help=(
                    "Run the script under the profiler and save the "
                    "profiling stats in FILE."))
        self.add_my_options()
        self.options, self.args = self.parser.parse_args(args=test_args)
        self.logger = scripts.logger(self.options, name)

        self.lockfilepath = os.path.join(LOCK_PATH, self.lockfilename)

    #
    # Hooks that we expect users to redefine.
    #

    def main(self):
        """Define the meat of your script here. Must be defined.

        Raise LaunchpadScriptFailure if you encounter an error condition
        that makes it impossible for you to proceed; sys.exit(1) will be
        invoked in that situation.
        """
        raise NotImplementedError

    def add_my_options(self):
        """Optionally customize this hook to define your own options.

        This method should contain only a set of lines that follow the
        template:

            self.parser.add_option("-f", "--foo", dest="foo",
                default="foobar-makes-the-world-go-round",
                help="You are joking, right?")
        """

    #
    # Convenience or death
    #

    def login(self, user):
        """Super-convenience method that avoids the import."""
        setupInteractionByEmail(user)

    #
    # Locking and running methods. Users only call these explicitly if
    # they really want to control the run-and-locking semantics of the
    # script carefully.
    #

    @property
    def lockfilename(self):
        """Return lockfilename.

        May be overridden in targeted scripts in order to have more specific
        lockfilename.
        """
        return "launchpad-%s.lock" % self.name

    def setup_lock(self):
        """Create lockfile.

        Note that this will create a lockfile even if you don't actually
        use it. GlobalLock.__del__ is meant to clean it up though.
        """
        self.lock = GlobalLock(self.lockfilepath, logger=self.logger)

    def lock_or_die(self, blocking=False):
        """Attempt to lock, and sys.exit(1) if the lock's already taken.

        Say blocking=True if you want to block on the lock being
        available.
        """
        self.setup_lock()
        try:
            self.lock.acquire(blocking=blocking)
        except LockAlreadyAcquired:
            self.logger.debug('Lockfile %s in use' % self.lockfilepath)
            sys.exit(1)

    def lock_or_quit(self, blocking=False):
        """Attempt to lock, and sys.exit(0) if the lock's already taken.

        For certain scripts the fact that a lock may already be acquired
        is a normal condition that does not warrant an error log or a
        non-zero exit code. Use this method if this is your case.
        """
        self.setup_lock()
        try:
            self.lock.acquire(blocking=blocking)
        except LockAlreadyAcquired:
            self.logger.info('Lockfile %s in use' % self.lockfilepath)
            sys.exit(0)

    def unlock(self, skip_delete=False):
        """Release the lock. Do this before going home.

        If you skip_delete, we won't try to delete the lock when it's
        freed. This is useful if you have moved the directory in which
        the lockfile resides.
        """
        self.lock.release(skip_delete=skip_delete)

    def run(self, use_web_security=False, implicit_begin=True,
            isolation=ISOLATION_LEVEL_DEFAULT):
        """Actually run the script, executing zcml and initZopeless."""
        self._init_zca(use_web_security=use_web_security)
        self._init_db(implicit_begin=implicit_begin, isolation=isolation)

        date_started = datetime.datetime.now(UTC)
        profiler = None
        if self.options.profile:
            profiler = Profile()
        try:
            if profiler:
                profiler.runcall(self.main)
            else:
                self.main()
        except LaunchpadScriptFailure, e:
            self.logger.error(str(e))
            sys.exit(e.exit_status)
        except SilentLaunchpadScriptFailure, e:
            sys.exit(e.exit_status)
        else:
            date_completed = datetime.datetime.now(UTC)
            self.record_activity(date_started, date_completed)
        if profiler:
            profiler.dump_stats(self.options.profile)

    def _init_zca(self, use_web_security):
        """Initialize the ZCA, this can be overriden for testing purpose."""
        scripts.execute_zcml_for_scripts(use_web_security=use_web_security)

    def _init_db(self, implicit_begin, isolation):
        """Initialize the database transaction.

        Can be overriden for testing purpose.
        """
        self.txn = initZopeless(
            dbuser=self.dbuser, implicitBegin=implicit_begin,
            isolation=isolation)

    def record_activity(self, date_started, date_completed):
        """Hook to record script activity."""

    #
    # Make things happen
    #

    def lock_and_run(self, blocking=False, skip_delete=False,
                     use_web_security=False, implicit_begin=True,
                     isolation=ISOLATION_LEVEL_DEFAULT):
        """Call lock_or_die(), and then run() the script.

        Will die with sys.exit(1) if the locking call fails.
        """
        self.lock_or_die(blocking=blocking)
        try:
            self.run(use_web_security=use_web_security,
                     implicit_begin=implicit_begin, isolation=isolation)
        finally:
            self.unlock(skip_delete=skip_delete)


class LaunchpadCronScript(LaunchpadScript):
    """Logs successful script runs in the database."""

    def __init__(self, name=None, dbuser=None, test_args=None):
        """Initialize, and sys.exit() if the cronscript is disabled.

        Rather than hand editing crontab files, cronscripts can be
        enabled and disabled using a config file.

        The control file location is specified by
        config.canonical.cron_control_file.
        """
        super(LaunchpadCronScript, self).__init__(name, dbuser, test_args)

        enabled = cronscript_enabled(
            config.canonical.cron_control_file, self.name, self.logger)
        if not enabled:
            sys.exit(0)

    def record_activity(self, date_started, date_completed):
        """Record the successful completion of the script."""
        self.txn.begin()
        self.login(ANONYMOUS)
        getUtility(IScriptActivitySet).recordSuccess(
            name=self.name,
            date_started=date_started,
            date_completed=date_completed)
        self.txn.commit()


def cronscript_enabled(control_path, name, log):
    """Return True if the cronscript is enabled."""
    if not os.path.isabs(control_path):
        control_path = os.path.abspath(
            os.path.join(config.root, control_path))

    cron_config = SafeConfigParser({'enabled': str(True)})

    if not os.path.exists(control_path):
        # No control file exists. Everything enabled by default.
        log.debug("Cronscript control file not found at %s", control_path)
    else:
        log.debug("Cronscript control file found at %s", control_path)

        # Try reading the config file. If it fails, we log the
        # traceback and continue on using the defaults.
        try:
            cron_config.read(control_path)
        except:
            log.exception("Error parsing %s", control_path)

    if cron_config.has_option(name, 'enabled'):
        section = name
    else:
        section = 'DEFAULT'

    try:
        enabled = cron_config.getboolean(section, 'enabled')
    except:
        log.exception(
            "Failed to load value from %s section of %s",
            section, control_path)
        enabled = True

    if enabled:
        log.debug("Enabled by %s section", section)
    else:
        log.info("Disabled by %s section", section)

    return enabled
