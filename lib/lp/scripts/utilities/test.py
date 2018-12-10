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
"""Test script."""

import doctest
import os
import random
import re
import signal
import sys
import time
import warnings

import six
from zope.testing import testrunner
from zope.testing.testrunner import options

from lp.scripts.utilities import (
    importfascist,
    warninghandler,
    )
from lp.services.config import config


def fix_doctest_output():
    # Fix doctest so that it can handle mixed unicode and encoded output.
    _RealSpoofOut = doctest._SpoofOut

    class _SpoofOut(doctest._SpoofOut):

        def write(self, value):
            _RealSpoofOut.write(self, six.ensure_binary(value))

    doctest._SpoofOut = _SpoofOut


def configure_environment():
    # Make tests run in a timezone no launchpad developers live in.
    # Our tests need to run in any timezone.
    # (This is no longer actually required, as PQM does this.)
    os.environ['TZ'] = 'Asia/Calcutta'
    time.tzset()

    # Httplib2 0.7 started validating SSL certificates, and the test suite
    # uses a self-signed certificate, so disable it with an env variable.
    os.environ['LP_DISABLE_SSL_CERTIFICATE_VALIDATION'] = '1'

    # Storm's C extensions should already be enabled from
    # lp_sitecustomize.py, which our custom sitecustomize.py ran.
    assert os.environ['STORM_CEXTENSIONS'] == '1'

    # Install the import fascist import hook and atexit handler.
    importfascist.install_import_fascist()

    # Install the warning handler hook and atexit handler.
    warninghandler.install_warning_handler()

    # Ensure that atexit handlers are executed on TERM.
    def exit_with_atexit_handlers(*ignored):
        sys.exit(-1 * signal.SIGTERM)
    signal.signal(signal.SIGTERM, exit_with_atexit_handlers)

    # Tell lp.services.config to use the testrunner config instance.
    config.setInstance('testrunner')
    config.generate_overrides()

    # Remove this module's directory from path, so that zope.testbrowser
    # can import pystone from test:
    sys.path[:] = [p for p in sys.path if os.path.abspath(p) != config.root]

    # Turn on psycopg debugging wrapper
    #import lp.services.database.debug
    #lp.services.database.debug.install()

    # Unset the http_proxy environment variable, because we're going to make
    # requests to localhost and we don't want this to be proxied.
    os.environ.pop('http_proxy', None)

    # Suppress accessibility warning because the test runner does not have UI.
    os.environ['GTK_MODULES'] = ''


def filter_warnings():
    # Silence spurious warnings. Note that this does not propagate to
    # subprocesses so this is not always as easy as it seems. Warnings
    # caused by our code that need to be silenced should have an accompanied
    # Bug reference.
    warnings.filterwarnings(
        'ignore', 'PyCrypto', RuntimeWarning, 'twisted[.]conch[.]ssh',
        )
    warnings.filterwarnings(
        'ignore', 'twisted.python.plugin', DeprecationWarning,
        )
    warnings.filterwarnings(
        'ignore', 'zope.testing.doctest', DeprecationWarning,
        )
    warnings.filterwarnings(
        'ignore', 'bzrlib.*was deprecated', DeprecationWarning,
        )
    # The next one is caused by an infelicity in python-openid.  The
    # following change to openid/server/server.py would make the warning
    # filter unnecessary:
    # 978c974,974
    # >         try:
    # >             namespace = request.message.getOpenIDNamespace()
    # >         except AttributeError:
    # >             namespace = request.namespace
    # >         self.fields = Message(namespace)
    # ---
    # <         self.fields = Message(request.namespace)
    warnings.filterwarnings(
        'ignore',
        (r'The \"namespace\" attribute of CheckIDRequest objects is '
         r'deprecated.\s+'
         r'Use \"message.getOpenIDNamespace\(\)\" instead'),
        DeprecationWarning
    )
    # This warning will be triggered if the beforeTraversal hook fails. We
    # want to ensure it is not raised as an error, as this will mask the
    # real problem.
    warnings.filterwarnings(
        'always',
        re.escape('clear_request_started() called outside of a request'),
        UserWarning
        )
    # Unicode warnings are always fatal
    warnings.filterwarnings('error', category=UnicodeWarning)

    # shortlist() raises an error when it is misused.
    warnings.filterwarnings('error', r'shortlist\(\)')


