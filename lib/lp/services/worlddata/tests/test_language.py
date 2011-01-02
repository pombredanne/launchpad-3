# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lazr.lifecycle.interfaces import IDoNotSnapshot

from canonical.testing.layers import FunctionalLayer
from lp.services.worlddata.interfaces.language import ILanguage
from lp.testing import TestCaseWithFactory


class TestLanguageWebservice(TestCaseWithFactory):
    """Test Language web service API."""

    layer = FunctionalLayer

    def test_translators(self):
        self.failUnless(
            IDoNotSnapshot.providedBy(ILanguage['translators']),
            "ILanguage.translators should not be included in snapshots, "
            "see bug 553093.")
