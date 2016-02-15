# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import

from ConfigParser import SafeConfigParser
import httplib
import json
import os.path
import socket
from StringIO import StringIO
import subprocess
from tempfile import NamedTemporaryFile
from textwrap import dedent
import time

from fixtures import Fixture

from lp.testing.keyserver import KeyServerTac
from lp.services.config import config

__metaclass__ = type


class GPGKeyServiceFixture(Fixture):

    """Run the gpgservice webapp and test key server."""

    def setUp(self):
        super(GPGKeyServiceFixture, self).setUp()
        # Figure out if the keyserver is running,and if not, run it:
        keyserver = KeyServerTac()
        if not os.path.exists(keyserver.pidfile):
            self.useFixture(KeyServerTac())

        # Write service config to a file on disk. This file gets deleted when the
        # fixture ends.
        service_config = _get_default_service_config()
        self._config_file = NamedTemporaryFile()
        self.addCleanup(self._config_file.close)
        service_config.write(self._config_file)
        self._config_file.flush()

        # Set the environment variable that tells gpgservice where to read it's
        # config file from:
        env = os.environ.copy()
        env['GPGSERVICE_CONFIG_PATH'] = self._config_file.name

        gunicorn_path = os.path.join(
            config.root, 'bin', 'gunicorn-for-gpgservice')
        self.interface = '127.0.0.1'
        self.port = _get_unused_port()
        gunicorn_options = ['-b', self.bind_address]
        wsgi_app_name = 'gpgservice.webapp:app'

        self._process = subprocess.Popen(
            args=[gunicorn_path] + gunicorn_options + [wsgi_app_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)
        self.addCleanup(self._kill_server)
        self._wait_for_service_start()
        self.reset_service_database()

    def _kill_server(self):
        self._process.terminate()
        stdout, stderr = self._process.communicate()
        self.addDetail('gunicorn-stdout', stdout)
        self.addDetail('gunicorn-stderr', stderr)

    def _wait_for_service_start(self):
        errors = []
        for i in range(10):
            conn = httplib.HTTPConnection(self.bind_address)
            try:
                conn.request('GET', '/')
            except socket.error as e:
                errors.append(e)
            else:
                resp = conn.getresponse()
                if resp.status == 200:
                    return
            time.sleep(0.1)
        raise RuntimeError("Service not responding: %r" % errors)

    def reset_service_database(self):
        """Reset the gpgservice instance database to the launchpad test data set."""
        conn = httplib.HTTPConnection(self.bind_address)
        test_data = {
            'keys': [
                {
                    'owner': 'name16_oid',
                    'id': '12345678',
                    'fingerprint': 'ABCDEF0123456789ABCDDCBA0000111112345678',
                    'size': 1024,
                    'algorithm': 'D',
                    'can_encrypt': True,
                    'enabled': True,
                }
            ]
        }
        headers = {'Content-Type': 'application/json'}
        conn.request('POST', '/test/reset_db', json.dumps(test_data), headers)
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            raise RuntimeError("Could not reset database: %s" % body)

    @property
    def bind_address(self):
        return '%s:%d' % (self.interface, self.port)


def _get_default_service_config():
    config = SafeConfigParser()
    config.readfp(StringIO(dedent("""\
        [gpghandler]
        host: localhost
        public_host: keyserver.ubuntu.com
        upload_keys: True
        port: 11371
        timeout: 5.0
        maximum_upload_size: 16777216
        enable_test_endpoint: true

        [database]
        type: sqlite
    """)))
    return config


def _get_unused_port():
    """Find and return an unused port

    There is a small race condition here (between the time we allocate the
    port, and the time it actually gets used), but for the purposes for which
    this function gets used it isn't a problem in practice.
    """
    s = socket.socket()
    try:
        s.bind(('localhost', 0))
        return s.getsockname()[1]
    finally:
        s.close()
