# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POFile',
    'DummyPOFile',
    'POFileSet',
    'POFileTranslator',
    ]

import StringIO
import logging
from zope.interface import implements
from zope.component import getUtility
from urllib2 import URLError
from sqlobject import (
    ForeignKey, IntCol, StringCol, BoolCol, SQLObjectNotFound, SQLMultipleJoin
    )

from canonical.config import config
from canonical.database.sqlbase import (
    cursor, SQLBase, flush_database_updates, quote, sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW
from canonical.lp.dbschema import (
    RosettaImportStatus, TranslationPermission, TranslationValidationStatus)
from canonical.launchpad import helpers
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.mailnotification import MailWrapper
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ILibraryFileAliasSet, IPersonSet, IPOFile,
    IPOFileSet, IPOFileTranslator, IPOTemplateExporter, ITranslationImporter,
    NotExportedFromLaunchpad, NotFoundError, OldTranslationImported,
    TranslationFormatSyntaxError, TranslationFormatInvalidInputError,
    UnknownTranslationRevisionDate, ZeroLengthPOExportError)
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.pomsgset import POMsgSet, DummyPOMsgSet
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.posubmission import POSubmission
from canonical.launchpad.database.translationimportqueue import (
    TranslationImportQueueEntry)

from canonical.launchpad.webapp import canonical_url

