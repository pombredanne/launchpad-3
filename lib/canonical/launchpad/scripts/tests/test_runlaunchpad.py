# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for runlaunchpad.py"""

__metaclass__ = type
__all__ = [
    'CommandLineArgumentProcessing',
    'ServersToStart'
    ]


import unittest

from canonical.config import config
from canonical.launchpad.scripts.runlaunchpad import (
    get_services_to_run, SERVICES, split_out_runlaunchpad_arguments)


class CommandLineArgumentProcessing(unittest.TestCase):
    """runlaunchpad.py's command line arguments fall into two parts. The first
    part specifies which services to run, then second part is passed directly
    on to the Zope webserver start up.
    """

    def test_no_parameter(self):
        """Given no arguments, return no services and no Zope arguments."""
        self.assertEqual(([], []), split_out_runlaunchpad_arguments([]))

    def test_run_options(self):
        """Services to run are specified with an optional `-r` option.

        If a service is specified, it should appear as the first value in the
        returned tuple.
        """
        self.assertEqual(
            (['foo'], []), split_out_runlaunchpad_arguments(['-r', 'foo']))

    def test_run_lots_of_things(self):
        """The `-r` option can be used to specify multiple services.

        Multiple services are separated with commas. e.g. `-r foo,bar`.
        """
        self.assertEqual(
            (['foo', 'bar'], []),
            split_out_runlaunchpad_arguments(['-r', 'foo,bar']))

    def test_run_with_zope_params(self):
        """Any arguments after the initial `-r` option should be passed
        straight through to Zope.
        """
        self.assertEqual(
            (['foo', 'bar'], ['-o', 'foo', '--bar=baz']),
            split_out_runlaunchpad_arguments(['-r', 'foo,bar', '-o', 'foo',
                                              '--bar=baz']))

    def test_run_with_only_zope_params(self):
        """If no `-r` option is given, then all of the options should be passed
        straight through to Zope.
        """
        self.assertEqual(
            ([], ['-o', 'foo', '--bar=baz']),
            split_out_runlaunchpad_arguments(['-o', 'foo', '--bar=baz']))


class ServersToStart(unittest.TestCase):
    def setUp(self):
        """Make sure that only the Librarian is configured to launch."""
        unittest.TestCase.setUp(self)
        self.configs = [config.librarian.server,
                        config.buildsequencer,
                        config.authserver,
                        config.codehosting]
        self.old_launch_values = [conf.launch for conf in self.configs]
        new_launch_values = [True, False, False, False]
        for conf, launch_value in zip(self.configs, new_launch_values):
            conf.launch = launch_value

    def tearDown(self):
        """Restore the default configuration."""
        for config, launch_value in zip(self.configs, self.old_launch_values):
            config.launch = launch_value
        unittest.TestCase.tearDown(self)

    def test_nothing_explictly_requested(self):
        """When no service is explicitly requested, start services based on the
        config.launch property.
        """
        services = sorted(get_services_to_run([]))
        expected = [SERVICES['librarian']]
        # Mailman may or may not be asked to run.
        if config.mailman.launch:
            expected.append(SERVICES['mailman'])
        expected = sorted(expected)
        self.assertEqual(expected, services)

    def test_explicit_request_overrides(self):
        """Only start those services which are explictly requested, ignoring
        the configuration properties.
        """
        services = get_services_to_run(['sftp'])
        self.assertEqual([SERVICES['sftp']], services)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
