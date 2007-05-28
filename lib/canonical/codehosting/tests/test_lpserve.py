# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Tests for the Launchpad Bazaar smart server plugin."""

__metaclass__ = type

import os
import unittest

import bzrlib
from bzrlib.commands import get_cmd_object, register_command
from bzrlib import errors
from bzrlib.tests import TestCaseInTempDir
from bzrlib.transport import get_transport
from bzrlib.transport.memory import MemoryServer

from twisted.internet import defer
from canonical.tests.test_twisted import TwistedTestCase

from canonical.codehosting import plugins
from canonical.codehosting.plugins import lpserve
from canonical.codehosting.tests.test_acceptance import deferToThread
from canonical.codehosting.tests.test_transport import FakeLaunchpad
from canonical.launchpad.daemons.authserver import AuthserverService
from canonical.launchpad.scripts import runlaunchpad
from canonical.testing import TwistedLayer


ROCKETFUEL_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(bzrlib.__file__)))


class TestLaunchpadServerCommand(TwistedTestCase, TestCaseInTempDir):

    layer = TwistedLayer

    def assertInetServerShutsdownCleanly(self, process):
        """Shutdown the server process looking for errors."""
        # Shutdown the server: the server should shut down when it cannot read
        # from stdin anymore.
        process.stdin.close()
        # Hide stdin from the subprocess module, so it won't fail to close it.
        process.stdin = None
        result = self.finish_bzr_subprocess(process, retcode=0)
        self.assertEqual('', result[0])
        self.assertEqual('', result[1])

    def start_server_port(self, user_id, extra_options=()):
        """Start a bzr server subprocess.

         :param extra_options: extra options to give the server.
        :return: a tuple with the bzr process handle for passing to
            finish_bzr_subprocess, and the base url for the server.
        """
        # Serve from the current directory
        args = ['lp-serve', '--port', 'localhost:0']
        args.extend(extra_options)
        args.extend([user_id])
        process = self.start_bzr_subprocess(args, skip_if_plan_to_signal=True,
                                            allow_plugins=True)
        port_line = process.stdout.readline()
        prefix = 'listening on port: '
        self.assertStartsWith(port_line, prefix)
        port = int(port_line[len(prefix):])
        return (process, 'bzr://localhost:%d/' % port)

    def start_bzr_subprocess(self, process_args,
                             skip_if_plan_to_signal=False,
                             working_dir=None,
                             allow_plugins=False):
        env_changes = {'BZR_PLUGIN_PATH': os.path.dirname(plugins.__file__)}
        return TestCaseInTempDir.start_bzr_subprocess(
            self,
            process_args,
            env_changes=env_changes,
            skip_if_plan_to_signal=skip_if_plan_to_signal,
            working_dir=working_dir,
            allow_plugins=allow_plugins)

    def get_bzr_path(self):
        bzr_path = ROCKETFUEL_ROOT + '/sourcecode/bzr/bzr'
        assert os.path.isfile(bzr_path), "Bad Rocketfuel. Couldn't find bzr."
        return bzr_path

    def iterate_reactor(self):
        # XXX - This atrocity is here so that the adbapi's threadpool gets a
        # chance to start up.
        # Jonathan Lange, 2007-05-25
        from twisted.internet import reactor
        d = defer.Deferred()
        reactor.callLater(0.0001, d.callback, None)
        return d

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        authserver = AuthserverService()
        authserver.startService()
        self.addCleanup(authserver.stopService)
        return self.iterate_reactor()

    def test_command_registered(self):
        self.assertIsInstance(
            get_cmd_object('lp-serve'), lpserve.cmd_launchpad_server)

    @deferToThread
    def _test_bzr_serve_port_readonly(self):
        process, url = self.start_server_port('sabdfl', ['--read-only'])
        transport = get_transport(url)
        self.assertRaises(errors.TransportNotPossible,
                          transport.mkdir, '~sabdfl/+junk/new-branch')
        self.assertServerFinishesCleanly(process)

    def test_bzr_serve_port_readonly(self):
        return self._test_bzr_serve_port_readonly()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
