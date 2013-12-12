# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mock Swift test fixture."""

__metaclass__ = type
__all__ = ['SwiftFixture']

import os.path
import shutil
import socket
import tempfile
import time

from fixtures import EnvironmentVariableFixture, FunctionFixture
from s4 import hollow
from swiftclient import client as swiftclient
import testtools.content
import testtools.content_type
from txfixtures.tachandler import TacTestFixture

from lp.services.config import config


class SwiftFixture(TacTestFixture):

    tacfile = os.path.join(os.path.dirname(__file__), 'hollow.tac')
    pidfile = None
    logfile = None
    root = None
    daemon_port = None

    def setUp(self, spew=False, umask=None):
        # Pick a random, free port.
        if self.daemon_port is None:
            sock = socket.socket()
            sock.bind(('', 0))
            self.daemon_port = sock.getsockname()[1]
            sock.close()
            self.logfile = os.path.join(
                config.root, 'logs', 'hollow-%s.log' % self.daemon_port)
            self.pidfile = os.path.join(
                config.root, 'logs', 'hollow-%s.pid' % self.daemon_port)
        assert self.daemon_port is not None

        super(SwiftFixture, self).setUp(
            spew, umask,
            os.path.join(config.root, 'bin', 'py'),
            os.path.join(config.root, 'bin', 'twistd'))

        logfile = self.logfile
        self.addCleanup(lambda: os.path.exists(logfile) and os.unlink(logfile))

        testtools.content.attach_file(
            self, logfile, 'swift-log', testtools.content_type.UTF8_TEXT)

        self.useFixture(EnvironmentVariableFixture(
            'OS_AUTH_URL',
            'http://localhost:{0}/keystone/v2.0/'.format(self.daemon_port)))
        self.useFixture(EnvironmentVariableFixture(
            'OS_USERNAME', hollow.DEFAULT_USERNAME))
        self.useFixture(EnvironmentVariableFixture(
            'OS_PASSWORD', hollow.DEFAULT_PASSWORD))
        self.useFixture(EnvironmentVariableFixture(
            'OS_TENANT_NAME', hollow.DEFAULT_TENANT_NAME))

    def setUpRoot(self):
        # Create a root directory.
        if self.root is None or not os.path.isdir(self.root):
            root_fixture = FunctionFixture(tempfile.mkdtemp, shutil.rmtree)
            self.useFixture(root_fixture)
            self.root = root_fixture.fn_result
            os.chmod(self.root, 0o700)
        assert os.path.isdir(self.root)

        # Pass on options to the daemon.
        os.environ['HOLLOW_ROOT'] = self.root
        os.environ['HOLLOW_PORT'] = str(self.daemon_port)

    def connect(self):
        """Return a valid connection to our mock Swift"""
        client = swiftclient.Connection(
            authurl=os.environ.get('OS_AUTH_URL', None),
            auth_version="2.0",
            tenant_name=os.environ.get('OS_TENANT_NAME', None),
            user=os.environ.get('OS_USERNAME', None),
            key=os.environ.get('OS_PASSWORD', None),
            retries=0, insecure=True)
        return client

    def startup(self):
        self.setUp()

    def shutdown(self):
        self.killTac()
        while self._hasDaemonStarted():
            time.sleep(0.1)
