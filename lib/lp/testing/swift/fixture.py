# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mock Swift test fixture."""

__metaclass__ = type
__all__ = ['SwiftFixture']

import os.path
import shutil
import socket
import tempfile
from textwrap import dedent
import time

from fixtures import FunctionFixture
from s4 import hollow
from swiftclient import client as swiftclient
import testtools.content
import testtools.content_type
from txfixtures.tachandler import TacTestFixture

from lp.services.config import config
from lp.testing.layers import BaseLayer


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

        service_config = dedent("""\
                [librarian_server]
                os_auth_url: http://localhost:{0}/keystone/v2.0/
                os_username: {1}
                os_password: {2}
                os_tenant_name: {3}
                """.format(
                    self.daemon_port, hollow.DEFAULT_USERNAME,
                    hollow.DEFAULT_PASSWORD, hollow.DEFAULT_TENANT_NAME))
        BaseLayer.config_fixture.add_section(service_config)
        config.reloadConfig()
        assert config.librarian_server.os_tenant_name == 'test'

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
            authurl=config.librarian_server.os_auth_url,
            auth_version="2.0",
            tenant_name=config.librarian_server.os_tenant_name,
            user=config.librarian_server.os_username,
            key=config.librarian_server.os_password,
            retries=0, insecure=True)
        return client

    def startup(self):
        self.setUp()

    def shutdown(self):
        self.killTac()
        while self._hasDaemonStarted():
            time.sleep(0.1)
