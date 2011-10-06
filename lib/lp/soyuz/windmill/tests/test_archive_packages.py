# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.soyuz.windmill.testing import SoyuzWindmillLayer
from lp.testing import WindmillTestCase
from lp.testing.windmill import constants


class TestArchivePackagesSourcesExtra(WindmillTestCase):
    """Each listed source package can be expanded for extra information."""

    layer = SoyuzWindmillLayer

    def test_sources_extra_available(self):
        """A successful request for the extra info updates the display."""

        self.client.open(
            url='%s/~cprov/+archive/ppa/+packages'
                % SoyuzWindmillLayer.base_url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)

        self.client.click(id="pub29-expander")

        self.client.waits.forElement(
            xpath=u'//div[@id="pub29-container"]//a[text()="i386"]',
            timeout=constants.FOR_ELEMENT)
