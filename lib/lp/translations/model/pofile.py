# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212,W0231

"""`SQLObject` implementation of `IPOFile` interface."""

__metaclass__ = type
__all__ = [
    'POFile',
    'DummyPOFile',
    'POFileSet',
    'POFileToChangedFromPackagedAdapter',
    'POFileToTranslationFileDataAdapter',
    ]

import datetime

import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    StringCol,
    )
from storm.expr import (
    And,
    Coalesce,
    Exists,
    Join,
    LeftJoin,
    Not,
    Or,
    Select,
    SQL,
    )
from storm.info import ClassAlias
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    flush_database_updates,
    quote,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad import helpers
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.readonly import is_read_only
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from lp.registry.interfaces.person import validate_public_person
from lp.registry.model.person import Person
from lp.services.propertycache import cachedproperty
from lp.translations.enums import (
    RosettaImportStatus,
    TranslationPermission,
    )
from lp.translations.interfaces.pofile import (
    IPOFile,
    IPOFileSet,
    )
from lp.translations.interfaces.potmsgset import (
    BrokenTextError,
    TranslationCreditsType,
    )
from lp.translations.interfaces.translationcommonformat import (
    ITranslationFileData,
    )
from lp.translations.interfaces.translationexporter import (
    ITranslationExporter,
    )
from lp.translations.interfaces.translationimporter import (
    ITranslationImporter,
    NotExportedFromLaunchpad,
    OutdatedTranslationError,
    TooManyPluralFormsError,
    TranslationFormatInvalidInputError,
    TranslationFormatSyntaxError,
    )
from lp.translations.interfaces.translationmessage import (
    TranslationValidationStatus,
    )
from lp.translations.interfaces.translations import TranslationConstants
from lp.translations.interfaces.translationsperson import ITranslationsPerson
from lp.translations.model.pomsgid import POMsgID
from lp.translations.model.potmsgset import POTMsgSet
from lp.translations.model.translatablemessage import TranslatableMessage
from lp.translations.model.translationimportqueue import collect_import_info
from lp.translations.model.translationmessage import (
    make_plurals_sql_fragment,
    TranslationMessage,
    )
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )
from lp.translations.utilities.rosettastats import RosettaStats
from lp.translations.utilities.translation_common_format import (
    TranslationMessageData,
    )


def _check_translation_perms(permission, translators, person):
    """Return True or False dependening on whether the person is part of the
    right group of translators, and the permission on the relevant project,
    product or distribution.

    :param permission: The kind of TranslationPermission.
    :param translators: The list of official translators for the
        product/project/distribution.
    :param person: The person that we want to check if has translation
        permissions.
    """
    # Let's determine if the person is part of a designated translation team
    is_designated_translator = False
    # XXX sabdfl 2005-05-25:
    # This code could be improved when we have implemented CrowdControl.
    for translator in translators:
        if person.inTeam(translator):
            is_designated_translator = True
            break

    # have a look at the applicable permission policy
    if permission == TranslationPermission.OPEN:
        # if the translation policy is "open", then yes, anybody is an
        # editor of any translation
        return True
    elif permission == TranslationPermission.STRUCTURED:
        # in the case of a STRUCTURED permission, designated translators
        # can edit, unless there are no translators, in which case
        # anybody can translate
        if len(translators) > 0:
            # when there are designated translators, only they can edit
            if is_designated_translator is True:
                return True
        else:
            # since there are no translators, anyone can edit
            return True
    elif permission in (TranslationPermission.RESTRICTED,
                        TranslationPermission.CLOSED):
        # if the translation policy is "restricted" or "closed", then check if
        # the person is in the set of translators
        if is_designated_translator:
            return True
    else:
        raise NotImplementedError('Unknown permission %s' % permission.name)

    # ok, thats all we can check, and so we must assume the answer is no
    return False


def _person_has_not_licensed_translations(person):
    """Whether a person has declined to BSD-license their translations."""
    t_p = ITranslationsPerson(person)
    if (t_p.translations_relicensing_agreement is not None and
        t_p.translations_relicensing_agreement is False):
        return True
    else:
        return False


def _can_edit_translations(pofile, person):
    """Say if a person is able to edit existing translations.

    Return True or False indicating whether the person is allowed
    to edit these translations.

    Admins and Rosetta experts are always able to edit any translation.
    If the `IPOFile` is for an `IProductSeries`, the owner of the `IProduct`
    has also permissions.
    Any other mortal will have rights depending on if he/she is on the right
    translation team for the given `IPOFile`.translationpermission and the
    language associated with this `IPOFile`.
    """
    if is_read_only():
        # Nothing can be edited in read-only mode.
        return False

    # If the person is None, then they cannot edit
    if person is None:
        return False

    # XXX Carlos Perello Marin 2006-02-07 bug=4814:
    # We should not check the permissions here but use the standard
    # security system.

    # Rosetta experts and admins can always edit translations.
    admins = getUtility(ILaunchpadCelebrities).admin
    rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
    if (person.inTeam(admins) or person.inTeam(rosetta_experts)):
        return True

    # The owner of the product is also able to edit translations.
    if pofile.potemplate.productseries is not None:
        product = pofile.potemplate.productseries.product
        if person.inTeam(product.owner):
            return True

    # If a person has decided not to license their translations under BSD
    # license they can't edit translations.
    if _person_has_not_licensed_translations(person):
        return False

    # Finally, check whether the user is member of the translation team or
    # owner for the given PO file.
    translators = [t.translator for t in pofile.translators]
    return _check_translation_perms(
        pofile.translationpermission,
        translators,
        person) or person.inTeam(pofile.owner)


def _can_add_suggestions(pofile, person):
    """Whether a person is able to add suggestions.

    Besides people who have permission to edit the translation, this
    includes any logged-in user for translations in STRUCTURED mode, and
    any logged-in user for translations in RESTRICTED mode that have a
    translation team assigned.
    """
    if is_read_only():
        # No suggestions can be added in read-only mode.
        return False

    if person is None:
        return False

    # If a person has decided not to license their translations under BSD
    # license they can't edit translations.
    if _person_has_not_licensed_translations(person):
        return False

    if _can_edit_translations(pofile, person):
        return True

    if pofile.translationpermission == TranslationPermission.OPEN:
        # We would return True here, except OPEN mode already allows
        # anyone to edit (see above).
        raise AssertionError(
            "Translation is OPEN, but user is not allowed to edit.")
    elif pofile.translationpermission == TranslationPermission.STRUCTURED:
        return True
    elif pofile.translationpermission == TranslationPermission.RESTRICTED:
        # Only allow suggestions if there is someone to review them.
        groups = pofile.potemplate.translationgroups
        for group in groups:
            if group.query_translator(pofile.language):
                return True
        return False
    elif pofile.translationpermission == TranslationPermission.CLOSED:
        return False

    raise AssertionError("Unknown translation mode.")


