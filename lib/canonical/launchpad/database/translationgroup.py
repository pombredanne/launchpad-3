# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['TranslationGroup', 'TranslationGroupSet']

from zope.component import getUtility
from zope.interface import implements

from sqlobject import (
    ForeignKey, StringCol, SQLMultipleJoin, SQLRelatedJoin,
    SQLObjectNotFound)

from canonical.launchpad.interfaces import (
    ILanguageSet, ITranslationGroup, ITranslationGroupSet, NotFoundError)
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.project import Project

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.validators.person import validate_public_person
from canonical.launchpad.database.translator import Translator


class TranslationGroup(SQLBase):
    """A TranslationGroup."""

    implements(ITranslationGroup)

    # default to listing alphabetically
    _defaultOrder = 'name'

    # db field names
    name = StringCol(unique=True, alternateID=True, notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)

    # useful joins
    distributions = SQLMultipleJoin('Distribution',
        joinColumn='translationgroup')
    languages = SQLRelatedJoin('Language', joinColumn='translationgroup',
        intermediateTable='Translator', otherColumn='language')
    translators = SQLMultipleJoin('Translator',
                                  joinColumn='translationgroup')

    # used to note additions
    def add(self, content):
        """See ITranslationGroup."""
        return content

    # adding and removing translators
    def remove_translator(self, translator):
        """See ITranslationGroup."""
        Translator.delete(translator.id)

    # get a translator by language or code
    def query_translator(self, language):
        """See ITranslationGroup."""
        return Translator.selectOneBy(language=language,
                                      translationgroup=self)

    @property
    def products(self):
        return Product.selectBy(translationgroup=self.id, active=True)

    @property
    def projects(self):
        return Project.selectBy(translationgroup=self.id, active=True)

    # get a translator by code
    def __getitem__(self, code):
        """See ITranslationGroup."""
        language_set = getUtility(ILanguageSet)
        language = language_set[code]
        result = Translator.selectOneBy(language=language,
                                        translationgroup=self)
        if result is None:
            raise NotFoundError, code
        return result


class TranslationGroupSet:

    implements(ITranslationGroupSet)

    title = 'Rosetta Translation Groups'

    def __iter__(self):
        """See ITranslationGroupSet."""
        for group in TranslationGroup.select():
            yield group

    def __getitem__(self, name):
        """See ITranslationGroupSet."""
        try:
            return TranslationGroup.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError, name

    def new(self, name, title, summary, owner):
        """See ITranslationGroupSet."""
        return TranslationGroup(
            name=name,
            title=title,
            summary=summary,
            owner=owner)

    def getByPerson(self, person):
        """See ITranslationGroupSet."""
        # XXX CarlosPerelloMarin 2007-04-02 bug=30789:
        # Direct members query is required until teams are members
        # of themselves.
        direct = TranslationGroup.select("""
            Translator.translationgroup = TranslationGroup.id AND
            Translator.translator = %s
            """ % sqlvalues(person),
            clauseTables=["Translator"],
            orderBy="TranslationGroup.title")

        indirect = TranslationGroup.select("""
            Translator.translationgroup = TranslationGroup.id AND
            Translator.translator = TeamParticipation.team AND
            TeamParticipation.person = %s
            """ % sqlvalues(person),
            clauseTables=["TeamParticipation", "Translator"],
            orderBy="TranslationGroup.title")

        return direct.union(indirect)

    def getGroupsCount(self):
        """See ITranslationGroupSet."""
        return TranslationGroup.select().count()

