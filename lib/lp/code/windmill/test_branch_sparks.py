# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test for branch spark lines."""

__metaclass__ = type
__all__ = []

import windmill
from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_branch_sparks_var():
    """Test branch bug links."""
    client = WindmillTestClient("Branch bug links")

    client.open(
        url=windmill.settings['TEST_URL'] + '/~sabdfl/')
    client.waits.forPageLoad(timeout=u'10000')
    client.asserts.assertJS(js=u'''(function() {
        return branch_sparks.length == 5;
        }());''')
    client.asserts.assertJS(js=u'''(function() {
        var first_branch_spark = branch_sparks[0];
        return (first_branch_spark[0] == 'b-1' &&
            first_branch_spark[1] == '%s/~sabdfl/+junk/testdoc/+spark')
        }());''' % (windmill.settings['TEST_URL']))

