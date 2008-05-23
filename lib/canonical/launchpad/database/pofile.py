# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212,W0231

"""`SQLObject` implementation of `IPOFile` interface."""

__metaclass__ = type
__all__ = [
    'POFile',
    'DummyPOFile',
    'POFileSet',
    'POFileToTranslationFileDataAdapter',
    'POFileTranslator',
    ]

import datetime
import pytz
from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLMultipleJoin
    )
from zope.interface import implements
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import (
    SQLBase, flush_database_updates, quote, quote_like, sqlvalues)
from canonical.launchpad import helpers
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.translationmessage import (
    DummyTranslationMessage, make_plurals_sql_fragment, TranslationMessage)
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IPersonSet, IPOFile, IPOFileSet, IPOFileTranslator,
    ITranslationExporter, ITranslationFileData, ITranslationImporter,
    IVPOExportSet, NotExportedFromLaunchpad, NotFoundError,
    OutdatedTranslationError, RosettaImportStatus, TooManyPluralFormsError,
    TranslationConstants, TranslationFormatInvalidInputError,
    TranslationFormatSyntaxError, TranslationPermission,
    TranslationValidationStatus)
from canonical.launchpad.translationformat import TranslationMessageData
from canonical.launchpad.webapp import canonical_url
from canonical.librarian.interfaces import ILibrarianClient


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

    # Finally, check whether the user is member of the translation team or
    # owner for the given PO file.
    translators = [t.translator for t in pofile.translators]
    return _check_translation_perms(
        pofile.translationpermission,
        translators,
        person) or person.inTeam(pofile.owner)

