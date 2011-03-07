# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from launchpadlib.errors import Unauthorized

from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    api_url,
    launchpadlib_for,
    TestCaseWithFactory,
    )


class TestDistribution(TestCaseWithFactory):
    """Test how distributions behave through the web service."""

    layer = DatabaseFunctionalLayer

    def test_attempt_to_write_data_without_permission_gives_Unauthorized(self):
        distro = self.factory.makeDistribution()
        endInteraction()
        lp = launchpadlib_for("anonymous-access")
        lp_distro = lp.load(api_url(distro))
        lp_distro.active = False
        self.assertRaises(Unauthorized, lp_distro.lp_save)
