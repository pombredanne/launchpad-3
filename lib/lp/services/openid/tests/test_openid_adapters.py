# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from testtools.matchers import StartsWith

from lp.services.config.fixture import (
    ConfigFixture,
    ConfigUseFixture,
    )
from lp.services.openid.adapters.openid import IOpenIDPersistentIdentity
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class OpenIdAdapterTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def set_launchpad_section_setings(self, **kwargs):
        config_name = self.getUniqueString()
        config_fixture = self.useFixture(
            ConfigFixture(
                config_name,
                DatabaseFunctionalLayer.config_fixture.instance_name))
        setting_lines = ['[launchpad]'] + \
            ['%s: %s' % (k, v) for k, v in kwargs.items()]
        config_fixture.add_section('\n'.join(setting_lines))
        self.useFixture(ConfigUseFixture(config_name))

    def test_openid_adapter_openid_urls_obey_settings(self):
        self.set_launchpad_section_setings(
            openid_canonical_root='https://login.testing.ubuntu.com',
            openid_provider_root='https://some.new.provider.com',
        )
        account = self.factory.makeAccount()
        i = IOpenIDPersistentIdentity(account)
        self.assertThat(
            i.openid_identity_url,
            StartsWith('https://some.new.provider.com'))
        self.assertThat(
            i.openid_canonical_url,
            StartsWith('https://login.testing.ubuntu.com'))
