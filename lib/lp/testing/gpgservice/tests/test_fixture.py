# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import

import base64
import json
import httplib

from testtools import TestCase
from testtools.matchers import (
    Contains,
    HasLength,
    Not,
    PathExists,
    StartsWith,
)

from lp.services.config import config
from lp.services.config.fixture import (
    ConfigFixture,
    ConfigUseFixture,
    )
from lp.testing.layers import BaseLayer
from lp.testing.gpgservice import GPGKeyServiceFixture


class GPGServiceFixtureTests(TestCase):

    layer = BaseLayer

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
        self.assertThat(resp.read(), StartsWith('gpgservice - Copyright'))

    def test_fixture_can_create_test_data(self):
        fixture = self.useFixture(GPGKeyServiceFixture())
        conn = httplib.HTTPConnection(fixture.bind_address)
        user = base64.b64encode(
            config.launchpad.openid_provider_root + '+id/name16_oid',
            altchars='-_')
        conn.request('GET', '/users/%s/keys' % user)
        resp = conn.getresponse()
        self.assertEqual(200, resp.status)
        data = json.loads(resp.read())
        self.assertThat(data, Contains('keys'))
        self.assertThat(data['keys'], HasLength(1))

    def test_fixture_can_set_config_data(self):
        config_name = self.getUniqueString()
        config_fixture = self.useFixture(
            ConfigFixture(config_name, BaseLayer.config_fixture.instance_name))
        self.useFixture(ConfigUseFixture(config_name))
        gpg_fixture = self.useFixture(GPGKeyServiceFixture(config_fixture))

        self.assertEqual(
            gpg_fixture.bind_address, config.gpgservice.api_endpoint)
