# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for runlaunchpad.py"""

__metaclass__ = type
__all__ = [
    'CommandLineArgumentProcessing',
    'ServersToStart'
    ]


import os
import shutil
import tempfile
import unittest

import canonical.config
import lp.testing

from canonical.config import config
from canonical.launchpad.scripts.runlaunchpad import (
    get_services_to_run, SERVICES, process_config_arguments,
    split_out_runlaunchpad_arguments)



class CommandLineArgumentProcessing(lp.testing.TestCase):
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
        """Pass all the options to zope when the `-r` option is not given."""
        self.assertEqual(
            ([], ['-o', 'foo', '--bar=baz']),
            split_out_runlaunchpad_arguments(['-o', 'foo', '--bar=baz']))



class TestDefaultConfigArgument(lp.testing.TestCase):
    """Tests for the processing of the -C argument."""

    def setUp(self):
        self.config_root = tempfile.mkdtemp('configs')
        self.saved_instance = config.instance_name
        self.saved_config_roots = canonical.config.CONFIG_ROOT_DIRS
        canonical.config.CONFIG_ROOT_DIRS = [self.config_root]
        self.addCleanup(self.cleanUp)

    def cleanUp(self):
        shutil.rmtree(self.config_root)
        canonical.config.CONFIG_ROOT_DIRS = self.saved_config_roots
        config.setInstance(self.saved_instance)

    def test_keep_argument(self):
        """Make sure that a -C is processed unchanged."""
        self.assertEqual(
            ['-v', '-C', 'a_file.conf', '-h'],
            process_config_arguments(['-v', '-C', 'a_file.conf', '-h']))

    def test_default_config(self):
        """Make sure that the -C option is set to the correct instance."""
        instance_config_dir = os.path.join(self.config_root, 'instance1')
        os.mkdir(instance_config_dir)
        open(os.path.join(instance_config_dir, 'launchpad.conf'), 'w').close()
        config.setInstance('instance1')
        self.assertEqual(
            ['-a_flag', '-C', '%s/launchpad.conf' % instance_config_dir],
            process_config_arguments(['-a_flag']))

    def test_instance_not_found_raises_ValueError(self):
        """Make sure that an unknown instance fails."""
        config.setInstance('unknown')
        self.assertRaises(ValueError, process_config_arguments, [])

    def test_i_sets_the_instance(self):
        """The -i parameter will set the config instance name."""
        instance_config_dir = os.path.join(self.config_root, 'test')
        os.mkdir(instance_config_dir)
        open(os.path.join(instance_config_dir, 'launchpad.conf'), 'w').close()
        self.assertEquals(
            ['-o', 'foo', '-C', '%s/launchpad.conf' % instance_config_dir],
            process_config_arguments(
                ['-i', 'test', '-o', 'foo']))
        self.assertEquals('test', config.instance_name)


class ServersToStart(unittest.TestCase):
    """Test server startup control."""

    def setUp(self):
        """Make sure that only the Librarian is configured to launch."""
        unittest.TestCase.setUp(self)
        launch_data = """
            [librarian_server]
            launch: True
            [buildsequencer]
            launch: False
            [codehosting]
            launch: False
            """
        config.push('launch_data', launch_data)

    def tearDown(self):
        """Restore the default configuration."""
        config.pop('launch_data')
        unittest.TestCase.tearDown(self)

    def test_nothing_explictly_requested(self):
        """Implicitly start services based on the config.*.launch property.
        """
        services = sorted(get_services_to_run([]))
        expected = [SERVICES['librarian']]

        # Mailman may or may not be asked to run.
        if config.mailman.launch:
            expected.append(SERVICES['mailman'])

        # Likewise, the GoogleWebService may or may not be asked to
        # run.
        if config.google_test_service.launch:
            expected.append(SERVICES['google-webservice'])

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
