# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TranslationsPerson."""

__metaclass__ = type

from lp.app.enums import ServiceUsage
from lp.services.webapp.testing import verifyObject
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.translations.interfaces.translationsperson import ITranslationsPerson


class TestTranslationsPerson(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_baseline(self):
        person = ITranslationsPerson(self.factory.makePerson())
        self.assertTrue(verifyObject(ITranslationsPerson, person))

    def test_hasTranslated(self):
        person = self.factory.makePerson()
        translationsperson = ITranslationsPerson(person)
        self.assertFalse(translationsperson.hasTranslated())
        self.factory.makeSuggestion(translator=person)
        self.assertTrue(translationsperson.hasTranslated())

    def test_translation_history_inactive_projects(self):
        # The translation history doesn't include projects that don't use
        # rosetta.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        series = self.factory.makeProductSeries(product=product)
        template = self.factory.makePOTemplate(productseries=series)
        pofile = self.factory.makePOFile(potemplate=template)
        self.factory.makeSuggestion(translator=person, pofile=pofile)
        with person_logged_in(product.owner):
            product.translations_usage = ServiceUsage.NOT_APPLICABLE
        translationsperson = ITranslationsPerson(person)
        history = translationsperson.translation_history
        self.assertTrue(history.is_empty()) 
