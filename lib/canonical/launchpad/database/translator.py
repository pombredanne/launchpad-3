# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Translator', 'TranslatorSet']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from storm.expr import Join
from storm.store import Store

from canonical.launchpad.interfaces.translator import (
    ITranslator, ITranslatorSet)

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from lp.registry.interfaces.person import validate_public_person
from lp.registry.model.teammembership import TeamParticipation

class Translator(SQLBase):
    """A Translator in a TranslationGroup."""

    implements(ITranslator)

    # default to listing newest first
    _defaultOrder = '-id'

    # db field names
    translationgroup = ForeignKey(dbName='translationgroup',
        foreignKey='TranslationGroup', notNull=True)
    language = ForeignKey(dbName='language',
        foreignKey='Language', notNull=True)
    translator = ForeignKey(
        dbName='translator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    style_guide_url = StringCol(notNull=False, default=None)


class TranslatorSet:
    implements(ITranslatorSet)

    def new(self, translationgroup, language,
            translator, style_guide_url=None):
        return Translator(
            translationgroup=translationgroup,
            language=language,
            translator=translator,
            style_guide_url=style_guide_url)

    def getByTranslator(self, translator):
        """See ITranslatorSet."""

        store = Store.of(translator)
        # TranslationGroup is referenced directly in SQL to avoid
        # a cyclic import.
        origin = [
            Translator,
            Join(TeamParticipation,
                TeamParticipation.teamID == Translator.translatorID),
            Join("TranslationGroup",
                 on="TranslationGroup.id = Translator.translationgroup")
            ]
        result = store.using(*origin).find(
            Translator, TeamParticipation.person == translator)

        return result.order_by("TranslationGroup.title")