def install_fake_pgsql_connect():
    from lp.testing import pgsql
    # If this is removed, make sure lp.testing.pgsql is updated
    # because the test harness there relies on the Connection wrapper being
    # installed.
    pgsql.installFakeConnect()


def randomise_listdir():
    # Monkey-patch os.listdir to randomise the results.
    original_listdir = os.listdir

    def listdir(path):
        """Randomise the results of os.listdir.

        It uses random.shuffle to randomise os.listdir results.  This way
        tests relying on unstable ordering will have a higher chance to fail
        in the development environment.
        """
        directory_contents = original_listdir(path)
        random.shuffle(directory_contents)
        return directory_contents

    os.listdir = listdir


defaults = {
    # Find tests in the tests and ftests directories
    'tests_pattern': '^f?tests$',
    'test_path': [os.path.join(config.root, 'lib')],
    'package': ['canonical', 'lp', 'devscripts', 'launchpad_loggerhead'],
    'layer': ['!(YUIAppServerLayer)'],
    'require_unique_ids': True,
    }


def main():
    # The working directory change is just so that the test script
    # can be invoked from places other than the root of the source
    # tree. This is very useful for IDE integration, so an IDE can
    # e.g. run the test that you are currently editing.
    there = os.getcwd()
    os.chdir(config.root)

    fix_doctest_output()
    configure_environment()
    filter_warnings()
    install_fake_pgsql_connect()
    randomise_listdir()

    # The imports at the top of this file must avoid anything that reads
    # from Launchpad config. Now that we've set the correct config instance,
    # we can safely import the rest.
    from lp.services.testing.customresult import (
        filter_tests,
        patch_find_tests,
        )
    from lp.services.testing import profiled

    # Extract arguments so we can see them too. We need to strip
    # --resume-layer and --default stuff if found as get_options can't
    # handle it.
    if len(sys.argv) > 1 and sys.argv[1] == '--resume-layer':
        main_process = False
        args = list(sys.argv)
        args.pop(1)  # --resume-layer
        args.pop(1)  # The layer name
        args.pop(1)  # The resume number
        while len(args) > 1 and args[1] == '--default':
            args.pop(1)  # --default
            args.pop(1)  # The default value
        args.insert(0, sys.argv[0])
    else:
        main_process = True
        args = sys.argv

    # thunk across to parallel support if needed.
    if '--parallel' in sys.argv and '--list-tests' not in sys.argv:
        # thunk over to parallel testing.
        from lp.services.testing.parallel import main
        sys.exit(main(sys.argv))

    def load_list(option, opt_str, list_name, parser):
        patch_find_tests(filter_tests(list_name, '--shuffle' in sys.argv))
    options.parser.add_option(
        '--load-list', type=str, action='callback', callback=load_list)
    options.parser.add_option(
        '--parallel', action='store_true',
        help='Run tests in parallel processes. '
            'Poorly isolated tests will break.')

    # tests_pattern is a regexp, so the parsed value is hard to compare
    # with the default value in the loop below.
    options.parser.defaults['tests_pattern'] = defaults['tests_pattern']
    local_options = options.get_options(args=args)
    # Set our default options, if the options aren't specified.
    for name, value in defaults.items():
        parsed_option = getattr(local_options, name)
        if ((parsed_option == []) or
            (parsed_option == options.parser.defaults.get(name))):
            # The option probably wasn't specified on the command line,
            # let's replace it with our default value. It could be that
            # the real default (as specified in
            # zope.testing.testrunner.options) was specified, and we
            # shouldn't replace it with our default, but it's such and
            # edge case, so we don't have to care about it.
            options.parser.defaults[name] = value

    # Turn on Layer profiling if requested.
    if local_options.verbose >= 3 and main_process:
        profiled.setup_profiling()

    try:
        try:
            testrunner.run([])
        except SystemExit:
            # Print Layer profiling report if requested.
            if main_process and local_options.verbose >= 3:
                profiled.report_profile_stats()
            raise
    finally:
        os.chdir(there)
