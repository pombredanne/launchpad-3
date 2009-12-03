# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for languages listing and filtering behaviour."""

__metaclass__ = type
__all__ = []

import transaction

from windmill.authoring import WindmillTestClient
from zope.component import getUtility

from canonical.launchpad.windmill.testing.constants import (
    FOR_ELEMENT, PAGE_LOAD, SLEEP)
from lp.translations.windmill.testing import TranslationsWindmillLayer
from lp.testing import TestCaseWithFactory

class LanguagesFilterTest(TestCaseWithFactory):
    """Test that filtering on the +languages page works."""

    layer = TranslationsWindmillLayer

    def test_filter_languages(self):
        """Test that filtering on the +languages page works."""
        client = WindmillTestClient('Languages filter')
        start_url = 'http://translations.launchpad.dev:8085/+languages'
        # Go to the languages page
        client.open(url=start_url)
        client.waits.forPageLoad(timeout=PAGE_LOAD)