class POFileMixIn(RosettaStats):
    """Base class for `POFile` and `DummyPOFile`.

    Provides machinery for retrieving `TranslationMessage`s and populating
    their submissions caches.  That machinery is needed even for
    `DummyPOFile`s.
    """

    @property
    def plural_forms(self):
        """See `IPOFile`."""
        if self.language.pluralforms is not None:
            forms = self.language.pluralforms
        else:
            # Don't know anything about plural forms for this
            # language, fallback to the most common case, 2.
            forms = 2
        return forms

    def canEditTranslations(self, person):
        """See `IPOFile`."""
        return _can_edit_translations(self, person)

    def canAddSuggestions(self, person):
        """See `IPOFile`."""
        return _can_add_suggestions(self, person)

    def setOwnerIfPrivileged(self, person):
        """See `IPOFile`."""
        if self.canEditTranslations(person):
            self.owner = person

    def getHeader(self):
        """See `IPOFile`."""
        translation_importer = getUtility(ITranslationImporter)
        format_importer = translation_importer.getTranslationFormatImporter(
            self.potemplate.source_file_format)
        header = format_importer.getHeaderFromString(self.header)
        header.comment = self.topcomment
        header.has_plural_forms = self.potemplate.hasPluralMessage()
        return header

    def _getTranslationSearchQuery(self, pofile, plural_form, text):
        """Query to find `text` in `plural_form` translations of a `pofile`.

        This produces a list of clauses that can be used to search for
        TranslationMessages containing `text` in their msgstr[`plural_form`].
        Returned values are POTMsgSet ids containing them, expected to be
        used in a UNION across all plural forms.
        """
        translation_match = """
        -- Find translations containing `text`.
        -- Like in findPOTMsgSetsContaining(), to avoid seqscans on
        -- POTranslation table, we do ILIKE comparison on them in
        -- a subselect which is first filtered by the POFile.
          SELECT TranslationMessage.potmsgset
            FROM TranslationMessage
            JOIN TranslationTemplateItem
              ON TranslationMessage.potmsgset
                   = TranslationTemplateItem.potmsgset
            WHERE
              TranslationTemplateItem.potemplate = %(potemplate)s AND
              TranslationMessage.language = %(language)s AND
              TranslationMessage.msgstr%(plural_form)d IN (
                SELECT POTranslation.id FROM POTranslation WHERE
                  POTranslation.id IN (
                    SELECT DISTINCT(msgstr%(plural_form)d)
                      FROM TranslationMessage AS tm_ids
                      JOIN TranslationTemplateItem
                        ON tm_ids.potmsgset=TranslationTemplateItem.potmsgset
                      WHERE
                        TranslationTemplateItem.potemplate
                          = %(potemplate)s AND
                        TranslationTemplateItem.sequence > 0 AND
                        tm_ids.language=%(language)s
                  ) AND
                  POTranslation.translation
                    ILIKE '%%' || %(text)s || '%%')
                    """ % dict(potemplate=quote(pofile.potemplate),
                               language=quote(pofile.language),
                               plural_form=plural_form,
                               text=quote_like(text))
        return translation_match

    def _getTemplateSearchQuery(self, text):
        """Query for finding `text` in msgids of this POFile.
        """
        english_match = """
        -- Step 1a: get POTMsgSets where msgid_singular contains `text`
        -- To avoid seqscans on POMsgID table (what LIKE usually
        -- does), we do ILIKE comparison on them in a subselect first
        -- filtered by this POTemplate.
          SELECT POTMsgSet.id
            FROM POTMsgSet
            JOIN TranslationTemplateItem
              ON TranslationTemplateItem.potmsgset=POTMsgSet.id AND
                 TranslationTemplateItem.potemplate=%s
            WHERE
              (POTMsgSet.msgid_singular IS NOT NULL AND
               POTMsgSet.msgid_singular IN (
                 SELECT POMsgID.id FROM POMsgID
                   WHERE id IN (
                     SELECT DISTINCT(msgid_singular)
                       FROM POTMsgSet
                       JOIN TranslationTemplateItem
                         ON TranslationTemplateItem.potmsgset = POTMsgSet.id
                       WHERE
                         TranslationTemplateItem.potemplate=%s AND
                         TranslationTemplateItem.sequence > 0
                   ) AND
                   msgid ILIKE '%%' || %s || '%%'))
          UNION
        -- Step 1b: like above, just on msgid_plural.
          SELECT POTMsgSet.id
            FROM POTMsgSet
            JOIN TranslationTemplateItem
              ON TranslationTemplateItem.potmsgset=POTMsgSet.id AND
                 TranslationTemplateItem.potemplate=%s
            WHERE
              (POTMsgSet.msgid_plural IS NOT NULL AND
               POTMsgSet.msgid_plural IN (
                 SELECT POMsgID.id FROM POMsgID
                   WHERE id IN (
                     SELECT DISTINCT(msgid_plural)
                       FROM POTMsgSet
                       JOIN TranslationTemplateItem
                         ON TranslationTemplateItem.potmsgset = POTMsgSet.id
                       WHERE
                         TranslationTemplateItem.potemplate=%s AND
                         TranslationTemplateItem.sequence > 0
                   ) AND
                   msgid ILIKE '%%' || %s || '%%'))
            """ % (quote(self.potemplate), quote(self.potemplate),
                   quote_like(text),
                   quote(self.potemplate), quote(self.potemplate),
                   quote_like(text))
        return english_match

    def _getOrderedPOTMsgSets(self, origin_tables, query):
        """Find all POTMsgSets matching `query` from `origin_tables`.

        Orders the result by TranslationTemplateItem.sequence which must
        be among `origin_tables`.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        results = store.using(origin_tables).find(
            POTMsgSet, SQL(query))
        return results.order_by(TranslationTemplateItem.sequence)

    def findPOTMsgSetsContaining(self, text):
        """See `IPOFile`."""
        clauses = [
            'TranslationTemplateItem.potemplate = %s' % sqlvalues(
                self.potemplate),
            'TranslationTemplateItem.potmsgset = POTMsgSet.id',
            'TranslationTemplateItem.sequence > 0',
            ]

        if text is not None:
            assert len(text) > 1, (
                "You can not search for strings shorter than 2 characters.")

            if self.potemplate.uses_english_msgids:
                english_match = self._getTemplateSearchQuery(text)
            else:
                # If msgids are not in English, use English PO file
                # to fetch original strings instead.
                en_pofile = self.potemplate.getPOFileByLang('en')
                english_match = self._getTranslationSearchQuery(
                    en_pofile, 0, text)

            # Do not look for translations in a DummyPOFile.
            search_clauses = [english_match]
            if self.id is not None:
                for plural_form in range(self.plural_forms):
                    translation_match = self._getTranslationSearchQuery(
                        self, plural_form, text)
                    search_clauses.append(translation_match)

            clauses.append(
                "POTMsgSet.id IN (" + " UNION ".join(search_clauses) + ")")

        return self._getOrderedPOTMsgSets(
            [POTMsgSet, TranslationTemplateItem], ' AND '.join(clauses))

    def getFullLanguageCode(self):
        """See `IPOFile`."""
        return self.language.code

    def getFullLanguageName(self):
        """See `IPOFile`."""
        return self.language.englishname

    def makeTranslatableMessage(self, potmsgset):
        """See `IPOFile`."""
        return TranslatableMessage(potmsgset, self)


class POFile(SQLBase, POFileMixIn):
    implements(IPOFile)

    _table = 'POFile'

    potemplate = ForeignKey(foreignKey='POTemplate',
                            dbName='potemplate',
                            notNull=True)
    language = ForeignKey(foreignKey='Language',
                          dbName='language',
                          notNull=True)
    description = StringCol(dbName='description',
                            notNull=False,
                            default=None)
    topcomment = StringCol(dbName='topcomment',
                           notNull=False,
                           default=None)
    header = StringCol(dbName='header',
                       notNull=False,
                       default=None)
    fuzzyheader = BoolCol(dbName='fuzzyheader',
                          notNull=True)
    lasttranslator = ForeignKey(
        dbName='lasttranslator', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)

    date_changed = UtcDateTimeCol(
        dbName='date_changed', notNull=True, default=UTC_NOW)

    currentcount = IntCol(dbName='currentcount',
                          notNull=True,
                          default=0)
    updatescount = IntCol(dbName='updatescount',
                          notNull=True,
                          default=0)
    rosettacount = IntCol(dbName='rosettacount',
                          notNull=True,
                          default=0)
    unreviewed_count = IntCol(dbName='unreviewed_count',
                              notNull=True,
                              default=0)
    lastparsed = UtcDateTimeCol(dbName='lastparsed',
                                notNull=False,
                                default=None)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    path = StringCol(dbName='path',
                     notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    from_sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='from_sourcepackagename', notNull=False, default=None)

    @property
    def translation_messages(self):
        """See `IPOFile`."""
        return self.getTranslationMessages()

    def getTranslationMessages(self, condition=None):
        """See `IPOFile`."""
        applicable_template = Coalesce(
            TranslationMessage.potemplateID, self.potemplate.id)
        clauses = [
            TranslationTemplateItem.potmsgsetID ==
                TranslationMessage.potmsgsetID,
            TranslationTemplateItem.potemplate == self.potemplate,
            TranslationMessage.language == self.language,
            applicable_template == self.potemplate.id,
            ]
        if condition is not None:
            clauses.append(condition)

        return IStore(self).find(
            TranslationMessage, *clauses).order_by(TranslationMessage.id)

    @property
    def title(self):
        """See `IPOFile`."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        """See `IPOFile`."""
        translators = set()
        for group in self.potemplate.translationgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                translators.add(translator)
        return sorted(list(translators), key=lambda x: x.translator.name)

    @property
    def translationpermission(self):
        """See `IPOFile`."""
        return self.potemplate.translationpermission

    @property
    def contributors(self):
        """See `IPOFile`."""
        # Translation credit messages are "translated" by
        # rosetta_experts.  Shouldn't show up in contributors lists
        # though.
        admin_team = getUtility(ILaunchpadCelebrities).rosetta_experts

        contributors = Person.select("""
            POFileTranslator.person = Person.id AND
            POFileTranslator.person <> %s AND
            POFileTranslator.pofile = %s""" % sqlvalues(admin_team, self),
            clauseTables=["POFileTranslator"],
            distinct=True,
            # XXX: kiko 2006-10-19:
            # We can't use Person.sortingColumns because this is a
            # distinct query. To use it we'd need to add the sorting
            # function to the column results and then ignore it -- just
            # like selectAlso does, ironically.
            orderBy=["Person.displayname", "Person.name"])

        return contributors

    def prepareTranslationCredits(self, potmsgset):
        """See `IPOFile`."""
        LP_CREDIT_HEADER = u'Launchpad Contributions:'
        SPACE = u' '
        credits_type = potmsgset.translation_credits_type
        assert credits_type != TranslationCreditsType.NOT_CREDITS, (
            "Calling prepareTranslationCredits on a message with "
            "msgid '%s'." % potmsgset.singular_text)
        imported = potmsgset.getImportedTranslationMessage(
            self.potemplate, self.language)
        if imported is None:
            text = None
        else:
            text = imported.translations[0]
        if credits_type == TranslationCreditsType.KDE_EMAILS:
            emails = []
            if text is not None:
                emails.append(text)

            # Add two empty email fields to make formatting nicer.
            # See bug #133817 for details.
            emails.extend([u'', u''])

            for contributor in self.contributors:
                preferred_email = contributor.preferredemail
                if (contributor.hide_email_addresses or
                    preferred_email is None):
                    emails.append('')
                else:
                    emails.append(preferred_email.email)
            return u','.join(emails)
        elif credits_type == TranslationCreditsType.KDE_NAMES:
            names = []

            if text is not None:
                if text == u'':
                    text = SPACE
                names.append(text)
            # Add an empty name as a separator, and 'Launchpad
            # Contributions' header; see bug #133817 for details.
            names.extend([SPACE, LP_CREDIT_HEADER])
            names.extend([
                contributor.displayname
                for contributor in self.contributors])
            return u','.join(names)
        elif credits_type == TranslationCreditsType.GNOME:
            if len(list(self.contributors)):
                if text is None:
                    text = u''
                else:
                    # Strip existing Launchpad contribution lists.
                    header_index = text.find(LP_CREDIT_HEADER)
                    if header_index != -1:
                        text = text[:header_index]
                    else:
                        text += u'\n\n'

                text += LP_CREDIT_HEADER
                for contributor in self.contributors:
                    text += ("\n  %s %s" %
                             (contributor.displayname,
                              canonical_url(contributor)))
            return text
        else:
            raise AssertionError(
                "Calling prepareTranslationCredits on a message with "
                "unknown credits type '%s'." % credits_type.title)

    def _getClausesForPOFileMessages(self, current=True):
        """Get TranslationMessages for the POFile via TranslationTemplateItem.

        Call-site will have to have appropriate clauseTables.
        """
        clauses = [
            'TranslationTemplateItem.potemplate = %s' % sqlvalues(
                self.potemplate),
            ('TranslationTemplateItem.potmsgset'
             ' = TranslationMessage.potmsgset'),
            'TranslationMessage.language = %s' % sqlvalues(self.language)]
        if current:
            clauses.append('TranslationTemplateItem.sequence > 0')

        return clauses

    def getTranslationsFilteredBy(self, person):
        """See `IPOFile`."""
        assert person is not None, "You must provide a person to filter by."
        clauses = self._getClausesForPOFileMessages(current=False)
        clauses.append(
            'TranslationMessage.submitter = %s' % sqlvalues(person))

        return TranslationMessage.select(
            " AND ".join(clauses),
            clauseTables=['TranslationTemplateItem'],
            orderBy=['sequence', '-date_created'])

    def _getTranslatedMessagesQuery(self):
        """Get query data for fetching all POTMsgSets with translations.

        Return a tuple of SQL (clauses, clause_tables) to be used with
        POTMsgSet.select().
        """
        clause_tables = ['TranslationTemplateItem', 'TranslationMessage']
        clauses = self._getClausesForPOFileMessages()
        clauses.append('TranslationMessage.is_current IS TRUE')
        self._appendCompletePluralFormsConditions(clauses)

        # A message is current in this pofile if:
        #  * it's current (above) AND
        #  * (it's diverged AND non-empty)
        #     OR (it's shared AND non-empty AND no diverged one exists)
        diverged_translation_clauses = [
            'TranslationMessage.potemplate = %s' % sqlvalues(self.potemplate),
        ]
        diverged_translation_query = ' AND '.join(
            diverged_translation_clauses)

        shared_translation_clauses = [
            'TranslationMessage.potemplate IS NULL',
            '''NOT EXISTS (
                 SELECT * FROM TranslationMessage AS diverged
                   WHERE
                     diverged.potemplate=%(potemplate)s AND
                     diverged.is_current IS TRUE AND
                     diverged.language = %(language)s AND
                     diverged.potmsgset=TranslationMessage.potmsgset)''' % (
            dict(language=quote(self.language),
                 potemplate=quote(self.potemplate))),
        ]
        shared_translation_query = ' AND '.join(shared_translation_clauses)

        translated_query = ('( (' + diverged_translation_query + ') OR ('
                            + shared_translation_query + ') )')
        clauses.append(translated_query)
        return (clauses, clause_tables)

    def getPOTMsgSetTranslated(self):
        """See `IPOFile`."""
        clauses, clause_tables = self._getTranslatedMessagesQuery()
        clauses.append('TranslationTemplateItem.potmsgset = POTMsgSet.id')

        query = ' AND '.join(clauses)
        clause_tables.insert(0, POTMsgSet)
        return self._getOrderedPOTMsgSets(clause_tables, query)

    def getPOTMsgSetUntranslated(self):
        """See `IPOFile`."""
        # We get all POTMsgSet.ids with translations, and later
        # exclude them using a NOT IN subselect.
        translated_clauses, clause_tables = self._getTranslatedMessagesQuery()
        translated_clauses.append(
            'POTMsgSet.id=TranslationTemplateItem.potmsgset')
        # Even though this seems silly, Postgres prefers
        # TranslationTemplateItem index if we add it (and on staging we
        # get more than a 10x speed improvement: from 8s to 0.7s).  We
        # also need to put it before any other clauses to be actually useful.
        translated_clauses.insert(0,
            'TranslationTemplateItem.potmsgset ='
            ' TranslationTemplateItem.potmsgset')
        translated_query = (
            "(SELECT POTMsgSet.id"
            "   FROM TranslationTemplateItem, TranslationMessage, POTMsgSet"
            "   WHERE " + " AND ".join(translated_clauses) + ")")
        clauses = [
            'TranslationTemplateItem.potemplate = %s' % sqlvalues(
                self.potemplate),
            'TranslationTemplateItem.potmsgset = POTMsgSet.id',
            'TranslationTemplateItem.sequence > 0',
            ]
        clauses.append(
            'TranslationTemplateItem.potmsgset NOT IN (%s)' % (
                translated_query))

        query = ' AND '.join(clauses)
        return self._getOrderedPOTMsgSets(
            [POTMsgSet, TranslationTemplateItem], query)

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        clauses = self._getClausesForPOFileMessages()
        msgstr_clause = make_plurals_sql_fragment(
            "TranslationMessage.msgstr%(form)d IS NOT NULL", "OR")
        clauses.extend([
            'TranslationTemplateItem.potmsgset = POTMsgSet.id',
            'TranslationMessage.is_current IS NOT TRUE',
            "(%s)" % msgstr_clause,
            ])

        diverged_translation_query = (
            '''(SELECT COALESCE(diverged.date_reviewed, diverged.date_created)
                 FROM TranslationMessage AS diverged
                 WHERE
                   diverged.is_current IS TRUE AND
                   diverged.potemplate = %(potemplate)s AND
                   diverged.language = %(language)s AND
                   diverged.potmsgset=POTMsgSet.id)''' % dict(
            potemplate=quote(self.potemplate),
            language=quote(self.language)))

        shared_translation_query = (
            '''(SELECT COALESCE(shared.date_reviewed, shared.date_created)
                 FROM TranslationMessage AS shared
                 WHERE
                   shared.is_current IS TRUE AND
                   shared.potemplate IS NULL AND
                   shared.language = %(language)s AND
                   shared.potmsgset=POTMsgSet.id)''' % dict(
            language=quote(self.language)))
        beginning_of_time = "TIMESTAMP '1970-01-01 00:00:00'"
        newer_than_query = (
            "TranslationMessage.date_created > COALESCE(" +
            ",".join([diverged_translation_query,
                      shared_translation_query,
                      beginning_of_time]) + ")")
        clauses.append(newer_than_query)

        # A POT set has "new" suggestions if there is a non current
        # TranslationMessage newer than the current reviewed one.
        query = (
            """POTMsgSet.id IN (SELECT DISTINCT TranslationMessage.potmsgset
                 FROM TranslationMessage, TranslationTemplateItem, POTMsgSet
                 WHERE (%(query)s)) AND
               POTMsgSet.id=TranslationTemplateItem.potmsgset AND
               TranslationTemplateItem.potemplate=%(potemplate)s
            """ % dict(query=' AND '.join(clauses),
                       potemplate=quote(self.potemplate)))
        return self._getOrderedPOTMsgSets(
            [POTMsgSet, TranslationTemplateItem], query)

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        # POT set has been changed in Launchpad if it contains active
        # translation which didn't come from a published package
        # (iow, it's different from a published translation: this only
        # lists translations which have actually changed in LP, not
        # translations which are 'new' and only exist in LP).

        # TranslationMessage is changed if:
        # is_current IS TRUE, is_imported IS FALSE,
        # (diverged AND not empty) OR (shared AND not empty AND no diverged)
        # exists imported (is_imported AND not empty AND (diverged OR shared))
        clauses, clause_tables = self._getTranslatedMessagesQuery()
        clauses.extend([
            'TranslationTemplateItem.potmsgset = POTMsgSet.id',
            'TranslationMessage.is_imported IS FALSE',
            ])

        imported_no_diverged = (
            '''NOT EXISTS (
                 SELECT * FROM TranslationMessage AS diverged
                   WHERE
                     diverged.is_imported IS TRUE AND
                     diverged.id <> imported.id AND
                     diverged.potemplate = %(potemplate)s AND
                     diverged.language = %(language)s AND
                     diverged.potmsgset=TranslationMessage.potmsgset)''' % (
            dict(potemplate=quote(self.potemplate),
                 language=quote(self.language))))

        imported_clauses = [
            'imported.id <> TranslationMessage.id',
            'imported.potmsgset = POTMsgSet.id',
            'imported.language = %s' % sqlvalues(self.language),
            'imported.is_imported IS TRUE',
            '(imported.potemplate=%s OR ' % sqlvalues(self.potemplate) +
            '   (imported.potemplate IS NULL AND ' + imported_no_diverged
            + '  ))',
            ]
        self._appendCompletePluralFormsConditions(imported_clauses,
                                                  'imported')
        exists_imported_query = (
            'EXISTS ('
            '  SELECT * FROM TranslationMessage AS imported'
            '      WHERE ' + ' AND '.join(imported_clauses) + ')')
        clauses.append(exists_imported_query)

        clause_tables.insert(0, POTMsgSet)
        query = ' AND '.join(clauses)
        return self._getOrderedPOTMsgSets(clause_tables, query)

    def getPOTMsgSetWithErrors(self):
        """See `IPOFile`."""
        clauses = self._getClausesForPOFileMessages()
        clauses.extend([
            'TranslationTemplateItem.potmsgset = POTMsgSet.id',
            'TranslationMessage.is_imported IS TRUE',
            'TranslationMessage.validation_status <> %s' % sqlvalues(
                TranslationValidationStatus.OK),
            ])

        query = ' AND '.join(clauses)
        origin = [POTMsgSet, TranslationMessage, TranslationTemplateItem]
        return self._getOrderedPOTMsgSets(origin, query)

    def messageCount(self):
        """See `IRosettaStats`."""
        return self.potemplate.messageCount()

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        return self.currentcount

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        return self.updatescount

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        return self.rosettacount

    def unreviewedCount(self):
        """See `IRosettaStats`."""
        return self.unreviewed_count

    def getStatistics(self):
        """See `IPOFile`."""
        return (
            self.currentcount,
            self.updatescount,
            self.rosettacount,
            self.unreviewed_count)

    def _appendCompletePluralFormsConditions(self, query,
                                             table_name='TranslationMessage'):
        """Add conditions to implement ITranslationMessage.is_complete in SQL.

        :param query: A list of AND SQL conditions where the implementation of
            ITranslationMessage.is_complete will be appended as SQL
            conditions.
        """
        query.append('%(table_name)s.msgstr0 IS NOT NULL' % {
            'table_name': table_name})
        if self.language.pluralforms > 1:
            plurals_query = ' AND '.join(
                '%(table_name)s.msgstr%(plural_form)d IS NOT NULL' % {
                  'plural_form': plural_form,
                  'table_name': table_name,
                } for plural_form in range(1, self.plural_forms))
            query.append(
                '(POTMsgSet.msgid_plural IS NULL OR (%s))' % plurals_query)
        return query

    def updateStatistics(self):
        """See `IPOFile`."""
        # make sure all the data is in the db
        flush_database_updates()

        # Get number of imported messages that are still synced in Launchpad.
        current_clauses = self._getClausesForPOFileMessages()

        current_clauses.extend([
            'TranslationTemplateItem.sequence > 0',
            'TranslationMessage.is_imported IS TRUE',
            'TranslationMessage.is_current IS TRUE',
            'TranslationMessage.potmsgset = POTMsgSet.id',
            """(TranslationMessage.potemplate = %(template)s OR (
                TranslationMessage.potemplate IS NULL AND NOT EXISTS (
                  SELECT * FROM TranslationMessage AS current
                    WHERE
                      current.potemplate = %(template)s AND
                      current.id <> TranslationMessage.id AND
                      current.language=%(language)s AND
                      TranslationMessage.potmsgset=current.potmsgset AND
                      current.msgstr0 IS NOT NULL AND
                      current.is_current IS TRUE )))""" % dict(
            template=quote(self.potemplate),
            language=quote(self.language)),
            ])
        self._appendCompletePluralFormsConditions(current_clauses)
        current = TranslationMessage.select(
            ' AND '.join(current_clauses),
            clauseTables=['TranslationTemplateItem', 'POTMsgSet']).count()

        # Get the number of translations that we have updated from what we got
        # from imports.
        updates = self.getPOTMsgSetChangedInLaunchpad().count()

        # Get total number of messages in a POTemplate.
        if self.potemplate.messageCount() > 0:
            total = self.potemplate.messageCount()
        else:
            total = self.potemplate.getPOTMsgSets().count()
            self.potemplate.messagecount = total

        # Get number of translations done only in Launchpad.
        untranslated = self.getPOTMsgSetUntranslated().count()
        translated = total - untranslated
        rosetta = translated - current

        # Get number of unreviewed translations in Launchpad.
        unreviewed = self.getPOTMsgSetWithNewSuggestions().count()

        self.currentcount = current
        self.updatescount = updates
        self.rosettacount = rosetta
        self.unreviewed_count = unreviewed
        return self.getStatistics()

    def updateHeader(self, new_header):
        """See `IPOFile`."""
        if new_header is None:
            return

        # XXX sabdfl 2005-05-27 should we also differentiate between
        # washeaderfuzzy and isheaderfuzzy?
        self.topcomment = new_header.comment
        self.header = new_header.getRawContent()
        self.fuzzyheader = new_header.is_fuzzy

    def isTranslationRevisionDateOlder(self, header):
        """See `IPOFile`."""
        old_header = self.getHeader()

        # Get the old and new PO-Revision-Date entries as datetime objects.
        old_date = old_header.translation_revision_date
        new_date = header.translation_revision_date
        if old_date is None or new_date is None:
            # If one of the headers has an unknown revision date, they cannot
            # be compared, so we consider the new one as the most recent.
            return False

        # Check whether the date is older.
        return old_date > new_date

    def setPathIfUnique(self, path):
        """See `IPOFile`."""
        if path != self.path and self.potemplate.isPOFilePathAvailable(path):
            self.path = path

    def importFromQueue(self, entry_to_import, logger=None, txn=None):
        """See `IPOFile`."""
        assert entry_to_import is not None, "Attempt to import None entry."
        assert entry_to_import.import_into.id == self.id, (
            "Attempt to import entry to POFile it doesn't belong to.")
        assert entry_to_import.status == RosettaImportStatus.APPROVED, (
            "Attempt to import non-approved entry.")

        # XXX: JeroenVermeulen 2007-11-29: This method is called from the
        # import script, which can provide the right object but can only
        # obtain it in security-proxied form.  We need full, unguarded access
        # to complete the import.
        entry_to_import = removeSecurityProxy(entry_to_import)

        translation_importer = getUtility(ITranslationImporter)

        # While importing a file, there are two kinds of errors:
        #
        # - Errors that prevent us to parse the file. That's a global error,
        #   is handled with exceptions and will not change any data other than
        #   the status of that file to note the fact that its import failed.
        #
        # - Errors in concrete messages included in the file to import. That's
        #   a more localised error that doesn't affect the whole file being
        #   imported. It allows us to accept other translations so we accept
        #   everything but the messages with errors. We handle it returning a
        #   list of faulty messages.
        import_rejected = False
        needs_notification_for_imported = False
        error_text = None
        errors, warnings = None, None
        try:
            errors, warnings = (
                translation_importer.importFile(entry_to_import, logger))
        except NotExportedFromLaunchpad:
            # We got a file that was not exported from Rosetta as a non
            # published upload. We log it and select the email template.
            if logger:
                logger.info(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-not-exported-from-rosetta.txt'
            import_rejected = True
            entry_to_import.setErrorOutput(
                "File was not exported from Launchpad.")
        except (BrokenTextError, TranslationFormatSyntaxError,
                TranslationFormatInvalidInputError, UnicodeDecodeError), (
                exception):
            # The import failed with a format error. We log it and select the
            # email template.
            if logger:
                logger.info(
                    'Error importing %s' % self.title, exc_info=1)
            if isinstance(exception, UnicodeDecodeError):
                template_mail = 'poimport-bad-encoding.txt'
            else:
                template_mail = 'poimport-syntax-error.txt'
            import_rejected = True
            error_text = str(exception)
            entry_to_import.setErrorOutput(error_text)
            needs_notification_for_imported = True
        except OutdatedTranslationError, exception:
            # The attached file is older than the last imported one, we ignore
            # it. We also log this problem and select the email template.
            if logger:
                logger.info('Got an old version for %s' % self.title)
            template_mail = 'poimport-got-old-version.txt'
            import_rejected = True
            error_text = str(exception)
            entry_to_import.setErrorOutput(
                "Outdated translation.  " + error_text)
        except TooManyPluralFormsError:
            if logger:
                logger.warning("Too many plural forms.")
            template_mail = 'poimport-too-many-plural-forms.txt'
            import_rejected = True
            entry_to_import.setErrorOutput("Too many plural forms.")
        else:
            # The import succeeded.  There may still be non-fatal errors
            # or warnings for individual messages (kept as a list in
            # "errors"), but we compose the text for that later.
            entry_to_import.setErrorOutput(None)

        # Prepare the mail notification.
        msgsets_imported = self.getTranslationMessages(
            TranslationMessage.was_obsolete_in_last_import == False).count()

        replacements = collect_import_info(entry_to_import, self, warnings)
        replacements.update({
            'import_title': '%s translations for %s' % (
                self.language.displayname, self.potemplate.displayname),
            'language': self.language.displayname,
            'language_code': self.language.code,
            'numberofmessages': msgsets_imported,
            })

        if error_text is not None:
            replacements['error'] = error_text

        entry_to_import.addWarningOutput(replacements['warnings'])

        if import_rejected:
            # We got an error that prevented us to import any translation, we
            # need to notify the user.
            subject = 'Import problem - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        elif len(errors) > 0:
            # There were some errors with translations.
            errorsdetails = ''
            for error in errors:
                potmsgset = error['potmsgset']
                pomessage = error['pomessage']
                error_message = error['error-message']
                errorsdetails = '%s%d. "%s":\n\n%s\n\n' % (
                    errorsdetails,
                    potmsgset.sequence,
                    error_message,
                    pomessage)

            entry_to_import.setErrorOutput(
                "Imported, but with errors:\n" + errorsdetails)

            replacements['numberoferrors'] = len(errors)
            replacements['errorsdetails'] = errorsdetails
            replacements['numberofcorrectmessages'] = (
                msgsets_imported - len(errors))

            template_mail = 'poimport-with-errors.txt'
            subject = 'Translation problems - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        else:
            # The import was successful.
            template_mail = 'poimport-confirmation.txt'
            subject = 'Translation import - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_experts
        if import_rejected:
            # There were no imports at all and the user needs to review that
            # file, we tag it as FAILED.
            entry_to_import.setStatus(
                RosettaImportStatus.FAILED, rosetta_experts)
        else:
            if (entry_to_import.is_published and
                not needs_notification_for_imported):
                # If it's a published upload (i.e. from a package or bzr
                # branch), do not send success notifications unless they
                # are needed.
                subject = None

            entry_to_import.setStatus(
                RosettaImportStatus.IMPORTED, rosetta_experts)
            # Assign karma to the importer if this is not an automatic import
            # (all automatic imports come from the rosetta expert user) and
            # comes from upstream.
            celebs = getUtility(ILaunchpadCelebrities)
            rosetta_experts = celebs.rosetta_experts
            if (entry_to_import.is_published and
                entry_to_import.importer.id != rosetta_experts.id):
                entry_to_import.importer.assignKarma(
                    'translationimportupstream',
                    product=self.potemplate.product,
                    distribution=self.potemplate.distribution,
                    sourcepackagename=self.potemplate.sourcepackagename)

            # Synchronize to database so we can calculate fresh statistics on
            # the server side.
            flush_database_updates()

            # Now we update the statistics after this new import
            self.updateStatistics()

        template = helpers.get_email_template(template_mail, 'translations')
        message = template % replacements
        return (subject, message)

    def export(self, ignore_obsolete=False, force_utf8=False):
        """See `IPOFile`."""
        translation_exporter = getUtility(ITranslationExporter)
        translation_file_data = getAdapter(
            self, ITranslationFileData, 'all_messages')
        exported_file = translation_exporter.exportTranslationFiles(
            [translation_file_data], ignore_obsolete=ignore_obsolete,
            force_utf8=force_utf8)

        try:
            file_content = exported_file.read()
        finally:
            exported_file.close()

        return file_content

    def _selectRows(self, where=None, ignore_obsolete=True):
        """Select translation message data.

        Diverged messages come before shared ones.  The exporter relies
        on this.
        """
        # Avoid circular import.
        from lp.translations.model.vpoexport import VPOExport

        # Prefetch all POTMsgSets for this template in one go.
        potmsgsets = {}
        for potmsgset in self.potemplate.getPOTMsgSets(ignore_obsolete):
            potmsgsets[potmsgset.id] = potmsgset

        # Names of columns that are selected and passed (in this order) to
        # the VPOExport constructor.
        column_names = [
            'TranslationTemplateItem.potmsgset',
            'TranslationTemplateItem.sequence',
            'TranslationMessage.comment',
            'TranslationMessage.is_current',
            'TranslationMessage.is_imported',
            'TranslationMessage.potemplate',
            'potranslation0.translation',
            'potranslation1.translation',
            'potranslation2.translation',
            'potranslation3.translation',
            'potranslation4.translation',
            'potranslation5.translation',
        ]
        columns = ', '.join(column_names)

        # Obsolete translations are marked with a sequence number of 0,
        # so they would get sorted to the front of the file during
        # export. To avoid that, sequence numbers of 0 are translated to
        # NULL and ordered to the end with NULLS LAST so that they
        # appear at the end of the file.
        sort_column_names = [
            'TranslationMessage.potemplate NULLS LAST',
            'CASE '
                'WHEN TranslationTemplateItem.sequence = 0 THEN NULL '
                'ELSE TranslationTemplateItem.sequence '
            'END NULLS LAST',
            'TranslationMessage.id',
        ]
        sort_columns = ', '.join(sort_column_names)

        main_select = "SELECT %s" % columns
        query = main_select + """
            FROM TranslationTemplateItem
            LEFT JOIN TranslationMessage ON
                TranslationMessage.potmsgset =
                    TranslationTemplateItem.potmsgset AND
                TranslationMessage.is_current IS TRUE AND
                TranslationMessage.language = %s
            """ % sqlvalues(self.language)

        for form in xrange(TranslationConstants.MAX_PLURAL_FORMS):
            alias = "potranslation%d" % form
            field = "TranslationMessage.msgstr%d" % form
            query += "LEFT JOIN POTranslation AS %s ON %s.id = %s\n" % (
                    alias, alias, field)

        template_id = quote(self.potemplate)
        conditions = [
            "TranslationTemplateItem.potemplate = %s" % template_id,
            "(TranslationMessage.potemplate IS NULL OR "
                 "TranslationMessage.potemplate = %s)" % template_id,
            ]


        if ignore_obsolete:
            conditions.append("TranslationTemplateItem.sequence <> 0")

        if where:
            conditions.append("(%s)" % where)

        query += "WHERE %s" % ' AND '.join(conditions)
        query += ' ORDER BY %s' % sort_columns

        for row in Store.of(self).execute(query):
            export_data = VPOExport(*row)
            export_data.setRefs(self, potmsgsets)
            yield export_data

    def getTranslationRows(self):
        """See `IVPOExportSet`."""
        # Only fetch rows that belong to this POFile and are "interesting":
        # they must either be in the current template (sequence != 0, so not
        # "obsolete") or be in the current imported version of the translation
        # (is_imported), or both.
        return self._selectRows(
            ignore_obsolete=False,
            where="TranslationTemplateItem.sequence <> 0 OR "
                "is_imported IS TRUE")

    def getChangedRows(self):
        """See `IVPOExportSet`."""
        return self._selectRows(where="is_imported IS FALSE")


class DummyPOFile(POFileMixIn):
    """Represents a POFile where we do not yet actually HAVE a POFile for
    that language for this template.
    """
    implements(IPOFile)

    def __init__(self, potemplate, language, owner=None):
        self.id = None
        self.potemplate = potemplate
        self.language = language
        self.description = None
        self.topcomment = None
        self.header = None
        self.fuzzyheader = False
        self.lasttranslator = None
        UTC = pytz.timezone('UTC')
        self.date_changed = None
        self.lastparsed = None
        self.owner = getUtility(ILaunchpadCelebrities).rosetta_experts

        # The default POFile owner is the Rosetta Experts team unless the
        # given owner has rights to write into that file.
        if self.canEditTranslations(owner):
            self.owner = owner

        self.path = u'unknown'
        self.datecreated = datetime.datetime.now(UTC)
        self.last_touched_pomsgset = None
        self.contributors = []
        self.from_sourcepackagename = None
        self.translation_messages = None

    def messageCount(self):
        return self.potemplate.messageCount()

    @property
    def title(self):
        """See `IPOFile`."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        tgroups = self.potemplate.translationgroups
        ret = []
        for group in tgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                ret.append(translator)
        return ret

    @property
    def translationpermission(self):
        """See `IPOFile`."""
        return self.potemplate.translationpermission

    def getTranslationsFilteredBy(self, person):
        """See `IPOFile`."""
        return None

    def getPOTMsgSetTranslated(self):
        """See `IPOFile`."""
        return EmptyResultSet()

    def getPOTMsgSetUntranslated(self):
        """See `IPOFile`."""
        return self.potemplate.getPOTMsgSets()

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        return EmptyResultSet()

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        return EmptyResultSet()

    def getPOTMsgSetWithErrors(self):
        """See `IPOFile`."""
        return EmptyResultSet()

    def getTranslationMessages(self, condition=None):
        """See `IPOFile`."""
        return EmptyResultSet()

    def hasMessageID(self, msgid):
        """See `IPOFile`."""
        raise NotImplementedError

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def unreviewedCount(self, language=None):
        """See `IPOFile`."""
        return 0

    def newCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def translatedCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def untranslatedCount(self, language=None):
        """See `IRosettaStats`."""
        return self.messageCount()

    def currentPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def rosettaPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def updatesPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def newPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def translatedPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def untranslatedPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 100.0

    def export(self, ignore_obsolete=False, force_utf8=False):
        """See `IPOFile`."""
        raise NotImplementedError

    def createMessageSetFromMessageSet(self, potmsgset):
        """See `IPOFile`."""
        raise NotImplementedError

    def getStatistics(self):
        """See `IPOFile`."""
        return (0, 0, 0, )

    def updateStatistics(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def updateHeader(self, new_header):
        """See `IPOFile`."""
        raise NotImplementedError

    def isTranslationRevisionDateOlder(self, header):
        """See `IPOFile`."""
        raise NotImplementedError

    def setPathIfUnique(self, path):
        """See `IPOFile`."""
        # Any path will do for a DummyPOFile.
        self.path = path

    def getNextToImport(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def importFromQueue(self, entry_to_import, logger=None, txn=None):
        """See `IPOFile`."""
        raise NotImplementedError

    def prepareTranslationCredits(self, potmsgset):
        """See `IPOFile`."""
        return None

    def getTranslationRows(self):
        """See `IPOFile`."""
        return []

    def getChangedRows(self):
        """See `IPOFile`."""
        return []


class POFileSet:
    implements(IPOFileSet)

    def getDummy(self, potemplate, language):
        return DummyPOFile(potemplate, language)

    def getPOFilesByPathAndOrigin(self, path, productseries=None,
                                  distroseries=None, sourcepackagename=None):
        """See `IPOFileSet`."""
        # Avoid circular imports.
        from lp.translations.model.potemplate import POTemplate

        assert productseries is not None or distroseries is not None, (
            'Either productseries or sourcepackagename arguments must be'
            ' not None.')
        assert productseries is None or distroseries is None, (
            'productseries and sourcepackagename/distroseries cannot be used'
            ' at the same time.')
        assert (
            (sourcepackagename is None and distroseries is None) or
             (sourcepackagename is not None and distroseries is not None)), (
                'sourcepackagename and distroseries must be None or not'
                   ' None at the same time.')

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        general_conditions = And(
            POFile.path == path,
            POFile.potemplate == POTemplate.id)

        if productseries is not None:
            return store.find(POFile, And(
                general_conditions,
                POTemplate.productseries == productseries))
        else:
            distro_conditions = And(
                general_conditions,
                POTemplate.distroseries == distroseries)

            # The POFile belongs to a distribution and it could come from
            # another package that its POTemplate is linked to, so we first
            # check to find it at IPOFile.from_sourcepackagename
            matches = store.find(POFile, And(
                distro_conditions,
                POFile.from_sourcepackagename == sourcepackagename))

            if not matches.is_empty():
                return matches

            # There is no pofile in that 'path' and
            # 'IPOFile.from_sourcepackagename' so we do a search using the
            # usual sourcepackagename.
            return store.find(POFile, And(
                distro_conditions,
                POTemplate.sourcepackagename == sourcepackagename))

    def getBatch(self, starting_id, batch_size):
        """See `IPOFileSet`."""
        return POFile.select(
            "id >= %s" % quote(starting_id), orderBy="id", limit=batch_size)

    def getPOFilesWithTranslationCredits(self, untranslated=False):
        """See `IPOFileSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        clauses = [
            TranslationTemplateItem.potemplateID == POFile.potemplateID,
            POTMsgSet.id == TranslationTemplateItem.potmsgsetID,
            POTMsgSet.msgid_singular == POMsgID.id,
            POMsgID.msgid.is_in(POTMsgSet.credits_message_ids)]
        if untranslated:
            message_select = Select(
                True,
                And(
                    TranslationMessage.potmsgsetID == POTMsgSet.id,
                    TranslationMessage.potemplate == None,
                    POFile.languageID == TranslationMessage.languageID,
                    TranslationMessage.is_current == True),
                (TranslationMessage))
            clauses.append(Not(Exists(message_select)))
        result = store.find((POFile, POTMsgSet), clauses)
        return result.order_by('POFile.id')

    def getPOFilesTouchedSince(self, date):
        """See `IPOFileSet`."""
        # Avoid circular imports.
        from lp.translations.model.potemplate import POTemplate
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.productseries import ProductSeries

        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

        # Find a matching POTemplate and its ProductSeries
        # and DistroSeries, if they are defined.
        MatchingPOT = ClassAlias(POTemplate)
        MatchingPOTJoin = Join(
            MatchingPOT, POFile.potemplate == MatchingPOT.id)
        MatchingProductSeries = ClassAlias(ProductSeries)
        MatchingProductSeriesJoin = LeftJoin(
            MatchingProductSeries,
            MatchingPOT.productseriesID == MatchingProductSeries.id)
        MatchingDistroSeries = ClassAlias(DistroSeries)
        MatchingDistroSeriesJoin = LeftJoin(
            MatchingDistroSeries,
            MatchingPOT.distroseriesID == MatchingDistroSeries.id)

        # Find any sharing POTemplate corresponding to MatchingPOT
        # and its ProductSeries and DistroSeries, if they are defined.
        OtherPOT = ClassAlias(POTemplate)
        OtherPOTJoin = Join(
            OtherPOT, And(OtherPOT.name == MatchingPOT.name))
        OtherProductSeries = ClassAlias(ProductSeries)
        OtherProductSeriesJoin = LeftJoin(
            OtherProductSeries,
            OtherPOT.productseriesID == OtherProductSeries.id)
        OtherDistroSeries = ClassAlias(DistroSeries)
        OtherDistroSeriesJoin = LeftJoin(
            OtherDistroSeries,
            OtherPOT.distroseriesID == OtherDistroSeries.id)

        # And find a sharing POFile corresponding to a sharing POTemplate,
        # i.e. OtherPOT.
        OtherPOFile = ClassAlias(POFile)
        OtherPOFileJoin = Join(
            OtherPOFile,
            And(OtherPOFile.languageID == POFile.languageID,
                OtherPOFile.potemplateID == OtherPOT.id))

        source = store.using(
            POFile, MatchingPOTJoin, MatchingProductSeriesJoin,
            MatchingDistroSeriesJoin, OtherPOTJoin,
            OtherProductSeriesJoin, OtherDistroSeriesJoin, OtherPOFileJoin)

        results = source.find(
            OtherPOFile,
            And(POFile.date_changed >= date,
                Or(
                    # OtherPOT is a sharing template with MatchingPOT
                    # in the same distribution and sourcepackagename.
                    And(MatchingPOT.distroseriesID is not None,
                        OtherPOT.distroseriesID is not None,
                        (MatchingDistroSeries.distributionID ==
                         OtherDistroSeries.distributionID),
                        (MatchingPOT.sourcepackagenameID ==
                         OtherPOT.sourcepackagenameID)),
                    # OtherPOT is a sharing template with MatchingPOT
                    # in the same product.
                    And(MatchingPOT.productseriesID is not None,
                        OtherPOT.productseriesID is not None,
                        (MatchingProductSeries.productID ==
                         OtherProductSeries.productID)))))
        results.config(distinct=True)
        return results


class POFileToTranslationFileDataAdapter:
    """Adapter from `IPOFile` to `ITranslationFileData`."""
    implements(ITranslationFileData)

    def __init__(self, pofile):
        self._pofile = pofile
        self.messages = self._getMessages()
        self.format = pofile.potemplate.source_file_format

    @cachedproperty
    def path(self):
        """See `ITranslationFileData`."""
        return self._pofile.path

    @cachedproperty
    def translation_domain(self):
        """See `ITranslationFileData`."""
        return self._pofile.potemplate.translation_domain

    @property
    def is_template(self):
        """See `ITranslationFileData`."""
        return False

    @cachedproperty
    def language_code(self):
        """See `ITranslationFile`."""
        if self.is_template:
            return None

        return self._pofile.language.code

    def _isWesternPluralForm(self, number, expression):
        # Western style is nplurals=2;plural=n!=1.
        if number != 2:
            return False
        if expression is None:
            return False
        # Normalize: Remove spaces.
        expression = expression.replace(' ', '')
        # Normalize: Remove enclosing brackets.
        expression = expression.strip('()')
        return expression in ('n!=1', '1!=n', 'n>1', '1<n')

    def _updateHeaderPluralInfo(self, header):
        header_nplurals = header.number_plural_forms
        database_nplurals = self._pofile.language.pluralforms
        # These checks are here to catch cases where the plural information
        # from the header might be more acurate than what we have in the
        # database. This is usually the case when the number of plural forms
        # has grown but not if it's the standard western form.
        # See bug 565294
        if header_nplurals is not None and database_nplurals is not None:
            if header_nplurals > database_nplurals:
                is_western = self._isWesternPluralForm(
                    header_nplurals, header.plural_form_expression)
                if not is_western:
                    # Use existing information from the header.
                    return
        if database_nplurals is None:
            # In all other cases we never use the plural info from the header.
            header.number_plural_forms = None
            header.plural_form_expression = None
        else:
            # We have pluralforms information for this language so we
            # update the header to be sure that we use the language
            # information from our database instead of using the one
            # that we got from upstream. We check this information so
            # we are sure it's valid.
            header.number_plural_forms = self._pofile.language.pluralforms
            header.plural_form_expression = (
                self._pofile.language.pluralexpression)

    @cachedproperty
    def header(self):
        """See `ITranslationFileData`."""
        template_header = self._pofile.potemplate.getHeader()
        translation_header = self._pofile.getHeader()
        # Update default fields based on its values in the template header.
        translation_header.updateFromTemplateHeader(template_header)
        translation_header.translation_revision_date = (
            self._pofile.date_changed)

        translation_header.comment = self._pofile.topcomment

        if self._pofile.potemplate.hasPluralMessage():
            self._updateHeaderPluralInfo(translation_header)
        if (self._pofile.lasttranslator is not None):
            email = self._pofile.lasttranslator.safe_email_or_blank
            if not email:
                # We are supposed to have always a valid email address, but
                # with removed accounts or people not wanting to show his
                # email that's not true anymore so we just set it to 'Unknown'
                # to note we don't know it.
                email = 'Unknown'
            displayname = self._pofile.lasttranslator.displayname
            translation_header.setLastTranslator(email, name=displayname)

        # We need to tag every export from Launchpad so we know whether a
        # later upload should change every translation in our database or
        # that we got a change between the export and the upload with
        # modifications.
        UTC = pytz.timezone('UTC')
        datetime_now = datetime.datetime.now(UTC)
        translation_header.launchpad_export_date = datetime_now

        return translation_header

    def _getMessages(self, changed_rows_only=False):
        """Return a list of `ITranslationMessageData` for the `IPOFile`
        adapted."""
        pofile = self._pofile
        # Get all rows related to this file. We do this to speed the export
        # process so we have a single DB query to fetch all needed
        # information.
        if changed_rows_only:
            rows = pofile.getChangedRows()
        else:
            rows = pofile.getTranslationRows()

        messages = []
        diverged_messages = set()
        for row in rows:
            assert row.pofile == pofile, 'Got a row for a different IPOFile.'
            assert row.sequence != 0 or row.is_imported, (
                "Got uninteresting row.")

            msg_key = (row.msgid_singular, row.msgid_plural, row.context)
            if row.diverged is not None:
                diverged_messages.add(msg_key)
            else:
                # If we are exporting a shared message, make sure we
                # haven't added a diverged one to the list already.
                if msg_key in diverged_messages:
                    continue

            # Create new message set
            msgset = TranslationMessageData()
            msgset.is_obsolete = (row.sequence == 0)
            msgset.msgid_singular = row.msgid_singular
            msgset.singular_text = row.potmsgset.singular_text
            msgset.msgid_plural = row.msgid_plural
            msgset.plural_text = row.potmsgset.plural_text

            forms = list(enumerate([
                getattr(row, "translation%d" % form)
                for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)]))
            max_forms = pofile.plural_forms
            for (pluralform, translation) in forms[:max_forms]:
                if translation is not None:
                    msgset.addTranslation(pluralform, translation)

            msgset.context = row.context
            msgset.comment = row.comment
            msgset.source_comment = row.source_comment
            msgset.file_references = row.file_references

            if row.flags_comment:
                msgset.flags = set([
                    flag.strip()
                    for flag in row.flags_comment.split(',')
                    if flag])

            messages.append(msgset)

        return messages


class POFileToChangedFromPackagedAdapter(POFileToTranslationFileDataAdapter):
    """Adapter from `IPOFile` to `ITranslationFileData`."""

    def __init__(self, pofile):
        self._pofile = pofile
        self.messages = self._getMessages(True)
