# Copyright 2007 Canonical Ltd.  All rights reserved.

import sys
import logging
from optparse import OptionParser

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.lp import initZopeless
from canonical.launchpad import scripts
from canonical.launchpad.ftests import login


class LaunchpadScriptFailure(Exception):
    exit_status = 1
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
        - self.options

    "Give me convenience or give me death."
    """
    lock = None
    txn = None
    usage = None
    description = None
    loglevel = logging.INFO
    def __init__(self, name, dbuser=None):
        """Construct new LaunchpadScript.

        Name is a short name for this script; it will be used in
        the lock filename and to identify the logger object.

        Use dbuser to specify the user to connect to the database; if
        not supplied a default will be used.
        """
        self.name = name
        self.dbuser = dbuser
        self.lockfile = "/var/lock/launchpad-%s.lock" % name

        # The construction of the option parser is a bit roundabout, but
        # at least it's isolated here. First we build the parser, then
        # we add options that our logger object uses, then call our
        # option-parsing hook, and finally pull out and store the
        # supplied options and args.
        self.parser = OptionParser(usage=self.usage, 
                                   description=self.description)
        scripts.logger_options(self.parser, default=self.loglevel)
        self.build_standard_options()
        self.options, self.args = self.parser.parse_args()
        if getattr(self.options, "lockfilename"):
            # I have no clue how to check if lockfilename is actually
            # present in self.options other than doing the getattr
            # above; it's a weird optparse.Values instance that has no
            # relevant methods.
            self.lockfile = self.options.lockfilename

        # Store logger and create lockfile. Note that this will create a
        # lockfile even if you don't actually use it; GlobalLock.__del__
        # is meant to clean it up though.
        self.logger = scripts.logger(self.options, name)
        self.lock = GlobalLock(self.lockfile, logger=self.logger)

    def build_standard_options(self):
        """Construct standard options. Right now this means --lockfile.

        You should use the add_my_options() hook to customize options.
        Override this only if you for some reason don't want the
        --lockfile option present.
        """
        self.parser.add_option("-l", "--lockfile", dest="lockfilename",
            default=self.lockfile,
            help="The file the script should use to lock the process.")
        self.add_my_options()

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
                help="You're joking right")
        """

    #
    # Convenience or death
    #

    def login(self, user):
        """Super-convenience method that avoids the import."""
        login(user)

    #
    # Locking and running methods. Users only call these explicitly if
    # they really want to control the run-and-locking semantics of the
    # script carefully.
    #

    def lock_or_die(self, blocking=False):
        """Attempt to lock, and sys.exit(1) if the lock's already taken.

        Say blocking=True if you want to block on the lock being
        available.
        """
        try:
            self.lock.acquire(blocking=blocking)
        except LockAlreadyAcquired:
            self.logger.error('Lockfile %s in use' % self.lockfilename)
            sys.exit(1)

    # XXX: I'm not sure this is actually necessary; if it is remove the
    # underscore, if not, remove the method. -- kiko, 2007-01-31
    def _lock_or_quit(self, blocking=False):
        """Attempt to lock, and sys.exit(0) if the lock's already taken.

        For certain scripts the fact that a lock may already be acquired
        is a normal condition that does not warrant an error log or a
        non-zero exit code. Use this method if this is your case.
        """
        try:
            self.lock.acquire(blocking=blocking)
        except LockAlreadyAcquired:
            self.logger.info('Lockfile %s in use' % self.lockfilename)
            sys.exit(0)

    def unlock(self, skip_delete=False):
        """Release the lock. Do this before going home.

        If you skip_delete, we won't try to delete the lock when it's
        freed. This is useful if you have moved the directory in which
        the lockfile resides.
        """
        self.lock.release(skip_delete=skip_delete)

    def run(self):
        """Actually run the script, executing zcml and initZopeless."""
        scripts.execute_zcml_for_scripts()
        self.txn = initZopeless(dbuser=self.dbuser)
        try:
            self.main()
        except LaunchpadScriptFailure, e:
            self.logger.error(str(e))
            sys.exit(e.exit_status)

    #
    # Make things happen
    #

    def lock_and_run(self, blocking=False, skip_delete=False):
        """Call lock_or_die(), and then run() the script.

        May die with sys.exit(1) if the locking call fails.
        """
        self.lock_or_die(blocking=blocking)
        try:
            self.run()
        finally:
            self.unlock(skip_delete=skip_delete)

