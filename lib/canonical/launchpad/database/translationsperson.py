# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'TranslationsPerson',
    ]

from zope.component import adapts, getUtility
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues

from lp.registry.interfaces.person import IPerson
from canonical.launchpad.interfaces.translationgroup import (
    ITranslationGroupSet)
from canonical.launchpad.interfaces.translationsperson import (
    ITranslationsPerson)
from canonical.launchpad.interfaces.translator import ITranslatorSet

from lp.services.worlddata.model.language import Language
from canonical.launchpad.database.pofiletranslator import POFileTranslator
from canonical.launchpad.database.translationrelicensingagreement import (
    TranslationRelicensingAgreement)


class TranslationsPerson:
    """See `ITranslationsPerson`."""
    implements(ITranslationsPerson)
    adapts(IPerson)

    def __init__(self, person):
        self.person = person

    @property
    def translatable_languages(self):
        """See `ITranslationsPerson`."""
        return Language.select("""
            Language.id = PersonLanguage.language AND
            PersonLanguage.person = %s AND
            Language.code <> 'en' AND
            Language.visible""" % sqlvalues(self.person),
            clauseTables=['PersonLanguage'], orderBy='englishname')

    @property
    def translation_history(self):
        """See `ITranslationsPerson`."""
        return POFileTranslator.select(
            'POFileTranslator.person = %s' % sqlvalues(self.person),
            orderBy='-date_last_touched')

    @property
    def translation_groups(self):
        """See `ITranslationsPerson`."""
        return getUtility(ITranslationGroupSet).getByPerson(self.person)

    @property
    def translators(self):
        """See `ITranslationsPerson`."""
        return getUtility(ITranslatorSet).getByTranslator(self.person)

    def get_translations_relicensing_agreement(self):
        """Return whether translator agrees to relicense their translations.

        If she has made no explicit decision yet, return None.
        """
        relicensing_agreement = TranslationRelicensingAgreement.selectOneBy(
            person=self.person)
        if relicensing_agreement is None:
            return None
        else:
            return relicensing_agreement.allow_relicensing

    def set_translations_relicensing_agreement(self, value):
        """Set a translations relicensing decision by translator.

        If she has already made a decision, overrides it with the new one.
        """
        relicensing_agreement = TranslationRelicensingAgreement.selectOneBy(
            person=self.person)
        if relicensing_agreement is None:
            relicensing_agreement = TranslationRelicensingAgreement(
                person=self.person,
                allow_relicensing=value)
        else:
            relicensing_agreement.allow_relicensing = value

    translations_relicensing_agreement = property(
        get_translations_relicensing_agreement,
        set_translations_relicensing_agreement,
        doc="See `ITranslationsPerson`.")
