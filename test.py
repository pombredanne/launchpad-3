#!/usr/bin/python2.4
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
import sys, os, time, logging, warnings, re


if os.getsid(0) == os.getsid(os.getppid()):
    # We need to become the process group leader so test_on_merge.py
    # can reap its children.
    #
    # Note that if setpgrp() is used to move a process from one
    # process group to another (as is done by some shells when
    # creating pipelines), then both process groups must be part of
    # the same session.
    os.setpgrp()

# Make tests run in a timezone no launchpad developers live in.
# Our tests need to run in any timezone.
# (No longer actually required, as PQM does this)
os.environ['TZ'] = 'Asia/Calcutta'
time.tzset()

here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

# Set a flag if this is the main testrunner process
if len(sys.argv) > 1 and sys.argv[1] == '--resume-layer':
    main_process = False
else:
    main_process = True

# Install the import fascist import hook and atexit handler.
import importfascist
importfascist.install_import_fascist()

# Install the warning handler hook and atexit handler.
import warninghandler
warninghandler.install_warning_handler()

# Ensure overrides are generated
from configs import generate_overrides
generate_overrides()

# Tell canonical.config to use the testrunner config instance.
from canonical.config import config
config.setInstance('testrunner')

# Remove this module's directory from path, so that zope.testbrowser
# can import pystone from test:
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != here]


# Turn on psycopg debugging wrapper
#import canonical.database.debug
#canonical.database.debug.install()

# Unset the http_proxy environment variable, because we're going to make
# requests to localhost and we don't wand this to be proxied.
try:
    os.environ.pop('http_proxy')
except KeyError:
    pass

# Silence spurious warnings. Note that this does not propagate to subprocesses
# so this is not always as easy as it seems. Warnings caused by our code that
# need to be silenced should have an accomponied Bug reference.
#
warnings.filterwarnings(
        'ignore', 'PyCrypto', RuntimeWarning, 'twisted[.]conch[.]ssh'
        )
warnings.filterwarnings(
        'ignore', 'twisted.python.plugin', DeprecationWarning, 'buildbot'
        )
warnings.filterwarnings(
        'ignore', 'The concrete concept of a view has been deprecated.',
        DeprecationWarning
        )
warnings.filterwarnings(
        'ignore', 'bzrlib.*was deprecated', DeprecationWarning
        )
# This warning can be removed once we upgrade PQM to hardy.
warnings.filterwarnings(
        'ignore', 'docutils', DeprecationWarning
        )

# This warning will be triggered if the beforeTraversal hook fails. We
# want to ensure it is not raised as an error, as this will mask the real
# problem.
warnings.filterwarnings(
        'always',
        re.escape('clear_request_started() called outside of a request'),
        UserWarning
        )

# Any warnings not explicitly silenced are errors
warnings.filterwarnings('error', append=True)


from canonical.ftests import pgsql
# If this is removed, make sure canonical.ftests.pgsql is updated
# because the test harness there relies on the Connection wrapper being
# installed.
pgsql.installFakeConnect()

from zope.testing import testrunner

defaults = [
    # Find tests in the tests and ftests directories
    '--tests-pattern=^f?tests$',
    '--test-path=%s' % os.path.join(here, 'lib'),
    '--package=canonical',
    ]

# Monkey-patch os.listdir to randomise the results
original_listdir = os.listdir

import random

def listdir(path):
    """Randomise the results of os.listdir.

    It uses random.suffle to randomise os.listdir results, this way tests
    relying on unstable ordering will have a higher chance to fail in the
    development environment.
    """
    directory_contents = original_listdir(path)
    random.shuffle(directory_contents)
    return directory_contents

os.listdir = listdir


if __name__ == '__main__':

    # Extract arguments so we can see them too. We need to strip
    # --resume-layer and --default stuff if found as get_options can't
    # handle it.
    if len(sys.argv) > 1 and sys.argv[1] == '--resume-layer':
        args = list(sys.argv)
        args.pop(1) # --resume-layer
        args.pop(1) # The layer name
        while len(args) > 1 and args[1] == '--default':
            args.pop(1) # --default
            args.pop(1) # The default value
        args.insert(0, sys.argv[0])
    else:
        args = sys.argv
    options = testrunner.get_options(args=args, defaults=defaults)

    # Turn on Layer profiling if requested.
    from canonical.testing import profiled
    if options.verbose >= 3 and main_process:
        profiled.setup_profiling()

    # The working directory change is just so that the test script
    # can be invoked from places other than the root of the source
    # tree. This is very useful for IDE integration, so an IDE can
    # e.g. run the test that you are currently editing.
    try:
        there = os.getcwd()
        os.chdir(here)
        result = testrunner.run(defaults)
    finally:
        os.chdir(there)
    # Cribbed from sourcecode/zope/test.py - avoid spurious error during exit.
    logging.disable(999999999)

    # Print Layer profiling report if requested.
    if main_process and options.verbose >= 3:
        profiled.report_profile_stats()
    sys.exit(result)

