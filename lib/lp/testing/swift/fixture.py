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

from fixtures import FunctionFixture
from s4 import hollow
from swiftclient import client as swiftclient
from txfixtures.tachandler import TacTestFixture

from lp.services.config import config


class SwiftFixture(TacTestFixture):

    tacfile = os.path.join(os.path.dirname(__file__), 'hollow.tac')
    pidfile = os.path.join(os.path.dirname(__file__), 'hollow.pid')
    logfile = os.path.join(os.path.dirname(__file__), 'hollow.log')
    root = None
    daemon_port = None

    def setUp(self, spew=False, umask=None):
        super(SwiftFixture, self).setUp(
            spew, umask,
            os.path.join(config.root, 'bin', 'py'),
            os.path.join(config.root, 'bin', 'twistd'))

    def setUpRoot(self):
        # Pick a random, free port.
        if self.daemon_port is None:
            sock = socket.socket()
            sock.bind(('', 0))
            self.daemon_port = sock.getsockname()[1]
            sock.close()
        assert self.daemon_port is not None

        # Create a root directory
        root_fixture = FunctionFixture(tempfile.mkdtemp, shutil.rmtree)
        self.useFixture(root_fixture)
        self.root = root_fixture.fn_result
        os.chmod(self.root, 0o700)
        os.environ['HOLLOW_ROOT'] = self.root
        os.environ['HOLLOW_PORT'] = str(self.daemon_port)

    def connect(
        self, tenant_name=hollow.DEFAULT_TENANT_NAME,
        username=hollow.DEFAULT_USERNAME, password=hollow.DEFAULT_PASSWORD):
        """Return a valid connection to our mock Swift"""
        port = self.daemon_port
        client = swiftclient.Connection(
            authurl="http://localhost:%d/keystone/v2.0/" % port,
            auth_version="2.0", tenant_name=tenant_name,
            user=username, key=password,
            retries=0, insecure=True)
        return client

    def startup(self):
        self.setUp()

    def shutdown(self):
        self.cleanUp()
        while self._hasDaemonStarted():
            time.sleep(0.1)