from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.translationformat import POHeader
from canonical.librarian.interfaces import (
    ILibrarianClient, UploadFailed)


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
    If the IPOFile is for an IProductSeries, the owner of the IProduct has
    also permissions.
    Any other mortal will have rights depending on if he/she is on the right
    translation team for the given IPOFile.translationpermission and the
    language associated with this IPOFile.
    """
    # If the person is None, then they cannot edit
    if person is None:
        return False

    # XXX Carlos Perello Marin 2006-02-07 bug=4814: 
    # We should not check the permissions here but use the standard
    # security system.

    # XXX Carlos Perello Marin 2006-02-08 bug=30789: 
    # The check person.id == rosetta_experts.id must be removed as soon as
    # the is closed.

    # Rosetta experts and admins can always edit translations.
    admins = getUtility(ILaunchpadCelebrities).admin
    rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert
    if (person.inTeam(admins) or person.inTeam(rosetta_experts) or
        person.id == rosetta_experts.id):
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
            pofile.translationpermission <> TranslationPermission.CLOSED)


class POFileMixIn(RosettaStats):
    """Base class for `POFile` and `DummyPOFile`.

    Provides machinery for retrieving `POMsgSet`s and populating their
    submissions caches.  That machinery is needed even for `DummyPOFile`s.
    """

    def getMsgSetsForPOTMsgSets(self, potmsgsets):
        """See `IPOFile`."""
        if potmsgsets is None:
            return {}
        potmsgsets = list(potmsgsets)
        if not potmsgsets:
            return {}

        # Retrieve existing POMsgSets matching potmsgsets (one each).
        ids_as_sql = ','.join(
            quote(potmsgset) for potmsgset in potmsgsets)
        existing_msgsets = []
        if self.id is not None:
            existing_msgsets = POMsgSet.select(
                "potmsgset in (%s) AND pofile = %s"
                % (ids_as_sql, quote(self)))

        result = dict((pomsgset.potmsgset, pomsgset)
                      for pomsgset in existing_msgsets)

        dummies = {}
        language_code = self.language.code
        variant = self.variant
        for potmsgset in potmsgsets:
            if not potmsgset in result:
                dummy = potmsgset.getDummyPOMsgSet(language_code, variant)
                dummies[potmsgset] = dummy

        cache = self._getRelatedSubmissions(result.values(), dummies.values())

        result.update(dummies)

        for pomsgset in result.values():
            pomsgset.initializeSubmissionsCaches(cache[pomsgset])

        return result

    def _getRelatedSubmissions(self, stored_pomsgsets, dummy_pomsgsets):
        """Find all POSubmissions that the listed POMsgSets may want to cache.

        Result is a dict mapping each of these POMsgSets to a list of all
        POSubmissions that are relevant to it.  Each of the lists is in
        newest-to-oldest order.

        :param stored_pomsgsets: List of pomsgsets that are already present in
            the database, and whose in-memory caches are to be populated.
        :param dummy_pomsgsets: List of pomsgsets that have not yet been
            stored in the database, and whose in-memory caches are to be
            populated.
        """
        all_pomsgsets = stored_pomsgsets + dummy_pomsgsets

        # We'll be mapping each POMsgSet from all_pomsgsets to a list of
        # submissions that may be relevant to it in some way, and that it will
        # wish to cache.
        result = dict((msgset, []) for msgset in all_pomsgsets)
        if not all_pomsgsets:
            return result

        # For each primemsgid we see, remember which of our input msgsets were
        # looking for suggestions on that primemsgid.
        takers_for_primemsgid = dict(
            (msgset.potmsgset.primemsgid_ID, [])
            for msgset in all_pomsgsets)
        for pomsgset in all_pomsgsets:
            primemsgid = pomsgset.potmsgset.primemsgid_ID
            takers_for_primemsgid[primemsgid].append(pomsgset)

        # We work in three steps:
        #
        # 1. Retrieve from the database all ids of POSubmissions that might be
        # relevant to our msgsets, and the primemsgids of their potmsgsets
        # which will be essential to step 3.
        #
        # 2. Load all relevant submissions from the database.
        #
        # 3. Sort out which submissions are relevant to which pomsgsets from
        # our parameters stored_pomsgsets and dummy_pomsgsets.  This depends
        # on knowing the primemsgids of the potmsgsets they are attached to,
        # but we don't want to retrieve all those potmsgsets just to get that
        # information.

        # XXX: JeroenVermeulen 2007-06-11: In theory we should be able to fold
        # step 2 into step 1, so we have only a single query.  But how do we
        # get SQLObject to return not just POSubmissions but also one extra
        # column from the join?
        parameters = sqlvalues(language=self.language,
            wanted_primemsgids=takers_for_primemsgid.keys())

        parameters['ids'] = 'false'
        if stored_pomsgsets:
            ids_list = ','.join(
                [quote(pomsgset) for pomsgset in stored_pomsgsets])
            parameters['ids'] = 'POMsgSet.id IN (%s)' % ids_list


        # Step 1.
        # Find ids of all POSubmissions that might be relevant (either as
        # suggestions for our all_pomsgsets or because they're already
        # attached to our stored_pomsgsets) plus their potmsgsets'
        # primemsgids.
        # Note that a suggestion coming from a fuzzy pomsgset isn't relevant
        # as a suggestion, but if it happens to be attached to a msgset from
        # stored_pomsgsets, it will still be relevant to that msgset.

        query = """
            SELECT DISTINCT POSubmission.id, POTMsgSet.primemsgid
            FROM POSubmission
            JOIN POMsgSet ON POSubmission.pomsgset = POMsgSet.id
            JOIN POTMsgSet ON POMsgSet.potmsgset = POTMsgSet.id
            JOIN POFile ON POMsgSet.pofile = POFile.id
            WHERE
                (%(ids)s OR NOT POMsgSet.isfuzzy) AND
                POFile.language = %(language)s AND
                POTMsgSet.primemsgid IN %(wanted_primemsgids)s
            """ % parameters
        cur = cursor()

        cur.execute(query)
        available = dict(cur.fetchall())
        if not available:
            return result

        # Step 2.
        # Load all relevant POSubmissions from the database.  We'll keep these
        # in newest-to-oldest order, because that's the way the POMsgSet's
        # cache likes them.
        relevant_submissions = POSubmission.select(
            "id IN %s" % sqlvalues(available.keys()), orderBy="-datecreated")

        # Step 3.
        # Figure out which of all_pomsgsets each submission is relevant to,
        # and return our mapping from all_pomsgset to various subsets of
        # load_submissions.
        pomsgset_ids = set(stored_pomsgsets)
        for submission in relevant_submissions:
            # There is a bit of special treatment for POSubmissions belonging
            # to fuzzy POMsgSets, since we don't accept those as suggestions.
            # Step 1 doesn't retrieve such POSubmissions as suggestions, but
            # it does retrieve whatever POSubmissions are directly attached to
            # stored_pomsgsets, regardless of fuzziness.
            # That means that if we retrieve a submission for a fuzzy
            # POMsgSet, it must be because that POMsgSet is one of the
            # stored_pomsgsets.
            # We can't just check submission.pomsgset.isfuzzy right away
            # because that might cause submission.pomsgset to be fetched from
            # database.  We've seen that add up to over a thousand retrievals
            # on some requests.
            # Instead, we start out by comparing the foreign-key value for
            # submission.pomsgset to the list of stored_pomsgsets.  If, and
            # only if, it is listed there, we also need to check it for
            # fuzziness.  And in that case we'll also know that
            # submission.pomsgset has already been fetched so we're not
            # triggering a new database query.
            owner_id = submission.pomsgsetID
            primemsgid = available[submission.id]
            assert (owner_id is not None,
                    "POSubmission %d has no POMsgSet." % submission.id)

            if owner_id in pomsgset_ids and submission.pomsgset.isfuzzy:
                # This is a POMsgSet that we've fetched (so we can access it
                # without causing an additional database fetch) and it turns
                # out to be fuzzy.  That implies that none of our pomsgsets
                # are expecting it as a useful suggestion, though we do need
                # to include it in the cacheable data for the POMsgSet it is
                # attached to.
                attached_msgset = submission.pomsgset
                assert (attached_msgset in takers_for_primemsgid[primemsgid],
                        "Fuzzy POMsgSet submission %d retrieved for no "
                        "apparent purpose." % submission.id)
                assert (attached_msgset in result,
                        "Fetched submission %d of unexpected, fuzzy "
                        "POMsgSet %d."
                        % (submission.id, submission.pomsgset.id))
                result[attached_msgset].append(submission)
            else:
                # Any other POSubmission we see here has to be non-fuzzy, and
                # so it's relevant to any POMsgSets that refer to the same
                # primemsgid, including the POMsgSet it itself is attached to.

                # XXX: JeroenVermeulen 2007-08-02 bug=132660: this assertion
                # may still trigger the unnecessary queries.  Remove it after
                # testing with production data!
                assert (not submission.pomsgset.isfuzzy,
                        "Submission %d from fuzzy POMsgSet %d fetched as a "
                        "suggestion."
                        % (submission.id, submission.pomsgset.id))
                for recipient in takers_for_primemsgid[primemsgid]:
                    result[recipient].append(submission)

        return result



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
    lasttranslator = ForeignKey(foreignKey='Person',
                                dbName='lasttranslator',
                                notNull=False,
                                default=None)
    license = IntCol(dbName='license',
                     notNull=False,
                     default=None)
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
    owner = ForeignKey(foreignKey='Person',
                       dbName='owner',
                       notNull=True)
    variant = StringCol(dbName='variant',
                        notNull=False,
                        default=None)
    path = StringCol(dbName='path',
                     notNull=True)
    exportfile = ForeignKey(foreignKey='LibraryFileAlias',
                            dbName='exportfile',
                            notNull=False,
                            default=None)
    exporttime = UtcDateTimeCol(dbName='exporttime',
                                notNull=False,
                                default=None)
    datecreated = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    last_touched_pomsgset = ForeignKey(
        foreignKey='POMsgSet', dbName='last_touched_pomsgset',
        notNull=False, default=None)

    from_sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='from_sourcepackagename', notNull=False, default=None)

    # joins
    pomsgsets = SQLMultipleJoin('POMsgSet', joinColumn='pofile')

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
        text = potmsgset.translationsForLanguage(self.language.code)[0]
        if (msgid == u'_: EMAIL OF TRANSLATORS\nYour emails'):
            emails = []
            if text is not None:
                emails.append(text)

            for contributor in self.contributors:
                preferred_email = contributor.preferredemail
                if (contributor.hide_email_addresses or
                    preferred_email is None):
                    emails.append('')
                else:
                    emails.append(preferred_email.email)
            return u','.join(emails)
        elif (msgid == u'_: NAME OF TRANSLATORS\nYour names'):
            names = []
            if text is not None:
                names.append(text)
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
                    text += ("\n  %s <%s>" %
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
        """See IPOFile."""
        return _can_add_suggestions(self, person)

    def currentMessageSets(self):
        return POMsgSet.select(
            'POMsgSet.pofile = %d AND POMsgSet.sequence > 0' % self.id,
            orderBy='sequence')

    def translated(self):
        """See `IPOFile`."""
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.iscomplete=TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0''' % self.id,
            clauseTables = ['POMsgSet']
            ))

    def untranslated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def __iter__(self):
        """See `IPOFile`."""
        return iter(self.currentMessageSets())

    def getPOMsgSetFromPOTMsgSet(self, potmsgset, only_current=False):
        """See `IPOFile`."""
        if potmsgset is None or (only_current and potmsgset.sequence <= 0):
            # There is no IPOTMsgSet for this id.
            return None

        return POMsgSet.selectOneBy(
            potmsgset=potmsgset, pofile=self)

    def getPOMsgSet(self, key, only_current=False):
        """See `IPOFile`."""
        query = 'potemplate = %d' % self.potemplate.id
        if only_current:
            query += ' AND sequence > 0'

        if not isinstance(key, unicode):
            raise AssertionError(
                "Can't index with type %s. (Must be unicode or POTMsgSet.)"
                % type(key))

        # Find a message ID with the given text.
        try:
            pomsgid = POMsgID.byMsgid(key)
        except SQLObjectNotFound:
            return None

        # Find a message set with the given message ID.

        potmsgset = POTMsgSet.selectOne(query +
            (' AND primemsgid = %d' % pomsgid.id))

        if potmsgset is None:
            # There is no IPOTMsgSet for this id.
            return None

        result = POMsgSet.selectOneBy(potmsgset=potmsgset, pofile=self)

        # Check that language has been initialized correctly.
        # XXX: JeroenVermeulen 2007-07-03, until language column in database
        # is initialized, accept null values here.
        has_language = (result is not None and result.language is not None)
        if has_language and result.language != self.language:
            raise AssertionError(
                "POFile in language %d contains POMsgSet in language %d"
                % (self.language, result.language))

        return result

    def __getitem__(self, msgid_text):
        """See `IPOFile`."""
        pomsgset = self.getPOMsgSet(msgid_text, only_current=True)
        if pomsgset is None:
            raise NotFoundError(msgid_text)
        else:
            return pomsgset

    def getPOMsgSetsNotInTemplate(self):
        """See `IPOFile`."""
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.sequence <> 0 AND
            POTMsgSet.sequence = 0''' % self.id,
            orderBy='sequence',
            clauseTables = ['POTMsgSet']))

    def getPOTMsgSetTranslated(self, slice=None):
        """See `IPOFile`."""
        # A POT set is translated only if the PO message set has
        # POMsgSet.iscomplete = TRUE.
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE
            ''' % sqlvalues(self.potemplate.id, self.id),
            clauseTables=['POMsgSet'],
            orderBy='POTMsgSet.sequence')

        if slice is not None:
            results = results[slice]

        return results

    def getPOTMsgSetFuzzy(self, slice=None):
        """See `IPOFile`."""
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POMsgSet.isfuzzy = TRUE
            ''' % sqlvalues(self.potemplate.id, self.id),
            clauseTables=['POMsgSet'],
            orderBy='POTmsgSet.sequence')

        if slice is not None:
            results = results[slice]

        return results

    def getPOTMsgSetUntranslated(self, slice=None):
        """See `IPOFile`."""
        # A POT set is not translated if the PO message set have
        # POMsgSet.iscomplete = FALSE or we don't have such POMsgSet.
        #
        # Use a subselect to allow the LEFT OUTER JOIN
        query = """POTMsgSet.id IN (
            SELECT POTMsgSet.id
            FROM POTMsgSet
            LEFT OUTER JOIN POMsgSet ON
                POTMsgSet.id = POMsgSet.potmsgset AND
                POMsgSet.pofile = %s
            WHERE
                 ((POMsgSet.isfuzzy = FALSE AND POMsgSet.iscomplete = FALSE) OR
                  POMsgSet.id IS NULL) AND
                 POTMsgSet.sequence > 0 AND
                 POTMsgSet.potemplate = %s
            ORDER BY POTMsgSet.sequence)""" % sqlvalues(self.id, self.potemplate.id)
        results = POTMsgSet.select(query, orderBy='POTMsgSet.sequence')

        if slice is not None:
            results = results[slice]

        return results

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        # A POT set has "new" suggestions if there is a POMsgSet with
        # submissions after active translation was reviewed
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POSubmission.pomsgset = POMsgSet.id AND
            (POSubmission.datecreated > POMsgSet.date_reviewed OR
             (POMsgSet.date_reviewed IS NULL AND
              POSubmission.active IS NOT TRUE))
            ''' % sqlvalues(self.potemplate, self),
            clauseTables=['POMsgSet', 'POSubmission'],
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
        results = POTMsgSet.select('''POTMsgSet.id IN (
            SELECT POTMsgSet.id
            FROM POTMsgSet
            LEFT OUTER JOIN POMsgSet ON
                POTMsgSet.id = POMsgSet.potmsgset AND
                POMsgSet.pofile = %s
            LEFT OUTER JOIN POSubmission ps1 ON
                ps1.pomsgset = POMsgSet.id
            LEFT OUTER JOIN POSubmission ps2 ON
                ps2.pomsgset = ps1.pomsgset AND
                ps2.pluralform = ps1.pluralform AND
                ps2.id != ps1.id
            WHERE
                ps1.published IS TRUE AND
                ps2.active IS TRUE AND
                POTMsgSet.sequence > 0 AND
                POTMsgSet.potemplate = %s)
            ''' % sqlvalues(self, self.potemplate),
            orderBy='POTmsgSet.sequence')

        return results

    def getPOTMsgSetWithErrors(self, slice=None):
        """See `IPOFile`."""
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POSubmission.pomsgset = POMsgSet.id AND
            POSubmission.published IS TRUE AND
            POSubmission.pluralform = 0 AND
            POSubmission.validationstatus <> %s
            ''' % sqlvalues(self.potemplate.id, self.id,
                            TranslationValidationStatus.OK),
            clauseTables=['POMsgSet', 'POSubmission'],
            orderBy='POTmsgSet.sequence')

        if slice is not None:
            results = results[slice]

        return results

    def hasMessageID(self, messageID):
        """See `IPOFile`."""
        results = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d''' % (self.id, messageID.id))
        return results.count() > 0

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
        return POMsgSet.select("""
            pofile = %s AND
            isfuzzy IS TRUE AND
            sequence > 0
            """ % sqlvalues(self.id)).count()

    def expireAllMessages(self):
        """See `IPOFile`."""
        for msgset in self.currentMessageSets():
            msgset.sequence = 0

    def updateStatistics(self, tested=False):
        """See `IPOFile`."""
        # make sure all the data is in the db
        flush_database_updates()
        current = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.sequence > 0 AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.publishedcomplete = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            ''' % self.id, clauseTables=['POTMsgSet']).count()

        updates = POMsgSet.select('''
            POMsgSet.pofile = %s AND
            POMsgSet.sequence > 0 AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.publishedcomplete = TRUE AND
            POMsgSet.isupdated = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            ''' % sqlvalues(self.id),
            clauseTables=['POTMsgSet']).count()

        if tested:
            updates_from_first_principles = POMsgSet.select('''
                POMsgSet.pofile = %s AND
                POMsgSet.sequence > 0 AND
                POMsgSet.isfuzzy = FALSE AND
                POMsgSet.iscomplete = TRUE AND
                POMsgSet.publishedfuzzy = FALSE AND
                POMsgSet.publishedcomplete = TRUE AND
                POMsgSet.potmsgset = POTMsgSet.id AND
                POTMsgSet.sequence > 0 AND
                active_submission.pomsgset = POMsgSet.id AND
                active_submission.active IS TRUE AND
                published_submission.pomsgset = POMsgSet.id AND
                published_submission.published IS TRUE AND
                active_submission.pluralform = published_submission.pluralform
                AND
                active_submission.datecreated > published_submission.datecreated
                ''' % sqlvalues(self.id),
                clauseTables=['POTMsgSet',
                              'POSubmission AS active_submission',
                              'POSubmission AS published_submission']).count()
            if updates != updates_from_first_principles:
                raise AssertionError('Failure in update statistics.')

        rosetta = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            ( POMsgSet.sequence < 1 OR
              POMsgSet.publishedcomplete = FALSE OR
              POMsgSet.publishedfuzzy=TRUE ) AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            ''' % self.id,
            clauseTables=['POTMsgSet']).count()

        unreviewed = POMsgSet.select('''
            POMsgSet.pofile = %s AND
            POSubmission.pomsgset = POMsgSet.id AND
            (POSubmission.datecreated > POMsgSet.date_reviewed OR
             (POMsgSet.date_reviewed IS NULL AND
              POSubmission.active IS NOT TRUE))
            ''' % sqlvalues(self),
            clauseTables=['POSubmission']).count()

        self.currentcount = current
        self.updatescount = updates
        self.rosettacount = rosetta
        self.unreviewed_count = unreviewed
        return (current, updates, rosetta, unreviewed)

    def createMessageSetFromMessageSet(self, potmsgset):
        """See `IPOFile`."""
        pomsgset = POMsgSet(
            sequence=0,
            pofile=self,
            iscomplete=False,
            publishedcomplete=False,
            obsolete=False,
            isfuzzy=False,
            publishedfuzzy=False,
            potmsgset=potmsgset,
            language=self.language)
        return pomsgset

    def createMessageSetFromText(self, text):
        """See `IPOFile`."""
        potmsgset = self.potemplate.getPOTMsgSetByMsgIDText(
            text, only_current=False)

        if potmsgset is None:
            potmsgset = self.potemplate.createMessageSetFromText(text)

        return self.createMessageSetFromMessageSet(potmsgset)

    def updateHeader(self, new_header):
        """See `IPOFile`."""
        if not new_header:
            return

        # check that the plural forms info is valid
        new_plural_form = new_header.get('Plural-Forms', None)
        if new_plural_form is None:
            # The new header does not have plural form information.
            # Parse the old header.
            old_header = POHeader(msgstr=self.header)
            # The POHeader needs to know is ready to be used.
            old_header.updateDict()
            old_plural_form = old_header.get('Plural-Forms', None)
            if old_plural_form is not None:
                # First attempt: use the plural-forms header that is already
                # in the database, if it exists.
                new_header['Plural-Forms'] = old_header['Plural-Forms']
            elif self.language.pluralforms is not None:
                # Second attempt: get the default value for plural-forms from
                # the language table.
                new_header['Plural-Forms'] = self.language.pluralforms
            else:
                # we absolutely don't know it; only complain if
                # a plural translation is present
                # XXX Carlos Perello Marin 2005-06-15 bugs=1186: 
                # We should implement this bug instead of
                # set it to this default value...
                new_header['Plural-Forms'] = 1
        # XXX sabdfl 2005-05-27 should we also differentiate between
        # washeaderfuzzy and isheaderfuzzy?
        self.topcomment = new_header.comment
        self.header = new_header.msgstr
        self.fuzzyheader = 'fuzzy' in new_header.flags

    def isPORevisionDateOlder(self, header):
        """See `IPOFile`."""
        old_header = POHeader(msgstr=self.header)
        old_header.updateDict()

        # Get the old and new PO-Revision-Date entries as datetime objects.
        try:
            old_date = old_header.getTranslationRevisionDate()
        except UnknownTranslationRevisionDate:
            # If one of the headers, has a missing or wrong PO-Revision-Date,
            # then they cannot be compared, so we consider the new header to
            # be the most recent.
            return False
        try:
            new_date = header.getTranslationRevisionDate()
        except UnknownTranslationRevisionDate:
            # If one of the headers, has a missing or wrong PO-Revision-Date,
            # then they cannot be compared, so we consider the new header to
            # be the most recent.
            return False

        # Check whether or not the date is older.
        if old_date <= new_date:
            return False
        elif old_date > new_date:
            return True

    def getNextToImport(self):
        """See `IPOFile`."""
        flush_database_updates()
        return TranslationImportQueueEntry.selectFirstBy(
                pofile=self,
                status=RosettaImportStatus.APPROVED,
                orderBy='dateimported')

    def importFromQueue(self, logger=None):
        """See `IPOFile`."""
        librarian_client = getUtility(ILibrarianClient)

        entry_to_import = self.getNextToImport()

        if entry_to_import is None:
            # There is no new import waiting for being imported.
            return

        import_file = librarian_client.getFileByAlias(entry_to_import.content.id)

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
        try:
            importer = getUtility(ITranslationImporter)
            errors = importer.importFile(entry_to_import, logger=logger)
        except NotExportedFromLaunchpad:
            # We got a file that was not exported from Rosetta as a non
            # published upload. We log it and select the email template.
            if logger:
                logger.warning(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-not-exported-from-rosetta.txt'
            import_rejected = True
        except (TranslationFormatSyntaxError,
                TranslationFormatInvalidInputError):
            # The import failed with a format error. We log it and select the
            # email template.
            if logger:
                logger.warning(
                    'Error importing %s' % self.title, exc_info=1)
            template_mail = 'poimport-syntax-error.txt'
            import_rejected = True
        except OldTranslationImported:
            # The attached file is older than the last imported one, we ignore
            # it. We also log this problem and select the email template.
            if logger:
                logger.warning('Got an old version for %s' % self.title)
            template_mail = 'poimport-got-old-version.txt'
            import_rejected = True

        flush_database_updates()

        # Prepare the mail notification.
        msgsets_imported = POMsgSet.select(
            'sequence > 0 AND pofile=%s' % (sqlvalues(self.id))).count()

        replacements = {
            'dateimport': entry_to_import.dateimported.strftime('%F %R%z'),
            'elapsedtime': entry_to_import.getElapsedTimeText(),
            'file_link': entry_to_import.content.http_url,
            'import_title': '%s translations for %s' % (
                self.language.displayname, self.potemplate.displayname),
            'importer': entry_to_import.importer.displayname,
            'language': self.language.displayname,
            'numberofmessages': msgsets_imported,
            'template': self.potemplate.displayname,
            }

        if import_rejected:
            # We got an error that prevented us to import any translation, we
            # need to notify the user.
            subject = 'Import problem - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        elif len(errors):
            # There were some errors with translations.
            errorsdetails = ''
            for error in errors:
                pomsgset = error['pomsgset']
                pomessage = error['pomessage']
                error_message = error['error-message']
                errorsdetails = '%s%d.  [msg %d]\n"%s":\n\n%s\n\n' % (
                    errorsdetails,
                    pomsgset.potmsgset.sequence,
                    pomsgset.sequence,
                    error_message,
                    unicode(pomessage))

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

        # Send the email.
        template = helpers.get_email_template(template_mail)
        message = template % replacements

        fromaddress = config.rosetta.rosettaadmin.email

        toaddress = helpers.contactEmailAddresses(entry_to_import.importer)

        simple_sendmail(fromaddress,
            toaddress,
            subject,
            MailWrapper().format(message))

        if import_rejected:
            # There were no imports at all and the user needs to review that
            # file, we tag it as FAILED.
            entry_to_import.status = RosettaImportStatus.FAILED
            return

        # The import has been done, we mark it that way.
        entry_to_import.status = RosettaImportStatus.IMPORTED
        # And add karma to the importer if it's not imported automatically
        # (all automatic imports come from the rosetta expert user) and comes
        # from upstream.
        rosetta_expert = getUtility(ILaunchpadCelebrities).rosetta_expert
        if (entry_to_import.is_published and
            entry_to_import.importer.id != rosetta_expert.id):
            # The Rosetta Experts team should not get karma.
            entry_to_import.importer.assignKarma(
                'translationimportupstream',
                product=self.potemplate.product,
                distribution=self.potemplate.distribution,
                sourcepackagename=self.potemplate.sourcepackagename)

        # Now we update the statistics after this new import
        self.updateStatistics()

    def validExportCache(self):
        """See `IPOFile`."""
        if self.exportfile is None:
            return False

        if self.last_touched_pomsgset is None:
            # There are no translations at all, we invalidate the cache just
            # in case.
            return False

        return not self.last_touched_pomsgset.isNewerThan(self.exporttime)

    def updateExportCache(self, contents):
        """See `IPOFile`."""
        alias_set = getUtility(ILibraryFileAliasSet)

        if self.variant:
            filename = '%s@%s.po' % (
                self.language.code, self.variant.encode('UTF-8'))
        else:
            filename = '%s.po' % (self.language.code)

        size = len(contents)
        file = StringIO.StringIO(contents)


        # XXX CarlosPerelloMarin 2006-02-27: Added the debugID argument to
        # help us to debug bug #1887 on production. This will let us track
        # this librarian import so we can discover why sometimes, the fetch
        # of it fails.
        self.exportfile = alias_set.create(
            filename, size, file, 'application/x-po',
            debugID='pofile-id-%d' % self.id)

        # Note that UTC_NOW is resolved to the time at the beginning of the
        # transaction. This is significant because translations could be added
        # to the database while the export transaction is in progress, and the
        # export would not include those translations. However, we want to be
        # able to compare the export time to other datetime object within the
        # same transaction -- e.g. in a call to validExportCache(). This is
        # why we call .sync() -- it turns the UTC_NOW reference into an
        # equivalent datetime object.
        self.exporttime = UTC_NOW
        self.sync()

    def fetchExportCache(self):
        """Return the cached export file, if it exists, or None otherwise."""

        if self.exportfile is None:
            return None
        else:
            alias_set = getUtility(ILibraryFileAliasSet)
            return alias_set[self.exportfile.id].read()

    def uncachedExport(self, included_obsolete=True, force_utf8=False):
        """See `IPOFile`."""
        exporter = IPOTemplateExporter(self.potemplate)
        exporter.force_utf8 = force_utf8
        return exporter.export_pofile(
            self.language, self.variant, included_obsolete)

    def export(self, included_obsolete=True):
        """See `IPOFile`."""
        if self.validExportCache() and included_obsolete:
            # Only use the cache if the request includes obsolete messages,
            # without them, we always do a full export.
            try:
                return self.fetchExportCache()
            except LookupError:
                # XXX: Carlos Perello Marin 2006-02-24: LookupError is a
                # workaround for bug #1887. Something produces LookupError
                # exception and we don't know why. This will allow us to
                # provide an export in those cases.
                logging.error(
                    "Error fetching a cached file from librarian", exc_info=1)
            except URLError:
                # There is a problem getting a cached export from Librarian.
                # Log it and do a full export.
                logging.warning(
                    "Error fetching a cached file from librarian", exc_info=1)

        contents = self.uncachedExport()

        if len(contents) == 0:
            # The export is empty, this is completely broken.
            raise ZeroLengthPOExportError, "Exporting %s" % self.title

        if included_obsolete:
            # Update the cache if the request includes obsolete messages.
            try:
                self.updateExportCache(contents)
            except UploadFailed:
                # For some reason, we were not able to upload the exported
                # file in librarian, that's fine. It only means that next
                # time, we will do a full export again.
                logging.warning(
                    "Error uploading a cached file into librarian", exc_info=1)

        return contents

    def exportToFileHandle(self, filehandle, included_obsolete=True):
        """See `IPOFile`."""
        exporter = IPOTemplateExporter(self.potemplate)
        exporter.export_pofile_to_file(filehandle, self.language,
            self.variant, included_obsolete)

    def invalidateCache(self):
        """See `IPOFile`."""
        self.exportfile = None


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
        self.license = None
        self.lastparsed = None
        self.owner = getUtility(ILaunchpadCelebrities).rosetta_expert

        # The default POFile owner is the Rosetta Experts team unless the
        # given owner has rights to write into that file.
        if self.canEditTranslations(owner):
            self.owner = owner

        self.path = u'unknown'
        self.exportfile = None
        self.datecreated = None
        self.last_touched_pomsgset = None
        self.contributors = []
        self.from_sourcepackagename = None
        self.pomsgsets = None


    def __getitem__(self, msgid_text):
        pomsgset = self.getPOMsgSet(msgid_text, only_current=True)
        if pomsgset is None:
            raise NotFoundError(msgid_text)
        else:
            return pomsgset

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

    def getPOMsgSetFromPOTMsgSet(self, potmsgset, only_current=False):
        """See `IPOFile`."""
        if potmsgset is None or (only_current and potmsgset.sequence <= 0):
            # There is no IPOTMsgSet for this id.
            return None

        return DummyPOMsgSet(self, potmsgset)

    def getPOMsgSet(self, key, only_current=False):
        """See `IPOFile`."""
        query = 'potemplate = %d' % self.potemplate.id
        if only_current:
            query += ' AND sequence > 0'

        if isinstance(key, POTMsgSet):
            potmsgset = key
        else:
            # Find a message ID with the given text.
            try:
                pomsgid = POMsgID.byMsgid(key)
            except SQLObjectNotFound:
                return None

            # Find a message set with the given message ID.

            potmsgset = POTMsgSet.selectOne(query +
                (' AND primemsgid = %d' % pomsgid.id))

        if potmsgset is None:
            # There is no IPOTMsgSet for this id.
            return None

        return DummyPOMsgSet(self, potmsgset)

    def emptySelectResults(self):
        return POFile.select("1=2")

    def getPOMsgSetsNotInTemplate(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetTranslated(self, slice=None):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetFuzzy(self, slice=None):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetUntranslated(self, slice=None):
        """See `IPOFile`."""
        return self.potemplate.getPOTMsgSets(slice)

    def getPOTMsgSetWithNewSuggestions(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetChangedInLaunchpad(self):
        """See `IPOFile`."""
        return self.emptySelectResults()

    def getPOTMsgSetWithErrors(self, slice=None):
        """See `IPOFile`."""
        return self.emptySelectResults()


    def hasMessageID(self, msgid):
        """See `IPOFile`."""
        raise NotImplementedError

    def currentCount(self):
        return 0

    def rosettaCount(self):
        return 0

    def updatesCount(self):
        return 0

    def unreviewedCount(self):
        """See `IPOFile`."""
        return 0

    def nonUpdatesCount(self):
        return 0

    def translatedCount(self):
        return 0

    def untranslatedCount(self):
        return self.messageCount()

    @property
    def fuzzy_count(self):
        """See `IPOFile`."""
        return 0

    def currentPercentage(self):
        return 0.0

    def rosettaPercentage(self):
        return 0.0

    def updatesPercentage(self):
        return 0.0

    def nonUpdatesPercentage(self):
        return 0.0

    def translatedPercentage(self):
        return 0.0

    def untranslatedPercentage(self):
        return 100.0

    def validExportCache(self):
        """See `IPOFile`."""
        return False

    def updateExportCache(self, contents):
        """See `IPOFile`."""
        raise NotImplementedError

    def export(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def exportToFileHandle(self, filehandle, included_obsolete=True):
        """See `IPOFile`."""
        raise NotImplementedError

    def uncachedExport(self, included_obsolete=True, export_utf8=False):
        """See `IPOFile`."""
        raise NotImplementedError

    def invalidateCache(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def createMessageSetFromMessageSet(self, potmsgset):
        """See `IPOFile`."""
        raise NotImplementedError

    def createMessageSetFromText(self, text):
        """See `IPOFile`."""
        raise NotImplementedError

    def translated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def untranslated(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def expireAllMessages(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def updateStatistics(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def updateHeader(self, new_header):
        """See `IPOFile`."""
        raise NotImplementedError

    def isPORevisionDateOlder(self, header):
        """See `IPOFile`."""
        raise NotImplementedError

    def getNextToImport(self):
        """See `IPOFile`."""
        raise NotImplementedError

    def importFromQueue(self, logger=None):
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
                POTemplate.distrorelease = %s AND
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
                POTemplate.distrorelease = %s AND
                POTemplate.sourcepackagename = %s''' % sqlvalues(
                    path, distroseries.id, sourcepackagename.id),
                clauseTables=['POTemplate'])


class POFileTranslator(SQLBase):
    """See `IPOFileTranslator`."""

    implements(IPOFileTranslator)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    latest_posubmission = ForeignKey(foreignKey='POSubmission',
        dbName='latest_posubmission', notNull=True)
    date_last_touched = UtcDateTimeCol(dbName='date_last_touched',
        notNull=False, default=None)

