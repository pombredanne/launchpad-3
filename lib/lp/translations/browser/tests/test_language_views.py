# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.registry.model.karma import KarmaCategory, KarmaCache
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.browser.language import LanguageAdminView


class TestLanguageAdminView(TestCaseWithFactory):
    """Test Language web service API."""

    layer = LaunchpadZopelessLayer

    def setUpLanguageAdminView(self, language):
        return view

    def setUpLanguageTranslators(self, language, total=2):
        people = []

        for count in range(total):
            person = self.factory.makePerson()
            person.addLanguage(language)
            people.append(person)

        translations_category = KarmaCategory.selectOne(
            KarmaCategory.name=='translations')
        LaunchpadZopelessLayer.switchDbUser('karma')
        for person in people:
            # Fake some translations Karma for these Serbian people.
            karma = KarmaCache(person=person,
                               category=translations_category,
                               karmavalue=1)
        LaunchpadZopelessLayer.commit()

    def test_post(self):
        serbian = getUtility(ILanguageSet).getLanguageByCode('sr')
        self.setUpLanguageTranslators(serbian, 1001)

        LaunchpadZopelessLayer.switchDbUser('launchpad')
        form = {}
        view = LanguageAdminView(serbian, LaunchpadTestRequest(form=form))
        view.initialize()
        view.updateContextFromData(form)

