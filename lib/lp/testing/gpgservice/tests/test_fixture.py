# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import

import json
import httplib

from testtools import TestCase
from testtools.matchers import (
    Contains,
    HasLength,
    Not,
    PathExists,
)

from lp.testing.gpgservice import GPGKeyServiceFixture


class GPGServiceFixtureTests(TestCase):

    def test_fixture_writes_and_deletes_service_config_file(self):
        fixture = GPGKeyServiceFixture()
        with fixture:
            config_file_path = fixture._config_file.name
            self.assertThat(config_file_path, PathExists())
        self.assertThat(config_file_path, Not(PathExists()))

    def test_fixture_starts_gpgservice(self):
        fixture = self.useFixture(GPGKeyServiceFixture())
        conn = httplib.HTTPConnection(fixture.bind_address)
        conn.request('GET', '/')
        resp = conn.getresponse()
        self.assertEqual(200, resp.status)
        self.assertEqual('gpgservice - Copyright 2015 Canonical', resp.read())

    def test_fixture_can_create_test_data(self):
        fixture = self.useFixture(GPGKeyServiceFixture())
        conn = httplib.HTTPConnection(fixture.bind_address)
        conn.request('GET', '/users/name16_oid/keys')
        resp = conn.getresponse()
        self.assertEqual(200, resp.status)
        data = json.loads(resp.read())
        self.assertThat(data, Contains('keys'))
        self.assertThat(data['keys'], HasLength(1))
