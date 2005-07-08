#!/usr/bin/env python2.4
##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test script

$Id: test.py 25177 2004-06-02 13:17:31Z jim $
"""
import sys, os, psycopg, time
from operator import attrgetter
import itertools

os.setpgrp() # So test_on_merge.py can reap its children

# Make tests run in a timezone no launchpad developers live in.
# Our tests need to run in any timezone.
# (No longer actually required, as PQM does this)
os.environ['TZ'] = 'Asia/Calcutta'
time.tzset()

here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

# Import fascist.  We set this up early to try to intercept as many imports as
# possible.
import __builtin__
import atexit

original_import = __builtin__.__import__
database_root = 'canonical.launchpad.database'
browser_root = 'canonical.launchpad.browser'
naughty_imports = set()

class JackbootError(ImportError):
    """Import Fascist says you can't make this import."""

    def __init__(self, import_into, name, *args):
        ImportError.__init__(self, import_into, name, *args)
        self.import_into = import_into
        self.name = name

    def format_message(self):
        return 'Generic JackbootError: %s imported into %s' % (
            self.name, self.import_into)

    def __str__(self):
        return self.format_message()


class DatabaseImportPolicyViolation(JackbootError):
    """Database code is imported directly into other code."""

    def format_message(self):
        return 'You should not import %s into %s' % (
            self.name, self.import_into)


class FromStarPolicyViolation(JackbootError):
    """import * from a module that has no __all__."""

    def format_message(self):
        return ('You should not import * from %s because it has no __all__'
                ' (in %s)' % (self.name, self.import_into))


class NotInModuleAllPolicyViolation(JackbootError):
    """import of a name that does not appear in a module's __all__."""

    def __init__(self, import_into, name, attrname):
        JackbootError.__init__(self, import_into, name, attrname)
        self.attrname = attrname

    def format_message(self):
        return ('You should not import %s into %s from %s,'
                ' because it is not in its __all__.' %
                (self.attrname, self.import_into, self.name))

def report_import_error(error):
    naughty_imports.add(error)

def raise_import_error(error):
    raise error

def import_fascist(name, globals={}, locals={}, fromlist=[]):
    # Change this next line when we want to start raising JackbootErrors
    # rather than just reporting them.
    notify_import_error = report_import_error

    import_into = globals.get('__name__')
    if import_into is None:
        import_into = ''
    if name.startswith(database_root) and import_into.startswith(browser_root):
        # Importing database code into browser code is naughty.
        # We'll eventually disallow these imports altogether.  For now we just
        # warn about it.
        error = DatabaseImportPolicyViolation(import_into, name)
        notify_import_error(error)

    module = original_import(name, globals, locals, fromlist)

    if fromlist is not None and import_into.startswith('canonical'):
        # We only want to warn about "from foo import bar" violations in our 
        # own code.
        if list(fromlist) == ['*'] and not hasattr(module, '__all__'):
            # "from foo import *" is naughty if foo has no __all__
            error = FromStarPolicyViolation(import_into, name)
            #notify_import_error(error)
            raise_import_error(error)
        elif list(fromlist) != ['*'] and hasattr(module, '__all__'):
            # "from foo import bar" is naughty if bar isn't in foo.__all__ (and
            # foo actually has an __all__).
            for attrname in fromlist:
                if attrname not in module.__all__:
                    error = NotInModuleAllPolicyViolation(
                        import_into, name, attrname)
                    notify_import_error(error)
    return module

__builtin__.__import__ = import_fascist


class attrsgetter:
    """Like operator.attrgetter, but works on multiple attribute names."""

    def __init__(self, *names):
        self.names = names

    def __call__(self, obj):
        return tuple(getattr(obj, name) for name in self.names)


