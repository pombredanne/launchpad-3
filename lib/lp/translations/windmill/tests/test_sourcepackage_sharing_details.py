# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for sharing details page."""


__metaclass__ = type


import transaction

from canonical.launchpad.webapp import canonical_url
from lp.testing import (
    feature_flags,
    set_feature_flag,
    WindmillTestCase,
)
from lp.testing.windmill import (
    lpuser,
)
from lp.testing.windmill.constants import (
    FOR_ELEMENT,
    PAGE_LOAD,
)
from lp.testing.windmill.widgets import (
    search_and_select_picker_widget,
)
from lp.translations.windmill.testing import (
    TranslationsWindmillLayer,
)


class TestSharingDetails(WindmillTestCase):

    layer = TranslationsWindmillLayer

    def test_set_branch(self):
        packaging = self.factory.makePackagingLink()
        branch = self.factory.makeProductBranch(
            product=packaging.productseries.product, name='product-branch')
        self.useContext(feature_flags())
        set_feature_flag(u'translations.sharing_information.enabled', u'on')
        transaction.commit()
        url = canonical_url(
            packaging.sourcepackage, rootsite='translations',
            view_name='+sharing-details')
        self.client.open(url=url)
        self.client.waits.forPageLoad(timeout=PAGE_LOAD)
        lpuser.TRANSLATIONS_ADMIN.ensure_login(self.client)
        self.client.waits.forElement(
            id='branch-incomplete', timeout=FOR_ELEMENT)
        self.client.click(xpath='//*[@id="branch-incomplete-picker"]/a')
        search_and_select_picker_widget(self.client, 'product-branch', 1)
        self.client.waits.forElementProperty(
            classname="unseen", option='id|branch-incomplete',
            timeout=FOR_ELEMENT)
        transaction.commit()
        self.assertEqual(branch, packaging.productseries.branch)