def _can_add_suggestions(pofile, person):
    """Whether a person is able to add suggestions.

    Any user that can edit translations can add suggestions, the others will
    be able to add suggestions only if the permission is not CLOSED.
    """
    return (_can_edit_translations(pofile, person) or
            pofile.translationpermission != TranslationPermission.CLOSED)


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

    def getHeader(self):
        """See `IPOFile`."""
        translation_importer = getUtility(ITranslationImporter)
        format_importer = translation_importer.getTranslationFormatImporter(
            self.potemplate.source_file_format)
        header = format_importer.getHeaderFromString(self.header)
        header.comment = self.topcomment
        header.has_plural_forms = self.potemplate.hasPluralMessage()
        return header

    def getCurrentTranslationMessage(self, msgid_text, context=None,
                                     ignore_obsolete=False):
        """See `IPOFile`."""
        if not isinstance(msgid_text, unicode):
            raise AssertionError(
                "Can't index with type %s. (Must be unicode.)"
                % type(msgid_text))

        potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(key=msgid_text,
                                                            context=context)
        return self.getCurrentTranslationMessageFromPOTMsgSet(
            potmsgset, ignore_obsolete=ignore_obsolete)

    def findPOTMsgSetsContaining(self, text):
        """See `IPOFile`."""
        clauses = [
            'POTMsgSet.potemplate = %s' % sqlvalues(self.potemplate),
            # Only count the number of POTMsgSet that are current.
            'POTMsgSet.sequence > 0',
            ]

        if text is not None:
            assert len(text) > 1, (
                "You can not search for strings shorter than 2 characters.")

            english_match = """
            -- Step 1: find POTMsgSets with msgid_singular containing `text`.
            -- To avoid seqscans on POMsgID table (what LIKE usually does),
            -- we do ILIKE comparison on them in a subselect first filtered
            -- by this POTemplate.
               ((POTMsgSet.msgid_singular IS NOT NULL AND
                 POTMsgSet.msgid_singular IN (
                   SELECT POMsgID.id FROM POMsgID
                     WHERE id IN (
                       SELECT DISTINCT(msgid_singular)
                         FROM POTMsgSet
                         WHERE POTMsgSet.potemplate=%s
                     ) AND
                     msgid ILIKE '%%' || %s || '%%')) OR
            -- Step 1b: like above, just on msgid_plural.
                (POTMsgSet.msgid_plural IS NOT NULL AND
                 POTMsgSet.msgid_plural IN (
                   SELECT POMsgID.id FROM POMsgID
                     WHERE id IN (
                       SELECT DISTINCT(msgid_plural)
                         FROM POTMsgSet
                         WHERE POTMsgSet.potemplate=%s
                     ) AND
                     msgid ILIKE '%%' || %s || '%%'))
               )""" % (quote(self.potemplate), quote_like(text),
                       quote(self.potemplate), quote_like(text))

            # Do not look for translations in a DummyPOFile.
            if self.id is not None:
                search_clauses = [english_match]
                for plural_form in range(self.plural_forms):
                    translation_match = """
                    -- Step 2: find translations containing `text`.
                    -- Like above, to avoid seqscans on POTranslation table,
                    -- we do ILIKE comparison on them in a subselect which is
                    -- first filtered by the POFile.
                    (POTMsgSet.id IN (
                      SELECT POTMsgSet.id FROM POTMsgSet
                        JOIN TranslationMessage
                          ON TranslationMessage.potmsgset=POTMsgSet.id
                        WHERE
                          TranslationMessage.pofile=%(pofile)s AND
                          TranslationMessage.msgstr%(plural_form)d IN (
                            SELECT POTranslation.id FROM POTranslation WHERE
                              POTranslation.id IN (
                                SELECT DISTINCT(msgstr%(plural_form)d)
                                  FROM TranslationMessage
                                  WHERE TranslationMessage.pofile=%(pofile)s
                              ) AND
                              POTranslation.translation
                                ILIKE '%%' || %(text)s || '%%')
                              ))""" % dict(pofile=quote(self),
                                           plural_form=plural_form,
                                           text=quote_like(text))
                    search_clauses.append(translation_match)

                clauses.append("(" + " OR ".join(search_clauses) + ")")
            else:
                clauses.append(english_match)

        return POTMsgSet.select(" AND ".join(clauses),
                                orderBy='sequence')


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
        validator=public_person_validator, notNull=False, default=None)

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
        validator=public_person_validator, notNull=True)
    variant = StringCol(dbName='variant',
                        notNull=False,
                        default=None)
    path = StringCol(dbName='path',
                     notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    from_sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='from_sourcepackagename', notNull=False, default=None)

    # joins
    translation_messages = SQLMultipleJoin(
        'TranslationMessage', joinColumn='pofile', orderBy='id')

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
        return getUtility(IPersonSet).getPOFileContributors(self)

    def prepareTranslationCredits(self, potmsgset):
        """See `IPOFile`."""
        msgid = potmsgset.singular_text
        assert potmsgset.is_translation_credit, (
            "Calling prepareTranslationCredits on a message with "
            "msgid '%s'." % msgid)
        imported = potmsgset.getImportedTranslationMessage(self.language)
        if imported is None:
            text = None
        else:
            text = imported.translations[0]
        if msgid in [u'_: EMAIL OF TRANSLATORS\nYour emails', u'Your emails']:
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
        elif msgid in [u'_: NAME OF TRANSLATORS\nYour names', u'Your names']:
            names = []
            if text is not None:
                names.append(text)
            # Add an empty name as a separator, and 'Launchpad
            # Contributions' header; see bug #133817 for details.
            names.extend([u'',
                          u'Launchpad Contributions:'])
            names.extend([
                contributor.displayname
                for contributor in self.contributors])
            return u','.join(names)
        elif (msgid in [u'translation-credits',
                        u'translator-credits',
                        u'translator_credits']):
            if len(list(self.contributors)):
                if text is None:
                    text = u''
                else:
                    text += u'\n\n'

                text += 'Launchpad Contributions:'
                for contributor in self.contributors:
                    text += ("\n  %s %s" %
                             (contributor.displayname,
                              canonical_url(contributor)))
            return text
        else:
            raise AssertionError(
                "Calling prepareTranslationCredits on a message with "
                "msgid '%s'." % (msgid))

    def canEditTranslations(self, person):
        """See `IPOFile`."""
        return _can_edit_translations(self, person)

    def canAddSuggestions(self, person):
        """See `IPOFile`."""
        return _can_add_suggestions(self, person)

    def translated(self):
        """See `IPOFile`."""
        raise NotImplementedError
        # return iter(TranslationMessage.select('''
        #     POMsgSet.pofile = %d AND
        #     POMsgSet.iscomplete=TRUE AND
        #     POMsgSet.potmsgset = POTMsgSet.id AND
        #     POTMsgSet.sequence > 0''' % self.id,
        #     clauseTables = ['POMsgSet']
        #     ))

    def untranslated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def __iter__(self):
        """See `IPOFile`."""
        return iter(self.currentMessageSets())

    def getCurrentTranslationMessageFromPOTMsgSet(self, potmsgset,
                                                  ignore_obsolete=False):
        """See `IPOFile`."""
        if potmsgset is None or (ignore_obsolete and potmsgset.sequence <= 0):
            # There is no IPOTMsgSet for this id.
            return None

        current = potmsgset.getCurrentTranslationMessage(self.language)
        if current is None:
            return DummyTranslationMessage(self, potmsgset)
        else:
            return current

    def __getitem__(self, msgid_text):
        """See `IPOFile`."""
        translation_message = self.getCurrentTranslationMessage(
            unicode(msgid_text), ignore_obsolete=True)
        if translation_message is None:
            raise NotFoundError(msgid_text)
        else:
            return translation_message

    def getTranslationsFilteredBy(self, person):
        """See `IPOFile`."""
        # We are displaying translations grouped by POTMsgSets,
        # but since the most common case will be having a single
        # TranslationMessage per POTMsgSet, we are issuing a slightly
        # faster SQL query by avoiding a join with POTMsgSet.
        assert person is not None, "You must provide a person to filter by."
        return TranslationMessage.select(
            """
            TranslationMessage.pofile = %s AND
            TranslationMessage.submitter = %s
            """ % sqlvalues(self, person),
            orderBy=['potmsgset', '-date_created'])

    def getPOTMsgSetTranslated(self):
        """See `IPOFile`."""
        query = [
            'POTMsgSet.potemplate = %s' % sqlvalues(self.potemplate),
            'POTMsgSet.sequence > 0',
            'TranslationMessage.potmsgset = POTMsgSet.id',
            'TranslationMessage.pofile = %s' % sqlvalues(self),
            'TranslationMessage.is_current',
            'NOT TranslationMessage.is_fuzzy']
        self._appendCompletePluralFormsConditions(query)

        return POTMsgSet.select(
            ' AND '.join(query), clauseTables=['TranslationMessage'],
            orderBy='POTMsgSet.sequence')

    def getPOTMsgSetFuzzy(self):
        """See `IPOFile`."""
        return POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_current AND
            TranslationMessage.is_fuzzy
            ''' % sqlvalues(self.potemplate, self),
            clauseTables=['TranslationMessage'], orderBy='POTmsgSet.sequence')

    def getPOTMsgSetUntranslated(self):
        """See `IPOFile`."""
        incomplete_check = ['TranslationMessage.msgstr0 IS NULL']
        # Plural forms only matter if we are in a message with a msgid_plural.
        incomplete_plurals_check = ['FALSE']
        for plural_form in range(self.plural_forms)[1:]:
            incomplete_plurals_check.append(
                'TranslationMessage.msgstr%d IS NULL' % plural_form)
        incomplete_check.append(
            '(POTMsgSet.msgid_plural IS NOT NULL AND (%s))' % ' OR '.join(
                incomplete_plurals_check))

        # We use a subselect to allow the LEFT OUTER JOIN
        query = """POTMsgSet.id IN (
            SELECT POTMsgSet.id
            FROM POTMsgSet
            LEFT OUTER JOIN TranslationMessage ON
                TranslationMessage.potmsgset = POTMsgSet.id AND
                TranslationMessage.pofile = %s AND
                TranslationMessage.is_current IS TRUE
            WHERE
                POTMsgSet.sequence > 0 AND
                POTMsgSet.potemplate = %s AND
                (TranslationMessage.id IS NULL OR
                 (NOT TranslationMessage.is_fuzzy AND (%s))))
            """ % (quote(self), quote(self.potemplate),
                   ' OR '.join(incomplete_check))
        return POTMsgSet.select(query, orderBy='POTMsgSet.sequence')

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        # A POT set has "new" suggestions if there is a non current
        # TranslationMessage newer than the current reviewed one.
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_current IS NOT TRUE AND
            TranslationMessage.date_created > COALESCE(
                (SELECT COALESCE(current.date_reviewed, current.date_created)
                    FROM TranslationMessage current
                    WHERE current.potmsgset = POTMsgSet.id AND
                          current.pofile = %s AND
                          current.is_current IS TRUE),
                TIMESTAMP '1970-01-01 00:00:00')
            ''' % sqlvalues(self.potemplate, self, self),
            clauseTables=['TranslationMessage'],
            orderBy='POTmsgSet.sequence',
            distinct=True)

        return results

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        # POT set has been changed in Launchpad if it contains active
        # translation which didn't come from a published package
        # (iow, it's different from a published translation: this only
        # lists translations which have actually changed in LP, not
        # translations which are 'new' and only exist in LP).
        # XXX CarlosPerelloMarin 2007-11-29 bug=165218: Once bug #165218 is
        # properly fixed (that is, we no longer create empty
        # TranslationMessage objects for empty strings in imported files), all
        # the 'imported.msgstr? IS NOT NULL' conditions can be removed because
        # they will not be needed anymore.
        not_nulls = make_plurals_sql_fragment(
            "imported.msgstr%(form)d IS NOT NULL", "OR")

        results = POTMsgSet.select('''POTMsgSet.id IN (
            SELECT POTMsgSet.id
            FROM POTMsgSet
            JOIN TranslationMessage AS imported ON
                POTMsgSet.id = imported.potmsgset AND
                imported.pofile = %s AND
                imported.is_imported IS TRUE AND
                NOT imported.was_fuzzy_in_last_import
            JOIN TranslationMessage AS current ON
                POTMsgSet.id = current.potmsgset AND
                imported.id <> current.id AND
                current.pofile = imported.pofile AND
                current.is_current IS TRUE
            WHERE
                POTMsgSet.sequence > 0 AND
                POTMsgSet.potemplate = %s AND
                (%s))
            ''' % (quote(self), quote(self.potemplate), not_nulls),
            orderBy='POTmsgSet.sequence')

        return results

    def getPOTMsgSetWithErrors(self):
        """See `IPOFile`."""
        return POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_imported IS TRUE AND
            TranslationMessage.validation_status <> %s
            ''' % sqlvalues(self.potemplate.id, self.id,
                            TranslationValidationStatus.OK),
            clauseTables=['TranslationMessage'],
            orderBy='POTmsgSet.sequence')

    def hasMessageID(self, messageID):
        """See `IPOFile`."""
        return TranslationMessage.select("""
            TranslationMessage.pofile = %s AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            POTMsgSet.msgid_singular = %s""" % sqlvalues(
                self, messageID)).count() > 0

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

    @property
    def fuzzy_count(self):
        """See `IPOFile`."""
        return TranslationMessage.select("""
            TranslationMessage.pofile = %s AND
            TranslationMessage.is_fuzzy AND
            TranslationMessage.is_current AND
            TranslationMessage.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            """ % sqlvalues(self), clauseTables=['POTMsgSet']).count()

    def getStatistics(self):
        """See `IPOFile`."""
        return (
            self.currentcount,
            self.updatescount,
            self.rosettacount,
            self.unreviewed_count)

    def _appendCompletePluralFormsConditions(self, query):
        """Add conditions to implement ITranslationMessage.is_complete in SQL.

        :param query: A list of AND SQL conditions where the implementation of
            ITranslationMessage.is_complete will be appended as SQL
            conditions.
        """
        query.append('TranslationMessage.msgstr0 IS NOT NULL')
        if self.language.pluralforms > 1:
            plurals_query = ' AND '.join(
                'TranslationMessage.msgstr%d IS NOT NULL' % plural_form
                    for plural_form in range(1, self.plural_forms))
            query.append(
                '(POTMsgSet.msgid_plural IS NULL OR (%s))' % plurals_query)
        return query

    def updateStatistics(self):
        """See `IPOFile`."""
        # make sure all the data is in the db
        flush_database_updates()

        # Get the number of translations that we got from imports.
        query = ['TranslationMessage.pofile = %s' % sqlvalues(self),
                 'TranslationMessage.is_imported IS TRUE',
                 'NOT TranslationMessage.was_fuzzy_in_last_import',
                 'TranslationMessage.potmsgset = POTMsgSet.id',
                 'POTMsgSet.sequence > 0']
        self._appendCompletePluralFormsConditions(query)
        current = TranslationMessage.select(
            ' AND '.join(query), clauseTables=['POTMsgSet']).count()

        # Get the number of translations that we have updated from what we got
        # from imports.
        updates = self.getPOTMsgSetChangedInLaunchpad().count()

        # Get the number of new translations in Launchpad that imported ones
        # were not translated.
        query = [
            'TranslationMessage.pofile = %s' % sqlvalues(self),
            'NOT TranslationMessage.is_fuzzy',
            'TranslationMessage.is_current IS TRUE']
        # Check only complete translations.  For messages with only a single
        # msgid, that's anything with a singular translation; for ones with a
        # plural form, it's the number of plural forms the language supports.
        self._appendCompletePluralFormsConditions(query)
        # XXX CarlosPerelloMarin 2007-11-29 bug=165218: Once bug #165218 is
        # properly fixed (that is, we no longer create empty
        # TranslationMessage objects for empty strings in imported files), all
        # the 'imported.msgstr? IS NOT NULL' conditions can be removed because
        # they will not be needed anymore.
        not_nulls = make_plurals_sql_fragment(
            "imported.msgstr%(form)d IS NOT NULL", "OR")
        query.append('''NOT EXISTS (
            SELECT TranslationMessage.id
            FROM TranslationMessage AS imported
            WHERE
                imported.potmsgset = TranslationMessage.potmsgset AND
                imported.pofile = TranslationMessage.pofile AND
                imported.is_imported IS TRUE AND
                NOT imported.was_fuzzy_in_last_import AND
                (%s))''' % not_nulls)
        query.append('TranslationMessage.potmsgset = POTMsgSet.id')
        query.append('POTMsgSet.sequence > 0')
        rosetta = TranslationMessage.select(
            ' AND '.join(query), clauseTables=['POTMsgSet']).count()

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

    def importFromQueue(self, entry_to_import, logger=None):
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
        librarian_client = getUtility(ILibrarianClient)

        import_file = librarian_client.getFileByAlias(
            entry_to_import.content.id)

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
        error_text = None
        try:
            errors = translation_importer.importFile(entry_to_import, logger)
        except NotExportedFromLaunchpad:
            # We got a file that was not exported from Rosetta as a non
            # published upload. We log it and select the email template.
            if logger:
                logger.info(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-not-exported-from-rosetta.txt'
            import_rejected = True
        except (TranslationFormatSyntaxError,
                TranslationFormatInvalidInputError), exception:
            # The import failed with a format error. We log it and select the
            # email template.
            if logger:
                logger.info(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-syntax-error.txt'
            import_rejected = True
            error_text = str(exception)
        except OutdatedTranslationError:
            # The attached file is older than the last imported one, we ignore
            # it. We also log this problem and select the email template.
            if logger:
                logger.info('Got an old version for %s' % self.title)
            template_mail = 'poimport-got-old-version.txt'
            import_rejected = True
        except TooManyPluralFormsError:
            if logger:
                logger.warning("Too many plural forms.")
            template_mail = 'poimport-too-many-plural-forms.txt'
            import_rejected = True

        # Prepare the mail notification.
        msgsets_imported = TranslationMessage.select(
            'was_obsolete_in_last_import IS FALSE AND pofile=%s' %
            (sqlvalues(self.id))).count()

        replacements = {
            'dateimport': entry_to_import.dateimported.strftime('%F %R%z'),
            'elapsedtime': entry_to_import.getElapsedTimeText(),
            'file_link': entry_to_import.content.http_url,
            'import_title': '%s translations for %s' % (
                self.language.displayname, self.potemplate.displayname),
            'importer': entry_to_import.importer.displayname,
            'language': self.language.displayname,
            'language_code': self.language.code,
            'max_plural_forms': TranslationConstants.MAX_PLURAL_FORMS,
            'numberofmessages': msgsets_imported,
            'template': self.potemplate.displayname,
            }

        if error_text is not None:
            replacements['error'] = error_text

        if import_rejected:
            # We got an error that prevented us to import any translation, we
            # need to notify the user.
            subject = 'Import problem - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        elif len(errors):
            # There were some errors with translations.
            errorsdetails = ''
            for error in errors:
                pofile = error['pofile']
                potmsgset = error['potmsgset']
                pomessage = error['pomessage']
                error_message = error['error-message']
                errorsdetails = '%s%d. "%s":\n\n%s\n\n' % (
                    errorsdetails,
                    potmsgset.sequence,
                    error_message,
                    pomessage)

            replacements['numberoferrors'] = len(errors)
            replacements['errorsdetails'] = errorsdetails
            replacements['numberofcorrectmessages'] = (msgsets_imported -
                len(errors))

            template_mail = 'poimport-with-errors.txt'
            subject = 'Translation problems - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        else:
            # The import was successful.
            template_mail = 'poimport-confirmation.txt'
            subject = 'Translation import - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)

        if import_rejected:
            # There were no imports at all and the user needs to review that
            # file, we tag it as FAILED.
            entry_to_import.status = RosettaImportStatus.FAILED
        else:
            entry_to_import.status = RosettaImportStatus.IMPORTED
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

        template = helpers.get_email_template(template_mail)
        message = template % replacements
        return (subject, message)

    def export(self, ignore_obsolete=False, force_utf8=False):
        """See `IPOFile`."""
        # Get the exporter for this translation.
        translation_exporter = getUtility(ITranslationExporter)
        translation_format_exporter = (
            translation_exporter.getExporterProducingTargetFileFormat(
                self.potemplate.source_file_format))

        # Get the export file.
        exported_file = translation_format_exporter.exportTranslationFiles(
            [ITranslationFileData(self)], ignore_obsolete, force_utf8)

        try:
            file_content = exported_file.read()
        finally:
            exported_file.close()

        return file_content


class DummyPOFile(POFileMixIn):
    """Represents a POFile where we do not yet actually HAVE a POFile for
    that language for this template.
    """
    implements(IPOFile)

    def __init__(self, potemplate, language, variant=None, owner=None):
        self.id = None
        self.potemplate = potemplate
        self.language = language
        self.variant = variant
        self.description = None
        self.topcomment = None
        self.header = None
        self.fuzzyheader = False
        self.lasttranslator = None
        UTC = pytz.timezone('UTC')
        self.date_changed  = None
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

    def __getitem__(self, msgid_text):
        translation_message = self.getCurrentTranslationMessage(
            msgid_text, ignore_obsolete=True)
        if translation_message is None:
            raise NotFoundError(msgid_text)
        else:
            return translation_message

    def __iter__(self):
        """See `IPOFile`."""
        return iter(self.currentMessageSets())

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

    def canEditTranslations(self, person):
        """See `IPOFile`."""
        return _can_edit_translations(self, person)

    def canAddSuggestions(self, person):
        """See `IPOFile`."""
        return _can_add_suggestions(self, person)

    def getCurrentTranslationMessageFromPOTMsgSet(self, potmsgset,
                                                  ignore_obsolete=False):
        """See `IPOFile`."""
        if potmsgset is None or (ignore_obsolete and potmsgset.sequence <= 0):
            # There is no IPOTMsgSet for this id.
            return None

        return DummyTranslationMessage(self, potmsgset)

    def emptySelectResults(self):
        return POFile.select("1=2")

    def getTranslationsFilteredBy(self, person):
        """See `IPOFile`."""
        return None

    def getPOTMsgSetTranslated(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetFuzzy(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetUntranslated(self):
        """See `IPOFile`."""
        return self.potemplate.getPOTMsgSets()

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetWithErrors(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

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

    def nonUpdatesCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def translatedCount(self, language=None):
        """See `IRosettaStats`."""
        return 0

    def untranslatedCount(self, language=None):
        """See `IRosettaStats`."""
        return self.messageCount()

    @property
    def fuzzy_count(self):
        """See `IPOFile`."""
        return 0

    def currentPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def rosettaPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def updatesPercentage(self, language=None):
        """See `IRosettaStats`."""
        return 0.0

    def nonUpdatesPercentage(self, language=None):
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

    def translated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def untranslated(self):
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

    def importFromQueue(self, entry_to_import, logger=None):
        """See `IPOFile`."""
        raise NotImplementedError

    def prepareTranslationCredits(self, potmsgset):
        """See `IPOFile`."""
        return None

class POFileSet:
    implements(IPOFileSet)

    def getPOFilesPendingImport(self):
        """See `IPOFileSet`."""
        results = POFile.selectBy(
            rawimportstatus=RosettaImportStatus.PENDING,
            orderBy='-daterawimport')

        for pofile in results:
            yield pofile

    def getDummy(self, potemplate, language):
        return DummyPOFile(potemplate, language)

    def getPOFileByPathAndOrigin(self, path, productseries=None,
        distroseries=None, sourcepackagename=None):
        """See `IPOFileSet`."""
        assert productseries is not None or distroseries is not None, (
            'Either productseries or sourcepackagename arguments must be'
            ' not None.')
        assert productseries is None or distroseries is None, (
            'productseries and sourcepackagename/distroseries cannot be used'
            ' at the same time.')
        assert ((sourcepackagename is None and distroseries is None) or
                (sourcepackagename is not None and distroseries is not None)
                ), ('sourcepackagename and distroseries must be None or not'
                   ' None at the same time.')

        if productseries is not None:
            return POFile.selectOne('''
                POFile.path = %s AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.productseries = %s''' % sqlvalues(
                    path, productseries.id),
                clauseTables=['POTemplate'])
        else:
            # The POFile belongs to a distribution and it could come from
            # another package that its POTemplate is linked to, so we first
            # check to find it at IPOFile.from_sourcepackagename
            pofile = POFile.selectOne('''
                POFile.path = %s AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distroseries = %s AND
                POFile.from_sourcepackagename = %s''' % sqlvalues(
                    path, distroseries.id, sourcepackagename.id),
                clauseTables=['POTemplate'])

            if pofile is not None:
                return pofile

            # There is no pofile in that 'path' and
            # 'IPOFile.from_sourcepackagename' so we do a search using the
            # usual sourcepackagename.
            return POFile.selectOne('''
                POFile.path = %s AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distroseries = %s AND
                POTemplate.sourcepackagename = %s''' % sqlvalues(
                    path, distroseries.id, sourcepackagename.id),
                clauseTables=['POTemplate'])

    def getBatch(self, starting_id, batch_size):
        """See `IPOFileSet`."""
        return POFile.select(
            "id >= %s" % quote(starting_id), orderBy="id", limit=batch_size)


class POFileTranslator(SQLBase):
    """See `IPOFileTranslator`."""

    implements(IPOFileTranslator)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    latest_message = ForeignKey(foreignKey='TranslationMessage',
        dbName='latest_message', notNull=True)
    date_last_touched = UtcDateTimeCol(dbName='date_last_touched',
        notNull=False, default=None)


class POFileToTranslationFileDataAdapter:
    """Adapter from `IPOFile` to `ITranslationFileData`."""
    implements(ITranslationFileData)

    def __init__(self, pofile):
        self._pofile = pofile
        self.messages = self._getMessages()

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

    @cachedproperty
    def header(self):
        """See `ITranslationFileData`."""
        template_header = self._pofile.potemplate.getHeader()
        translation_header = self._pofile.getHeader()
        # Update default fields based on its values in the template header.
        translation_header.updateFromTemplateHeader(template_header)
        date_reviewed = None
        translation_header.translation_revision_date = (
            self._pofile.date_changed)

        translation_header.comment = self._pofile.topcomment

        if self._pofile.potemplate.hasPluralMessage():
            number_plural_forms = None
            plural_form_expression = None
            if self._pofile.language.pluralforms is not None:
                # We have pluralforms information for this language so we
                # update the header to be sure that we use the language
                # information from our database instead of use the one
                # that we got from upstream. We check this information so
                # we are sure it's valid.
                number_plural_forms = self._pofile.language.pluralforms
                plural_form_expression = (
                    self._pofile.language.pluralexpression)

            translation_header.number_plural_forms = number_plural_forms
            translation_header.plural_form_expression = plural_form_expression

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

    def _getMessages(self):
        """Return a list of `ITranslationMessageData` for the `IPOFile`
        adapted."""
        pofile = self._pofile
        # Get all rows related to this file. We do this to speed the export
        # process so we have a single DB query to fetch all needed
        # information.
        rows = getUtility(IVPOExportSet).get_pofile_rows(pofile)

        messages = []

        for row in rows:
            assert row.pofile == pofile, 'Got a row for a different IPOFile.'
            assert row.sequence != 0 or row.is_imported, (
                "Got uninteresting row.")

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
                    if flag
                    ])

            if row.is_fuzzy:
                msgset.flags.add('fuzzy')

            messages.append(msgset)

        return messages
