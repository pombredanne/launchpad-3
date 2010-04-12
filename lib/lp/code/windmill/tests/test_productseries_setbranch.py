# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for productseries setbranch Javascript."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.windmill.testing import lpuser

from lp.code.windmill.testing import CodeWindmillLayer
from lp.testing import WindmillTestCase


class TestProductSeriesSetbranch(WindmillTestCase):
    """Test productseries +setbranch Javascript controls."""

    layer = CodeWindmillLayer
    suite_name = 'ProductSeriesSetBranch'

    def test_productseries_setbranch(self):
        """Test productseries JS on /$projectseries/+setbranch page."""

        # Ensure we're logged in as 'foo bar'
        user = lpuser.FOO_BAR
        user.ensure_login(self.client)
        self.client.open(
            url=u'http://launchpad.dev:8085/firefox/trunk/+setbranch')
        self.client.waits.forElement(id=u'field.rcs_type.Bazaar',
                                     timeout=u'20000')
        self.client.waits.forElementProperty(
            id=u'field.rcs_type.Bazaar',
            option='onclick|onclick_rcs_type')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
