# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POSubmission',
    'POSubmissionSet'
    ]

from zope.interface import implements

from sqlobject import (BoolCol, ForeignKey, IntCol, SQLObjectNotFound)

from canonical.database import postgresql
from canonical.database.sqlbase import (cursor, quote, SQLBase, sqlvalues)
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import RosettaTranslationOrigin

from canonical.launchpad.interfaces.posubmission import (
    IPOSubmission, IPOSubmissionSet, TranslationValidationStatus)


class POSubmissionSet:

    implements(IPOSubmissionSet)

    def getPOSubmissionByID(self, id):
        """See `IPOSubmissionSet`."""
        try:
            return POSubmission.get(id)
        except SQLObjectNotFound:
            return None

    def getSubmissionsFor(self, stored_pomsgsets, dummy_pomsgsets):
        """See `IPOSubmissionSet`."""
        all_pomsgsets = stored_pomsgsets + dummy_pomsgsets

        # We'll be mapping each POMsgSet from all_pomsgsets to a list of
        # submissions that may be relevant to it in some way, and that it will
        # wish to cache.
        result = dict((msgset, []) for msgset in all_pomsgsets)
        if not all_pomsgsets:
            return result

        # Figure out what language we're retrieving for, and ensure that all
        # pomsgsets are for that same language.
        language = all_pomsgsets[0].language
        for pomsgset in all_pomsgsets:
            assert pomsgset.language == language, "POMsgSets mix languages!"

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
        # which will be essential to step 3.  Basically, we figure out which
        # messages could benefit from which suggestions.
        #
        # 2. Load all relevant submissions from the database.
        #
        # 3. Sort out which submissions are relevant to which pomsgsets from
        # our parameters stored_pomsgsets and dummy_pomsgsets.  This depends
        # on our knowing the primemsgids of the potmsgsets they are attached
        # to, but we don't want to retrieve all those potmsgsets just to get
        # that information.

        cur = cursor()
        available = {}

        parameters = sqlvalues(language=language,
            wanted_primemsgids=takers_for_primemsgid.keys())

        # Step 1.
        # Find ids of all POSubmissions that might be relevant (either as
        # suggestions for our all_pomsgsets or because they're already
        # attached to our stored_pomsgsets) plus their potmsgsets'
        # primemsgids.
        # A suggestion coming from a fuzzy pomsgset isn't relevant as a
        # suggestion, but if it happens to be attached to a msgset from
        # stored_pomsgsets, it will still be relevant to that msgset.

        if stored_pomsgsets:
            # Fetch submissions attached to our POMsgSets.
            parameters['one_of_ours'] = ("POMsgSet.id IN (%s)" %
                ', '.join([quote(pomsgset) for pomsgset in stored_pomsgsets]))

            query = """
                SELECT DISTINCT POSubmission.id, POTMsgSet.primemsgid
                FROM POSubmission
                JOIN POMsgSet ON POSubmission.pomsgset = POMsgSet.id
                JOIN POTMsgSet ON POMsgSet.potmsgset = POTMsgSet.id
                WHERE %(one_of_ours)s
                """ % parameters

            cur.execute(query)
            available.update(dict(cur.fetchall()))
        else:
            parameters['one_of_ours'] = 'false'

        # Fetch suggestions for our POMsgSets.  We don't separate suggestions
        # from submissions attached to our own POMsgSets at this point,
        # because one POMsgSet's attached submission may be another POMsgSet's
        # useful suggestion.  We dump them all in a big pile and sort 'em out
        # later.
        # Often there are many suggestions with identical POTranslations.
        # We only retrieve the most recent POSubmission that offers a given
        # POTranslation for a given primemsgid.  We also leave out any
        # suggestions that offer the same POTranslation that is already the
        # active translation for a given POMsgSet.
        # A join between POMsgSet and POSubmission is very expensive in this
        # query.  Here we force the optimizer's hand by breaking up the query
        # into one that selects POMsgSets whose translations would be valid
        # suggestions, and another retrieving the associated POSubmissions.
        # Intermediate results are kept in a temporary table.
        # This is not a good thing, and if it's any faster than a single big
        # query, that's pure coincidence.
        # XXX: JeroenVermeulen 2007-09-02 bug=30602: Evaluate performance with
        # this change on staging, and roll back if necessary.
        parameters['temp_table'] = 'temp_suggestion_pomsgset'
        postgresql.drop_tables(cur, [parameters['temp_table']])
        cur.execute("""
            CREATE TEMP TABLE %(temp_table)s AS
            SELECT DISTINCT POMsgSet.id, POTMsgSet.primemsgid
            FROM POMsgSet
            JOIN POTMsgSet ON POMsgSet.potmsgset = POTMsgSet.id
            JOIN POFile ON POMsgSet.pofile = POFile.id
            WHERE
                POFile.language = %(language)s AND
                POTMsgSet.primemsgid IN %(wanted_primemsgids)s AND
                NOT POMsgSet.isfuzzy AND
                NOT %(one_of_ours)s
            """ % parameters)
        cur.execute(
            "CREATE INDEX %(temp_table)s_idx ON %(temp_table)s(id)"
            % parameters)
        cur.execute("""
            SELECT DISTINCT id, primemsgid FROM (
            SELECT DISTINCT ON (potranslation, primemsgid)
                pos.id,
                pos.potranslation,
                primemsgid
            FROM POSubmission pos
            JOIN %(temp_table)s ON pos.pomsgset = %(temp_table)s.id
            WHERE NOT EXISTS (
                SELECT * FROM POSubmission better
                WHERE
                    better.pomsgset = %(temp_table)s.id AND
                    better.pluralform = pos.pluralform AND
                    better.potranslation = pos.potranslation AND
                    better.active)
            ORDER BY potranslation, primemsgid, pos.datecreated DESC
            ) AS suggestions
            """ % parameters)
        available.update(dict(cur.fetchall()))
        postgresql.drop_tables(cur, [parameters['temp_table']])

        if not available:
            return result

        # Step 2.
        # Load all relevant POSubmissions from the database.  We'll keep these
        # in newest-to-oldest order, because that's the way the view class
        # likes them.
        relevant_submissions = POSubmission.select(
            "id IN (%s)" % ", ".join([quote(id) for id in available]),
            orderBy="-datecreated")

        # Step 3.
        # Figure out which of all_pomsgsets each submission is relevant to,
        # and return our mapping from all_pomsgset to various subsets of
        # load_submissions.
        pomsgset_ids = set(pomsgset.id for pomsgset in stored_pomsgsets)
        for submission in relevant_submissions:
            # There is a bit of special treatment for POSubmissions belonging
            # to fuzzy POMsgSets, since we don't accept those as suggestions.
            # That means that if we retrieve a submission for a fuzzy
            # POMsgSet, it must be because that POMsgSet is one of the
            # stored_pomsgsets.
            # We can't just check submission.pomsgset.isfuzzy right away here,
            # because that might cause submission.pomsgset to be unnecessarily
            # fetched from the database.  We've seen that add up to over a
            # thousand retrievals on some requests.
            # Instead, we start out by comparing the foreign-key value for
            # submission.pomsgset to the list of stored_pomsgsets.  If, and
            # only if, it is listed there, we also need to check it for
            # fuzziness.  And in that case we'll also know that
            # submission.pomsgset has already been fetched so we're not
            # triggering a new database query.
            owner_id = submission.pomsgsetID
            primemsgid = available[submission.id]
            assert owner_id is not None, (
                    "POSubmission in database has no POMsgSet.")

            if owner_id in pomsgset_ids and submission.pomsgset.isfuzzy:
                # This is a POMsgSet that we've fetched (so we can access it
                # without causing an additional database fetch) and it turns
                # out to be fuzzy.  That implies that none of our pomsgsets
                # are expecting it as a useful suggestion, though we do need
                # to present it to its owning pomsgset.
                of_pomsgset = submission.pomsgset
                assert of_pomsgset in takers_for_primemsgid[primemsgid], (
                        "Fuzzy POMsgSet submission retrieved for no purpose.")
                assert of_pomsgset in result, (
                        "Fetched submission for unexpected, fuzzy POMsgSet.")
                result[of_pomsgset].append(submission)
            else:
                # Any other POSubmission we see here has to be non-fuzzy, and
                # so it's relevant to any POMsgSets that refer to the same
                # primemsgid, including the POMsgSet it itself is attached to.
                for recipient in takers_for_primemsgid[primemsgid]:
                    result[recipient].append(submission)

        return result


class POSubmission(SQLBase):

    implements(IPOSubmission)
    _table = 'POSubmission'

    pomsgset = ForeignKey(foreignKey='POMsgSet',
        dbName='pomsgset', notNull=True)
    pluralform = IntCol(notNull=True)
    potranslation = ForeignKey(foreignKey='POTranslation',
        dbName='potranslation', notNull=True)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    origin = EnumCol(dbName='origin', notNull=True,
        schema=RosettaTranslationOrigin)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)
    validationstatus = EnumCol(dbName='validationstatus', notNull=True,
        schema=TranslationValidationStatus)
    active = BoolCol(notNull=True, default=False)
    published = BoolCol(notNull=True, default=False)

    def makeHTMLId(self, description, for_potmsgset=None):
        """See `IPOSubmission`."""
        if for_potmsgset is None:
            for_potmsgset = self.pomsgset.potmsgset
        suffix = '_'.join([
            self.pomsgset.pofile.language.code,
            description,
            str(self.id),
            str(self.pluralform)])
        return for_potmsgset.makeHTMLId(suffix)


# XXX do we want to indicate the difference between a from-scratch
# submission and an editorial decision (for example, when someone is
# reviewing a file and says "yes, let's use that one")?