def report_naughty_imports():
    if naughty_imports:
        print
        print '** %d import policy violations **' % len(naughty_imports)
        current_type = None

        database_violations = []
        fromstar_violations = []
        notinall_violations = []
        sorting_map = {
            DatabaseImportPolicyViolation: database_violations,
            FromStarPolicyViolation: fromstar_violations,
            NotInModuleAllPolicyViolation: notinall_violations
            }
        for error in naughty_imports:
            sorting_map[error.__class__].append(error)

        if database_violations:
            print
            print "There were %s database import violations." % (
                len(database_violations))
            sorted_violations = sorted(
                database_violations,
                key=attrsgetter('name', 'import_into'))

            for name, sequence in itertools.groupby(
                sorted_violations, attrgetter('name')):
                print "You should not import %s into:" % name
                for error in sequence:
                    print "   ", error.import_into

        if fromstar_violations:
            print
            print "There were %s imports 'from *' without an __all__." % (
                len(fromstar_violations))
            sorted_violations = sorted(
                fromstar_violations,
                key=attrsgetter('import_into', 'name'))

            for import_into, sequence in itertools.groupby(
                sorted_violations, attrgetter('import_into')):
                print "You should not import * into %s from" % import_into
                for error in sequence:
                    print "   ", error.name

        if notinall_violations:
            print
            print (
                "There were %s imports of names not appearing in the __all__."
                % len(notinall_violations))
            sorted_violations = sorted(
                notinall_violations,
                key=attrsgetter('name', 'attrname', 'import_into'))

            for (name, attrname), sequence in itertools.groupby(
                sorted_violations, attrsgetter('name', 'attrname')):
                print "You should not import %s from %s:" % (attrname, name)
                import_intos = sorted(
                    set([error.import_into for error in sequence]))
                for import_into in import_intos:
                    print "   ", import_into

atexit.register(report_naughty_imports)

# Tell canonical.config to use the test config section in launchpad.conf
from canonical.config import config
config.setDefaultSection('testrunner')

# Turn on psycopg debugging wrapper
#import canonical.database.debug
#canonical.database.debug.install()

# Silence spurious warnings or turn them into errors
import warnings
# Our Z3 is still using whrandom
warnings.filterwarnings(
        "ignore",
        "the whrandom module is deprecated; please use the random module"
        )
# Some stuff got deprecated in 2.4 that we can clean up
warnings.filterwarnings(
        "error", category=DeprecationWarning, module="email"
        )

from canonical.ftests import pgsql
# If this is removed, make sure canonical.ftests.pgsql is updated
# because the test harness there relies on the Connection wrapper being
# installed.
pgsql.installFakeConnect()

# This is a terrible hack to divorce the FunctionalTestSetup from
# its assumptions about the ZODB.
from zope.app.tests.functional import FunctionalTestSetup
FunctionalTestSetup.__init__ = lambda *x: None

# Install our own test runner to to pre/post sanity checks
import zope.app.tests.test
from canonical.database.sqlbase import SQLBase, ZopelessTransactionManager
class LaunchpadTestRunner(zope.app.tests.test.ImmediateTestRunner):
    def precheck(self, test):
        pass

    def postcheck(self, test):
        '''Tests run at the conclusion of every top level test suite'''
        # Confirm Zopeless teardown has been called if necessary
        assert ZopelessTransactionManager._installed is None, \
                'Test used Zopeless but failed to tearDown correctly'

        # Confirm all database connections have been dropped
        assert len(pgsql.PgTestSetup.connections) == 0, \
                'Not all PostgreSQL connections closed'

        # Disabled this check - we now optimize by only dropping the
        # db if necessary
        #
        #con = psycopg.connect('dbname=template1')
        #try:
        #    cur = con.cursor()
        #    cur.execute("""
        #        SELECT count(*) FROM pg_database
        #        WHERE datname='launchpad_ftest'
        #        """)
        #    r = cur.fetchone()[0]
        #    assert r == 0, 'launchpad_ftest database not dropped'
        #finally:
        #    con.close()

    def run(self, test):
        self.precheck(test)
        rv = super(LaunchpadTestRunner, self).run(test)
        self.postcheck(test)
        return rv
zope.app.tests.test.ImmediateTestRunner = LaunchpadTestRunner

if __name__ == '__main__':
    zope.app.tests.test.process_args()
