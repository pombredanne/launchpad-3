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
            url=u'%s/firefox/trunk/+setbranch' % CodeWindmillLayer.base_url)

        # To demonstrate the Javascript is loaded we simply need to see that
        # one of the controls is deactivated when the radio button selections
        # change.  When "Link to a Bazaar branch" is selected the
        # branch_location field should be enabled.  When any other radio
        # button is selected the branch_location field is disabled.
        self.client.waits.forElement(id=u'field.branch_type.link-lp-bzr',
                                     timeout=u'20000')

        # Select Bazaar as the RCS type...
        self.client.click(id=u'field.branch_type.link-lp-bzr')
        self.client.waits.forElement(id=u'field.branch_location',
                                     timeout=u'20000')
        # And the branch location is enabled.
        self.client.asserts.assertElemJS(id=u'field.branch_location',
                                         js='!element.disabled')

        # Select 'create new'...
        self.client.click(id=u'field.branch_type.create-new')
        self.client.waits.forElement(id=u'field.branch_location',
                                     timeout=u'20000')
        # And the branch location is now disabled, proving that the javascript
        # controls have loaded and are functioning.
        self.client.asserts.assertElemJS(id=u'field.branch_location',
                                         js='element.disabled')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
