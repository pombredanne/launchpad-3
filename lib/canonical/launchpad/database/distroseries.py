# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Database classes for a distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeries',
    'DistroSeriesSet',
    ]

import logging
from cStringIO import StringIO

from sqlobject import (
    BoolCol, StringCol, ForeignKey, SQLMultipleJoin, IntCol,
    SQLObjectNotFound, SQLRelatedJoin)
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.multitablecopy import MultiTableCopy
from canonical.database.postgresql import drop_tables
from canonical.database.sqlbase import (cursor, flush_database_caches,
    flush_database_updates, quote_like, quote, SQLBase, sqlvalues)
from canonical.launchpad.database.binarypackagename import (
    BinaryPackageName)
from canonical.launchpad.database.binarypackagerelease import (
        BinaryPackageRelease)
from canonical.launchpad.database.bug import (
    get_bug_tags, get_bug_tags_open_count)
from canonical.launchpad.database.bugtarget import BugTargetBase
from canonical.launchpad.database.bugtask import BugTaskSet
from canonical.launchpad.database.component import Component
from canonical.launchpad.database.distroarchseries import DistroArchSeries
from canonical.launchpad.database.distroseriesbinarypackage import (
    DistroSeriesBinaryPackage)
from canonical.launchpad.database.distroserieslanguage import (
    DistroSeriesLanguage, DummyDistroSeriesLanguage)
from canonical.launchpad.database.distroseriespackagecache import (
    DistroSeriesPackageCache)
from canonical.launchpad.database.distroseriessourcepackagerelease import (
    DistroSeriesSourcePackageRelease)
from canonical.launchpad.database.language import Language
from canonical.launchpad.database.languagepack import LanguagePack
from canonical.launchpad.database.milestone import Milestone
from canonical.launchpad.database.packaging import Packaging
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.pomsgset import POMsgSet
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory, SourcePackagePublishingHistory)
from canonical.launchpad.database.queue import (
    PackageUpload, PackageUploadQueue)
from canonical.launchpad.database.section import Section
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.database.sourcepackagename import SourcePackageName
from canonical.launchpad.database.sourcepackagerelease import (
    SourcePackageRelease)
from canonical.launchpad.database.specification import (
    HasSpecificationsMixin, Specification)
from canonical.launchpad.database.translationimportqueue import (
    HasTranslationImportsMixin)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    IArchiveSet, IBinaryPackageName, IBuildSet, IDistroSeries,
    IDistroSeriesSet, IHasBuildRecords, IHasQueueItems,
    IHasTranslationTemplates, ILibraryFileAliasSet,
    IPublishedPackageSet, IPublishing, ISourcePackage, ISourcePackageName,
    ISourcePackageNameSet, LanguagePackType, NotFoundError)
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.lp.dbschema import (
    ArchivePurpose, DistroSeriesStatus, PackagePublishingPocket,
    PackagePublishingStatus, PackageUploadStatus, SpecificationFilter,
    SpecificationGoalStatus, SpecificationSort,
    SpecificationImplementationStatus)


def copy_active_translations_to_new_series(child, transaction, copier, logger):
    """Furnish untranslated child `DistroSeries` with parent's translations.

    This method uses `MultiTableCopy` to copy data.

    Translation data for the new series ("child") is first copied into holding
    tables called e.g. "temp_POTemplate_holding_ubuntu_feisty" and processed
    there.  Then, near the end of the procedure, the contents of these holding
    tables are all poured back into the original tables.

    If this procedure fails, it may leave holding tables behind.  This was
    done deliberately to leave some forensics information for failures, and
    also to allow admins to see what data has and has not been copied.

    If a holding table left behind by an abortive run has a column called
    new_id at the end, it contains unfinished data and may as well be dropped.
    If it does not have that column, the holding table was already in the
    process of being poured back into its source table.  In that case the
    sensible thing to do is probably to continue pouring it.
    """
    logger.info(
        "Populating blank distroseries %s with translations from %s." %
        sqlvalues(child, child.parent))

    # Because this function only deals with the case where "child" is a new
    # distroseries without any existing translations attached, it can afford
    # to be much more cavalier with ACID considerations than the function that
    # updates an existing translation based on what's found in the parent.

    # 1. Extraction phase--for every table involved (called a "source table"
    # in MultiTableCopy parlance), we create a "holding table."  We fill that
    # with all rows from the source table that we want to copy from the parent
    # series.  We make some changes to the copied rows, such as making them
    # belong to ourselves instead of our parent series.
    #
    # The first phase does not modify any tables that other clients may want
    # to use, avoiding locking problems.
    #
    # 2. Pouring phase.  From each holding table we pour all rows back into
    # the matching source table, deleting them from the holding table as we
    # go.  The holding table is dropped once empty.
    #
    # The second phase is "batched," moving only a small number of rows at
    # a time, then performing an intermediate commit.  This avoids holding
    # too many locks for too long and disrupting regular database service.

    assert child.hide_all_translations, (
        "hide_all_translations not set!"
        " That would allow users to see and modify incomplete"
        " translation state.")

    # Clean up any remains from a previous run.  If we got here, that means
    # that any such remains are unsalvagable.
    copier.dropHoldingTables()

    # Copy relevant POTemplates from existing series into a holding table,
    # complete with their original id fields.
    where = 'distrorelease = %s AND iscurrent' % quote(child.parentseries)
    copier.extract('POTemplate', [], where)

    # Now that we have the data "in private," where nobody else can see it,
    # we're free to play with it.  No risk of locking other processes out of
    # the database.
    # Change series identifiers in the holding table to point to the child
    # (right now they all bear the parent's id) and set creation dates to
    # the current transaction time.
    cursor().execute('''
        UPDATE %s
        SET
            distrorelease = %s,
            datecreated =
                timezone('UTC'::text,
                    ('now'::text)::timestamp(6) with time zone)
    ''' % (copier.getHoldingTableName('POTemplate'), quote(child)))


    # Copy each POTMsgSet whose template we copied, and let MultiTableCopy
    # replace each potemplate reference with a reference to our copy of the
    # original POTMsgSet's potemplate.
    copier.extract('POTMsgSet', ['POTemplate'], 'POTMsgSet.sequence > 0')

    # Copy POMsgIDSightings, substituting their potmsgset foreign keys with
    # references to the child's POTMsgSets (again, done by MultiTableCopy).
    copier.extract('POMsgIDSighting', ['POTMsgSet'])

    # Copy POFiles, making them refer to the child's copied POTemplates.
    copier.extract('POFile', ['POTemplate'])

    # Same for POMsgSet, but a bit more complicated since it refers to both
    # POFile and POTMsgSet.
    copier.extract('POMsgSet', ['POFile', 'POTMsgSet'])

    # And for POSubmission.
    copier.extract('POSubmission', ['POMsgSet'], 'active OR published')

    # Finally, pour the holding tables back into the originals.
    copier.pour(transaction)


def copy_active_translations_as_update(child, transaction, logger):
    """Update child distroseries with translations from parent."""
    full_name = "%s_%s" % (child.distribution.name, child.name)
    tables = ['POFile', 'POMsgSet', 'POSubmission']
    copier = MultiTableCopy(
        full_name, tables, restartable=False, logger=logger)

    drop_tables(cursor(), [
        'temp_equiv_template', 'temp_equiv_potmsgset', 'temp_inert_pomsgsets',
        'temp_changed_pofiles'])

    # Map parent POTemplates to corresponding POTemplates in child.  This will
    # come in handy later.
    cur = cursor()
    cur.execute("""
        CREATE TEMP TABLE temp_equiv_template AS
        SELECT DISTINCT pt1.id AS id, pt2.id AS new_id
        FROM POTemplate pt1, POTemplate pt2
        WHERE
            pt1.potemplatename = pt2.potemplatename AND
            pt1.sourcepackagename = pt2.sourcepackagename AND
            pt1.distrorelease = %s AND
            pt2.distrorelease = %s
        """ % sqlvalues(child.parentseries, child))
    cur.execute(
        "CREATE UNIQUE INDEX temp_equiv_template_pkey "
        "ON temp_equiv_template(id)")
    cur.execute(
        "CREATE UNIQUE INDEX temp_equiv_template_new_id "
        "ON temp_equiv_template(new_id)")

    # Map parent POTMsgSets to corresponding POTMsgSets in child.
    cur.execute("""
        CREATE TEMP TABLE temp_equiv_potmsgset AS
        SELECT DISTINCT ptms1.id AS id, ptms2.id AS new_id
        FROM POTMsgSet ptms1, POTMsgSet ptms2, temp_equiv_template
        WHERE
            ptms1.potemplate = temp_equiv_template.id AND
            ptms2.potemplate = temp_equiv_template.new_id AND
            (ptms1.alternative_msgid = ptms2.alternative_msgid OR
             (ptms1.alternative_msgid IS NULL AND
              ptms2.alternative_msgid IS NULL AND
              ptms1.primemsgid = ptms2.primemsgid AND
              (ptms1.context = ptms2.context OR
               (ptms1.context IS NULL AND ptms2.context IS NULL))))
        """)
    cur.execute(
        "CREATE UNIQUE INDEX temp_equiv_potmsgset_pkey "
        "ON temp_equiv_potmsgset(id)")
    cur.execute(
        "CREATE UNIQUE INDEX temp_equiv_potmsgset_new_id "
        "ON temp_equiv_potmsgset(new_id)")

    holding_tables = {
        'pofile': copier.getHoldingTableName('POFile'),
        'pomsgset': copier.getHoldingTableName('POMsgSet'),
        'posubmission': copier.getHoldingTableName('POSubmission'),
        }

    query_parameters = {
        'pofile_holding_table': holding_tables['pofile'],
        'pomsgset_holding_table': holding_tables['pomsgset'],
        'posubmission_holding_table': holding_tables['posubmission'],
        }

    # ### POFile ###

    def prepare_pofile_batch(
        holding_table, source_table, batch_size, start_id, end_id):
        """Prepare pouring of a batch of POfiles.

        Deletes any POFiles in the batch that already have equivalents in
        the source table.  Such rows would violate a unique constraint on
        the tuple (potemplate, language, variant), where null variants are
        considered equal.

        Any such POFiles must have been added after the POFiles were
        extracted, so we assume they are newer and better than what we
        have in our holding table.
        """
        batch_clause = (
            "holding.id >= %s AND holding.id < %s"
            % sqlvalues(start_id, end_id))
        cursor().execute("""
            DELETE FROM %s AS holding
            USING POFile pf
            WHERE %s AND
                holding.potemplate = pf.potemplate AND
                holding.language = pf.language AND
                COALESCE(holding.variant, ''::text) =
                    COALESCE(pf.variant, ''::text)
            """ % (holding_table, batch_clause))

    # Extract POFiles from parent whose potemplate has an equivalent in child.
    # Some of those POFiles will also have equivalents in child, in which case
    # we'll want to link to them in following extractions, but we won't be
    # pouring those POFiles themselves.
    pofiles_inert_where = """
        EXISTS (
            SELECT *
            FROM temp_equiv_template, POFile
            WHERE
                holding.potemplate = temp_equiv_template.id AND
                POFile.potemplate = temp_equiv_template.new_id AND
                POFile.language = holding.language AND
                COALESCE(POFile.variant, ''::text) =
                    COALESCE(holding.variant, ''::text)
        )
        """

    copier.extract(
        'POFile', where_clause="potemplate = temp_equiv_template.id",
        inert_where=pofiles_inert_where,
        batch_pouring_callback=prepare_pofile_batch,
        external_joins=['temp_equiv_template'])
    cur = cursor()

    # The new POFiles have their unreviewed_count set to zero.  Also, we're
    # not copying templates, but we need to update the copied POFiles'
    # potemplate references much in the same way as MultiTableCopy would do
    # for us had we also been copying templates.
    cur.execute("""
        UPDATE %(pofile_holding_table)s AS holding
        SET
            unreviewed_count = 0,
            potemplate = temp_equiv_template.new_id
        FROM temp_equiv_template
        WHERE
            holding.potemplate = temp_equiv_template.id AND
            holding.new_id IS NOT NULL
        """ % query_parameters)

    # To make our linking between holding tables work, we'll want the POFiles
    # we're not copying (i.e. the inert ones) to have new_id pointing to the
    # already-existing equivalent POFiles in the child distroseries.
    # MultiTableCopy.extract initialized these to null for us.  We're going to
    # set them here to make the next extract() pick up the new foreign-key
    # values.  We'll simply delete those rows before they can be poured so as
    # to avoid confusing MultiTableCopy.
    cur.execute("""
        UPDATE %(pofile_holding_table)s AS holding
        SET new_id = pf.id
        FROM POFile pf, temp_equiv_template
        WHERE
            holding.potemplate = temp_equiv_template.id AND
            pf.potemplate = temp_equiv_template.new_id AND
            holding.language = pf.language AND
            COALESCE(holding.variant, ''::text) =
                COALESCE(pf.variant, ''::text) AND
            holding.new_id IS NULL
        """ % query_parameters)

    # ### POMsgSet ###

    def prepare_pomsgset_batch(
        holding_table, source_table, batch_size, start_id, end_id):
        """Prepare pouring of a batch of `POMsgSet`s.

        Deletes any `POMsgSet`s in the batch that already have equivalents in
        the source table (same potmsgset and pofile, on which the source table
        has a unique index).  Any such `POMsgSet`s must have been added after
        the `POMsgSet`s were extracted, so we assume they are newer and better
        than what we have in our holding table.

        Also deletes `POMsgSet`s in the batch that refer to `POFile`s that do
        not exist.  Any such `POFile`s must have been deleted from their
        holding table after they were extracted.
        """
        batch_clause = (
            "holding.id >= %s AND holding.id < %s"
            % sqlvalues(start_id, end_id))
        cur = cursor()
        cur.execute("""
            DELETE FROM %s AS holding
            USING POMsgSet pms
            WHERE %s AND
                holding.potmsgset = pms.potmsgset AND
                holding.pofile = pms.pofile
            """ % (holding_table, batch_clause))
        cur.execute("""
            DELETE FROM %s AS holding
            WHERE %s AND
                NOT EXISTS (
                    SELECT * FROM POFile WHERE holding.pofile = POFile.id
                    )
            """ % (holding_table, batch_clause))

    # We'll extract POMsgSets that already have equivalents in the child
    # distroseries, to make it easier to copy POSubmissions for them
    # later, but we won't actually copy those POMsgSets.
    pomsgset_inert_where = """
        EXISTS (
            SELECT *
            FROM
                %(pofile_holding_table)s pfh,
                temp_equiv_potmsgset,
                POMsgSet pms
            WHERE
                holding.potmsgset = temp_equiv_potmsgset.id AND
                temp_equiv_potmsgset.new_id = pms.potmsgset AND
                holding.pofile = pfh.id AND
                pfh.new_id = pms.pofile
            )
        """ % query_parameters

    copier.extract(
        'POMsgSet', joins=['POFile'], inert_where=pomsgset_inert_where,
        batch_pouring_callback=prepare_pomsgset_batch)
    cur = cursor()

    # Set potmsgset to point to equivalent POTMsgSet in copy's POFile.  This
    # is similar to what MultiTableCopy would have done for us had we included
    # POTMsgSet in the copy operation.
    cur.execute("""
        UPDATE %(pomsgset_holding_table)s AS holding
        SET potmsgset = temp_equiv_potmsgset.new_id
        FROM temp_equiv_potmsgset
        WHERE holding.potmsgset = temp_equiv_potmsgset.id
        """ % query_parameters)

    # Map new_ids in holding to those of child distroseries' corresponding
    # POMsgSets.
    cur.execute("""
        UPDATE %(pomsgset_holding_table)s AS holding
        SET new_id = pms.id
        FROM POMsgSet pms
        WHERE
            holding.new_id IS NULL AND
            holding.potmsgset = pms.potmsgset AND
            holding.pofile = pms.pofile
        """ % query_parameters)

    # Keep some information about POMsgSets we won't be copying.  We'll be
    # removing those later, and even after that, the mapping information will
    # be needed.  We've just messed with the inert POMsgSets' new_id fields,
    # but we can still recognize each of these by the fact that its new_id
    # will refer to an already existing POMsgSet.
    cur.execute("""
        CREATE TEMP TABLE temp_inert_pomsgsets AS
        SELECT
            holding.id,
            holding.new_id,
            holding.iscomplete,
            holding.date_reviewed,
            holding.reviewer
        FROM %(pomsgset_holding_table)s holding, POMsgSet source
        WHERE holding.new_id = source.id
        """ % query_parameters)
    cur.execute(
        "CREATE UNIQUE INDEX inert_pomsgset_idx "
        "ON temp_inert_pomsgsets(id)")
    cur.execute(
        "CREATE UNIQUE INDEX inert_pomsgset_newid_idx "
        "ON temp_inert_pomsgsets(new_id)")

    # ### POSubmission ###

    def prepare_posubmission_batch(
        holding_table, source_table, batch_size, start_id, end_id):
        """Prepare pouring of a batch of `POSubmission`s.

        Deletes any `POSubmission`s in the batch that already have equivalents
        in the source table (same potranslation, pomsgset, and pluralform; or
        active and same pomsgset and pluralform).  Any such equivalents must
        have been added or made active after the `POMsgSet`s were extracted,
        so we assume they are newer and better than what we have in our
        holding table.

        Also deletes `POSubmission`s in the batch that refer to `POMsgSet`s
        that do not exist.  Any such `POSubmission`s must have been deleted
        from their holding table after they were extracted.
        """
        batch_clause = (
            "holding.id >= %s AND holding.id < %s"
            % sqlvalues(start_id, end_id))
        cur = cursor()

        # Don't pour POSubmissions whose POMsgSets have disappeared.
        cur.execute("""
            DELETE FROM %s AS holding
            WHERE %s AND
                NOT EXISTS (
                    SELECT *
                    FROM POMsgSet
                    WHERE holding.pomsgset = POMsgSet.id
                    )
            """ % (holding_table, batch_clause))

        # Don't pour POSubmissions for which the child already has a better
        # replacement.
        cur.execute("""
            DELETE FROM %s AS holding
            USING POSubmission better
            WHERE %s AND
                holding.pomsgset = better.pomsgset AND
                holding.pluralform = better.pluralform AND
                holding.potranslation = better.potranslation
            """ % (holding_table, batch_clause))

        # Deactivate POSubmissions we're about to replace with better ones
        # from the parent.
        cur.execute("""
            UPDATE POSubmission AS ps
            SET active = false
            FROM %s holding
            WHERE %s AND
                holding.pomsgset = ps.pomsgset AND
                holding.pluralform = ps.pluralform AND
                ps.active
            """ % (holding_table, batch_clause))

    # Exclude POSubmissions for which an equivalent (potranslation, pomsgset,
    # pluralform) exists, or we'd be introducing needless duplicates.  Don't
    # offer replacements for message sets that the child has newer submissions
    # for, i.e. ones with the same (pomsgset, pluralform) whose datecreated is
    # no older than the one the parent has to offer.
    # The MultiTableCopy does not allow us to join with the source table for
    # our extraction condition, so we make these unnecessary rows inert
    # instead, and after extraction, delete them from the holding table.
    have_better = """
        EXISTS (
            SELECT *
            FROM POSubmission better
            WHERE
                better.pomsgset = holding.new_pomsgset AND
                better.pluralform = holding.pluralform AND
                (better.potranslation = holding.potranslation OR
                 better.datecreated >= holding.datecreated)
        )
        """
    copier.extract(
        'POSubmission', joins=['POMsgSet'],
        where_clause="""
            active AND POSubmission.pomsgset = pms.id AND pms.iscomplete""",
        external_joins=['POMsgSet pms'],
        batch_pouring_callback=prepare_posubmission_batch,
        inert_where=have_better)
    cur = cursor()

    # Remember which POFiles we will affect, so we can update their stats
    # later.
    cur.execute(
        "CREATE TEMP TABLE temp_changed_pofiles "
        "AS SELECT new_id AS id FROM %s" % holding_tables['pofile'])
    cur.execute(
        "CREATE UNIQUE INDEX temp_changed_pofiles_pkey "
        "ON temp_changed_pofiles(id)")

    # Now get rid of those inert rows whose new_ids we messed with, or
    # horrible things will happen during pouring.
    cur.execute("""
        DELETE FROM %(pofile_holding_table)s AS holding
        USING POFile
        WHERE holding.id = POFile.id""" % query_parameters)
    cur.execute("""
        DELETE FROM %(pomsgset_holding_table)s AS holding
        USING POMsgSet
        WHERE holding.new_id = POMsgSet.id""" % query_parameters)

    # Pour copied rows back to source tables.  Contrary to appearances, this
    # is where the heavy lifting is done.
    copier.pour(transaction)

    # Where corresponding POMsgSets already exist but are not complete, and
    # so may have been completed, update review-related status.
    class UpdateReviewInfo:
        """Update review info for incomplete `POMsgSet`s in child.

        Where translations were copied from a complete `POMsgSet` belonging to
        the parent to an existing incomplete `POMsgSet` belonging to the
        child, and the child's `POMsgSet` has not been reviewed since the
        paren's has, copy the parent `POMsgSet`s review information to the
        child `POMsgSet`.
        """
        implements(ITunableLoop)

        def __init__(self, holding_table, transaction_manager):
            self.holding_table = holding_table
            self.transaction_manager = transaction_manager
            cur = cursor()

            cur.execute(
                "SELECT min(new_id), max(new_id) FROM temp_inert_pomsgsets")
            self.lowest_id, self.highest_id = cur.fetchone()

        def isDone(self):
            """See `ITunableLoop`."""
            return (self.lowest_id is None or
                self.lowest_id > self.highest_id)

        def __call__(self, chunk_size):
            """See `ITunableLoop`."""
            chunk_size = int(chunk_size)

            # Figure out what id lies exactly batch_size rows ahead.  There
            # could be huge holes in the numbering here, so we can't just do
            # fixed-size batches of id sequence.
            cur = cursor()
            cur.execute("""
                SELECT new_id
                FROM temp_inert_pomsgsets
                WHERE new_id >= %s
                ORDER BY new_id
                OFFSET %s
                LIMIT 1
                """ % (sqlvalues(self.lowest_id, chunk_size)))
            end_id = cur.fetchone()
            if end_id is not None:
                next = end_id[0]
            else:
                next = self.highest_id

            next += 1

            cur.execute("""
                UPDATE POMsgSet AS target
                SET
                    reviewer = temp.reviewer,
                    date_reviewed = temp.date_reviewed
                FROM temp_inert_pomsgsets temp
                WHERE
                    target.id = temp.new_id AND
                    temp.iscomplete AND
                    NOT target.iscomplete AND
                    temp.date_reviewed > target.date_reviewed AND
                    temp.id >= %s AND
                    temp.id < %s
                """ % sqlvalues(self.lowest_id, next))

            self.transaction_manager.commit()
            self.transaction_manager.begin()
            self.lowest_id = next

    # Update review information on existing incomplete POMsgSets that may
    # have become complete.
    updater = UpdateReviewInfo(holding_tables['pomsgset'], transaction)
    LoopTuner(updater, 2, 500).run()

    class UpdatePOMsgSetFlags:
        """Update flags on `POMsgSets` that may have been completed.

        Implemented using `LoopTuner`, this sets the iscomplete, isfuzzy, and
        isupdated flags appropriately.  This is done atop the object
        persistence layer, so should not be too arbitrarily mixed with SQL
        manipulation.
        """
        implements(ITunableLoop)

        def __init__(self, holding_table, transaction_manager):
            self.holding_table = holding_table
            self.transaction_manager = transaction_manager
            self.last_seen_id = -1
            self.done = False

        def isDone(self):
            """See `ITunableLoop`."""
            return self.done

        def __call__(self, chunk_size):
            """See `ITunableLoop`."""
            pomsgsets_to_update = POMsgSet.select("""
                id > %s AND
                NOT iscomplete AND
                id IN (SELECT new_id FROM temp_inert_pomsgsets)
                """ % quote(self.last_seen_id),
                orderBy="id", limit=int(chunk_size))
            highest_id = None
            for pomsgset in pomsgsets_to_update:
                pomsgset.updateFlags()
                highest_id = pomsgset.id

            self.transaction_manager.commit()
            self.transaction_manager.begin()

            if highest_id is None:
                self.done = True
            else:
                self.last_seen_id = highest_id

    class UpdatePOFileStats:
        """Update statistics of affected `POFiles`, using `LoopTuner`.

        This action modifies the `POFile` table and could run for some time.
        The work is broken into brief chunks to avoid locking out other client
        processes.

        Uses the object persistence layer, so be careful when mixing with
        direct database access.
        """
        implements(ITunableLoop)

        def __init__(self, transaction):
            """See `ITunableLoop`."""
            self.transaction = transaction
            self.last_seen_id = -1
            self.done = False

        def isDone(self):
            """See `ITunableLoop`."""
            return self.done

        def __call__(self, batch_size):
            """See `ITunableLoop`."""
            pofiles_to_update = POFile.select("""
                id > %s AND
                id IN (SELECT id FROM temp_changed_pofiles)
                """ % quote(self.last_seen_id),
                orderBy="id", limit=int(batch_size))

            highest_id = None
            for pofile in pofiles_to_update:
                pofile.updateStatistics()
                highest_id = pofile.id

            self.transaction.commit()
            self.transaction.begin()

            if highest_id is None:
                self.done = True
            else:
                self.last_seen_id = highest_id

    # Update review information on existing incomplete POMsgSets that may have
    # become complete.
    logger.info("Updating review information on POMsgSets")
    updater = UpdateReviewInfo(holding_tables['pomsgset'], transaction)
    LoopTuner(updater, 2).run()

    # Update other POMsgSet flags.  This uses SQLObject, not raw SQL.
    logger.info("Updating status flags on POMsgSets")
    updater = UpdatePOMsgSetFlags(holding_tables['pomsgset'], transaction)
    LoopTuner(updater, 1).run()

    # Update the statistics cache for every POFile we touched.
    logging.info("Updating statistics on POFiles")
    LoopTuner(UpdatePOFileStats(transaction), 1).run()

    # Clean up after ourselves, in case we get called again this session.
    drop_tables(cursor(), [
        'temp_equiv_template', 'temp_equiv_potmsgset',
        'temp_inert_pomsgsets', 'temp_changed_pofiles'])

    transaction.commit()


class DistroSeries(SQLBase, BugTargetBase, HasSpecificationsMixin,
                   HasTranslationImportsMixin):
    """A particular series of a distribution."""
    implements(
        IDistroSeries, IHasBuildRecords, IHasQueueItems,
        IHasTranslationTemplates, IPublishing)

    _table = 'DistroRelease'
    _defaultOrder = ['distribution', 'version']

    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=True)
    name = StringCol(notNull=True)
    displayname = StringCol(notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    description = StringCol(notNull=True)
    version = StringCol(notNull=True)
    status = EnumCol(
        dbName='releasestatus', notNull=True, schema=DistroSeriesStatus)
    date_created = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    datereleased = UtcDateTimeCol(notNull=False, default=None)
    parentseries =  ForeignKey(
        dbName='parentrelease', foreignKey='DistroSeries', notNull=False)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person', notNull=True)
    driver = ForeignKey(
        foreignKey="Person", dbName="driver", notNull=False, default=None)
    lucilleconfig = StringCol(notNull=False, default=None)
    changeslist = StringCol(notNull=False, default=None)
    nominatedarchindep = ForeignKey(
        dbName='nominatedarchindep',foreignKey='DistroArchSeries',
        notNull=False, default=None)
    messagecount = IntCol(notNull=True, default=0)
    binarycount = IntCol(notNull=True, default=DEFAULT)
    sourcecount = IntCol(notNull=True, default=DEFAULT)
    defer_translation_imports = BoolCol(notNull=True, default=True)
    hide_all_translations = BoolCol(notNull=True, default=True)
    language_pack_base = ForeignKey(
        foreignKey="LanguagePack", dbName="language_pack_base", notNull=False,
        default=None)
    language_pack_delta = ForeignKey(
        foreignKey="LanguagePack", dbName="language_pack_delta",
        notNull=False, default=None)
    language_pack_proposed = ForeignKey(
        foreignKey="LanguagePack", dbName="language_pack_proposed",
        notNull=False, default=None)
    language_pack_full_export_requested = BoolCol(notNull=True, default=False)

    architectures = SQLMultipleJoin(
        'DistroArchSeries', joinColumn='distroseries',
        orderBy='architecturetag')
    binary_package_caches = SQLMultipleJoin('DistroSeriesPackageCache',
        joinColumn='distroseries', orderBy='name')
    language_packs = SQLMultipleJoin(
        'LanguagePack', joinColumn='distroseries', orderBy='-date_exported')
    sections = SQLRelatedJoin(
        'Section', joinColumn='distrorelease', otherColumn='section',
        intermediateTable='SectionSelection')

    @property
    def upload_components(self):
        """See `IDistroSeries`."""
        return Component.select("""
            ComponentSelection.distrorelease = %s AND
            Component.id = ComponentSelection.component
            """ % self.id,
            clauseTables=["ComponentSelection"])

    @property
    def components(self):
        """See `IDistroSeries`."""
        # XXX julian 2007-06-25
        # This is filtering out the partner component for now, until
        # the second stage of the partner repo arrives in 1.1.8.
        return Component.select("""
            ComponentSelection.distrorelease = %s AND
            Component.id = ComponentSelection.component AND
            Component.name != 'partner'
            """ % self.id,
            clauseTables=["ComponentSelection"])

    @property
    def all_milestones(self):
        """See IDistroSeries."""
        return Milestone.selectBy(
            distroseries=self, orderBy=['dateexpected', 'name'])

    @property
    def milestones(self):
        """See IDistroSeries."""
        return Milestone.selectBy(
            distroseries=self, visible=True, orderBy=['dateexpected', 'name'])

    @property
    def parent(self):
        """See IDistroSeries."""
        return self.distribution

    @property
    def drivers(self):
        """See IDistroSeries."""
        drivers = set()
        drivers.add(self.driver)
        drivers = drivers.union(self.distribution.drivers)
        drivers.discard(None)
        return sorted(drivers, key=lambda driver: driver.browsername)

    @property
    def bugcontact(self):
        """See IDistroSeries."""
        return self.distribution.bugcontact

    @property
    def security_contact(self):
        """See IDistroSeries."""
        return self.distribution.security_contact

    @property
    def sortkey(self):
        """A string to be used for sorting distro seriess.

        This is designed to sort alphabetically by distro and series name,
        except that Ubuntu will be at the top of the listing.
        """
        result = ''
        if self.distribution.name == 'ubuntu':
            result += '-'
        result += self.distribution.name + self.name
        return result

    @property
    def packagings(self):
        # We join through sourcepackagename to be able to ORDER BY it,
        # and this code also uses prejoins to avoid fetching data later
        # on.
        packagings = Packaging.select(
            "Packaging.sourcepackagename = SourcePackageName.id "
            "AND DistroRelease.id = Packaging.distrorelease "
            "AND DistroRelease.id = %d" % self.id,
            prejoinClauseTables=["SourcePackageName", ],
            clauseTables=["SourcePackageName", "DistroRelease"],
            prejoins=["productseries", "productseries.product"],
            orderBy=["SourcePackageName.name"]
            )
        return packagings

    @property
    def supported(self):
        return self.status in [
            DistroSeriesStatus.CURRENT,
            DistroSeriesStatus.SUPPORTED
            ]

    @property
    def active(self):
        return self.status in [
            DistroSeriesStatus.DEVELOPMENT,
            DistroSeriesStatus.FROZEN,
            DistroSeriesStatus.CURRENT,
            DistroSeriesStatus.SUPPORTED
            ]

    @property
    def distroserieslanguages(self):
        result = DistroSeriesLanguage.select(
            "DistroReleaseLanguage.language = Language.id AND "
            "DistroReleaseLanguage.distrorelease = %d AND "
            "Language.visible = TRUE" % self.id,
            prejoinClauseTables=["Language"],
            clauseTables=["Language"],
            prejoins=["distroseries"],
            orderBy=["Language.englishname"])
        return result

    @cachedproperty('_previous_serieses_cached')
    def previous_serieses(self):
        """See IDistroSeries."""
        # This property is cached because it is used intensely inside
        # sourcepackage.py; avoiding regeneration reduces a lot of
        # count(*) queries.
        datereleased = self.datereleased
        # if this one is unreleased, use the last released one
        if not datereleased:
            datereleased = 'NOW'
        results = DistroSeries.select('''
                distribution = %s AND
                datereleased < %s
                ''' % sqlvalues(self.distribution.id, datereleased),
                orderBy=['-datereleased'])
        return list(results)

    def canUploadToPocket(self, pocket):
        """See IDistroSeries."""
        # Allow everything for distroseries in FROZEN state.
        if self.status == DistroSeriesStatus.FROZEN:
            return True

        # Define stable/released states.
        stable_states = (DistroSeriesStatus.SUPPORTED,
                         DistroSeriesStatus.CURRENT)

        # Deny uploads for RELEASE pocket in stable states.
        if (pocket == PackagePublishingPocket.RELEASE and
            self.status in stable_states):
            return False

        # Deny uploads for post-release pockets in unstable states.
        if (pocket != PackagePublishingPocket.RELEASE and
            self.status not in stable_states):
            return False

        # Allow anything else.
        return True

    def updatePackageCount(self):
        """See IDistroSeries."""

        # first update the source package count
        query = """
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.status = %s AND
            SourcePackagePublishingHistory.pocket = %s AND
            SourcePackagePublishingHistory.sourcepackagerelease =
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename =
                SourcePackageName.id
            """ % sqlvalues(
                    self,
                    self.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.PUBLISHED,
                    PackagePublishingPocket.RELEASE)
        self.sourcecount = SourcePackageName.select(
            query, distinct=True,
            clauseTables=['SourcePackageRelease',
                          'SourcePackagePublishingHistory']).count()


        # next update the binary count
        clauseTables = ['DistroArchRelease', 'BinaryPackagePublishingHistory',
                        'BinaryPackageRelease']
        query = """
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.pocket = %s AND
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s
            """ % sqlvalues(
                    PackagePublishingStatus.PUBLISHED,
                    PackagePublishingPocket.RELEASE,
                    self,
                    self.distribution.all_distro_archive_ids)
        ret = BinaryPackageName.select(
            query, distinct=True, clauseTables=clauseTables).count()
        self.binarycount = ret

    @property
    def architecturecount(self):
        """See IDistroSeries."""
        return self.architectures.count()

    @property
    def fullseriesname(self):
        return "%s %s" % (
            self.distribution.name.capitalize(), self.name.capitalize())

    @property
    def bugtargetname(self):
        """See IBugTarget."""
        return self.fullseriesname
        # XXX mpt 2007-07-10 bugs 113258, 113262:
        # The distribution's and series' names should be used instead
        # of fullseriesname.

    @property
    def bugtargetdisplayname(self):
        """See IBugTarget."""
        return self.fullseriesname

    @property
    def last_full_language_pack_exported(self):
        return LanguagePack.selectFirstBy(
            distroseries=self, type=LanguagePackType.FULL,
            orderBy='-date_exported')

    @property
    def last_delta_language_pack_exported(self):
        return LanguagePack.selectFirstBy(
            distroseries=self, type=LanguagePackType.DELTA,
            updates=self.language_pack_base, orderBy='-date_exported')

    def searchTasks(self, search_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        search_params.setDistroSeries(self)
        return BugTaskSet().search(search_params)

    def getUsedBugTags(self):
        """See IBugTarget."""
        return get_bug_tags("BugTask.distrorelease = %s" % sqlvalues(self))

    def getUsedBugTagsWithOpenCounts(self, user):
        """See IBugTarget."""
        return get_bug_tags_open_count(
            "BugTask.distrorelease = %s" % sqlvalues(self), user)

    @property
    def has_any_specifications(self):
        """See IHasSpecifications."""
        return self.all_specifications.count()

    @property
    def all_specifications(self):
        return self.specifications(filter=[SpecificationFilter.ALL])

    def specifications(self, sort=None, quantity=None, filter=None):
        """See IHasSpecifications.

        In this case the rules for the default behaviour cover three things:

          - acceptance: if nothing is said, ACCEPTED only
          - completeness: if nothing is said, ANY
          - informationalness: if nothing is said, ANY

        """

        # Make a new list of the filter, so that we do not mutate what we
        # were passed as a filter
        if not filter:
            # filter could be None or [] then we decide the default
            # which for a distroseries is to show everything approved
            filter = [SpecificationFilter.ACCEPTED]

        # defaults for completeness: in this case we don't actually need to
        # do anything, because the default is ANY

        # defaults for acceptance: in this case, if nothing is said about
        # acceptance, we want to show only accepted specs
        acceptance = False
        for option in [
            SpecificationFilter.ACCEPTED,
            SpecificationFilter.DECLINED,
            SpecificationFilter.PROPOSED]:
            if option in filter:
                acceptance = True
        if acceptance is False:
            filter.append(SpecificationFilter.ACCEPTED)

        # defaults for informationalness: we don't have to do anything
        # because the default if nothing is said is ANY

        # sort by priority descending, by default
        if sort is None or sort == SpecificationSort.PRIORITY:
            order = ['-priority', 'Specification.definition_status',
                     'Specification.name']
        elif sort == SpecificationSort.DATE:
            # we are showing specs for a GOAL, so under some circumstances
            # we care about the order in which the specs were nominated for
            # the goal, and in others we care about the order in which the
            # decision was made.

            # we need to establish if the listing will show specs that have
            # been decided only, or will include proposed specs.
            show_proposed = set([
                SpecificationFilter.ALL,
                SpecificationFilter.PROPOSED,
                ])
            if len(show_proposed.intersection(set(filter))) > 0:
                # we are showing proposed specs so use the date proposed
                # because not all specs will have a date decided.
                order = ['-Specification.datecreated', 'Specification.id']
            else:
                # this will show only decided specs so use the date the spec
                # was accepted or declined for the sprint
                order = ['-Specification.date_goal_decided',
                         '-Specification.datecreated',
                         'Specification.id']

        # figure out what set of specifications we are interested in. for
        # distroseries, we need to be able to filter on the basis of:
        #
        #  - completeness.
        #  - goal status.
        #  - informational.
        #
        base = 'Specification.distrorelease = %s' % self.id
        query = base
        # look for informational specs
        if SpecificationFilter.INFORMATIONAL in filter:
            query += (' AND Specification.implementation_status = %s' %
              quote(SpecificationImplementationStatus.INFORMATIONAL))

        # filter based on completion. see the implementation of
        # Specification.is_complete() for more details
        completeness =  Specification.completeness_clause

        if SpecificationFilter.COMPLETE in filter:
            query += ' AND ( %s ) ' % completeness
        elif SpecificationFilter.INCOMPLETE in filter:
            query += ' AND NOT ( %s ) ' % completeness

        # look for specs that have a particular goalstatus (proposed,
        # accepted or declined)
        if SpecificationFilter.ACCEPTED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.ACCEPTED.value)
        elif SpecificationFilter.PROPOSED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.PROPOSED.value)
        elif SpecificationFilter.DECLINED in filter:
            query += ' AND Specification.goalstatus = %d' % (
                SpecificationGoalStatus.DECLINED.value)

        # ALL is the trump card
        if SpecificationFilter.ALL in filter:
            query = base

        # Filter for specification text
        for constraint in filter:
            if isinstance(constraint, basestring):
                # a string in the filter is a text search filter
                query += ' AND Specification.fti @@ ftq(%s) ' % quote(
                    constraint)

        # now do the query, and remember to prejoin to people
        results = Specification.select(query, orderBy=order, limit=quantity)
        return results.prejoin(['assignee', 'approver', 'drafter'])

    def getSpecification(self, name):
        """See ISpecificationTarget."""
        return self.distribution.getSpecification(name)

    def getDistroSeriesLanguage(self, language):
        """See IDistroSeries."""
        return DistroSeriesLanguage.selectOneBy(
            distroseries=self, language=language)

    def getDistroSeriesLanguageOrDummy(self, language):
        """See IDistroSeries."""
        drl = self.getDistroSeriesLanguage(language)
        if drl is not None:
            return drl
        return DummyDistroSeriesLanguage(self, language)

    def updateStatistics(self, ztm):
        """See IDistroSeries."""
        # first find the set of all languages for which we have pofiles in
        # the distribution that are visible and not English
        langidset = set(
            language.id for language in Language.select('''
                Language.visible = TRUE AND
                Language.id = POFile.language AND
                Language.code != 'en' AND
                POFile.potemplate = POTemplate.id AND
                POTemplate.distrorelease = %s AND
                POTemplate.iscurrent = TRUE
                ''' % sqlvalues(self.id),
                orderBy=['code'],
                distinct=True,
                clauseTables=['POFile', 'POTemplate'])
            )
        # now run through the existing DistroSeriesLanguages for the
        # distroseries, and update their stats, and remove them from the
        # list of languages we need to have stats for
        for distroserieslanguage in self.distroserieslanguages:
            distroserieslanguage.updateStatistics(ztm)
            langidset.discard(distroserieslanguage.language.id)
        # now we should have a set of languages for which we NEED
        # to have a DistroSeriesLanguage
        for langid in langidset:
            drl = DistroSeriesLanguage(distroseries=self, languageID=langid)
            drl.updateStatistics(ztm)
        # lastly, we need to update the message count for this distro
        # series itself
        messagecount = 0
        for potemplate in self.getCurrentTranslationTemplates():
            messagecount += potemplate.messageCount()
        self.messagecount = messagecount
        ztm.commit()

    def getSourcePackage(self, name):
        """See IDistroSeries."""
        if not ISourcePackageName.providedBy(name):
            try:
                name = SourcePackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return SourcePackage(sourcepackagename=name, distroseries=self)

    def getBinaryPackage(self, name):
        """See IDistroSeries."""
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroSeriesBinaryPackage(self, name)

    def getSourcePackageRelease(self, sourcepackagerelease):
        """See IDistroSeries."""
        return DistroSeriesSourcePackageRelease(self, sourcepackagerelease)

    def __getitem__(self, archtag):
        """See IDistroSeries."""
        item = DistroArchSeries.selectOneBy(
            distroseries=self, architecturetag=archtag)
        if item is None:
            raise NotFoundError('Unknown architecture %s for %s %s' % (
                archtag, self.distribution.name, self.name))
        return item

    def getTranslatableSourcePackages(self):
        """See IDistroSeries."""
        query = """
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.iscurrent = TRUE AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id)
        result = SourcePackageName.select(query, clauseTables=['POTemplate'],
            orderBy=['name'], distinct=True)
        return [SourcePackage(sourcepackagename=spn, distroseries=self) for
            spn in result]

    def getUnlinkedTranslatableSourcePackages(self):
        """See IDistroSeries."""
        # Note that both unlinked packages and
        # linked-with-no-productseries packages are considered to be
        # "unlinked translatables".
        query = """
            SourcePackageName.id NOT IN (SELECT DISTINCT
             sourcepackagename FROM Packaging WHERE distrorelease = %s) AND
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id, self.id)
        unlinked = SourcePackageName.select(
            query, clauseTables=['POTemplate'], orderBy=['name'])
        query = """
            Packaging.sourcepackagename = SourcePackageName.id AND
            Packaging.productseries = NULL AND
            POTemplate.sourcepackagename = SourcePackageName.id AND
            POTemplate.distrorelease = %s""" % sqlvalues(self.id)
        linked_but_no_productseries = SourcePackageName.select(
            query, clauseTables=['POTemplate', 'Packaging'], orderBy=['name'])
        result = unlinked.union(linked_but_no_productseries)
        return [SourcePackage(sourcepackagename=spn, distroseries=self) for
            spn in result]

    def getPublishedReleases(self, sourcepackage_or_name, version=None,
                             pocket=None, include_pending=False,
                             exclude_pocket=None, archive=None):
        """See IDistroSeries."""
        # XXX cprov 2006-02-13 bug 31317:
        # We need a standard and easy API, no need
        # to support multiple type arguments, only string name should be
        # the best choice in here, the call site will be clearer.
        if ISourcePackage.providedBy(sourcepackage_or_name):
            spn = sourcepackage_or_name.name
        elif ISourcePackageName.providedBy(sourcepackage_or_name):
            spn = sourcepackage_or_name
        else:
            spns = getUtility(ISourcePackageNameSet)
            spn = spns.queryByName(sourcepackage_or_name)
            if spn is None:
                return []

        queries = ["""
        sourcepackagerelease=sourcepackagerelease.id AND
        sourcepackagerelease.sourcepackagename=%s AND
        distrorelease=%s
        """ % sqlvalues(spn.id, self.id)]

        if pocket is not None:
            queries.append("pocket=%s" % sqlvalues(pocket.value))

        if version is not None:
            queries.append("version=%s" % sqlvalues(version))

        if exclude_pocket is not None:
            queries.append("pocket!=%s" % sqlvalues(exclude_pocket.value))

        if include_pending:
            queries.append("status in (%s, %s)" % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING))
        else:
            queries.append("status=%s" % sqlvalues(
                PackagePublishingStatus.PUBLISHED))

        archives = self.distribution.archiveIdList(archive)
        queries.append("archive IN %s" % sqlvalues(archives))

        published = SourcePackagePublishingHistory.select(
            " AND ".join(queries), clauseTables = ['SourcePackageRelease'])

        return shortlist(published)

    def isUnstable(self):
        """See IDistroSeries."""
        return self.status in [
            DistroSeriesStatus.FROZEN,
            DistroSeriesStatus.DEVELOPMENT,
            DistroSeriesStatus.EXPERIMENTAL,
        ]

    def getSourcesPublishedForAllArchives(self):
        """See IDistroSeries."""
        # Both, PENDING and PUBLISHED sources will be considered for
        # as PUBLISHED. It's part of the assumptions made in:
        # https://launchpad.net/soyuz/+spec/build-unpublished-source
        pend_build_statuses = (
            PackagePublishingStatus.PENDING,
            PackagePublishingStatus.PUBLISHED,
            )

        query = """
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive = Archive.id AND
            SourcePackagePublishingHistory.status in %s
         """ % sqlvalues(self, pend_build_statuses)

        if not self.isUnstable():
            # Stable distroreleases don't allow builds for the release
            # pockets for the primary archives, but they do allow them for
            # the PPA and PARTNER archives.

            # XXX: this should come from a single location where this
            # is specified, not sprinkled around the code.
            allow_release_builds = (ArchivePurpose.PPA, ArchivePurpose.PARTNER)

            query += ("""AND (Archive.purpose in %s OR
                            SourcePackagePublishingHistory.pocket != %s)""" %
                      sqlvalues(allow_release_builds,
                                PackagePublishingPocket.RELEASE))

        return SourcePackagePublishingHistory.select(
            query, clauseTables=['Archive'], orderBy="id")

    def getSourcePackagePublishing(self, status, pocket, component=None,
                                   archive=None):
        """See IDistroSeries."""
        archives = self.distribution.archiveIdList(archive)

        clause = """
            SourcePackagePublishingHistory.sourcepackagerelease=
                SourcePackageRelease.id AND
            SourcePackageRelease.sourcepackagename=
                SourcePackageName.id AND
            SourcePackagePublishingHistory.distrorelease=%s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.status=%s AND
            SourcePackagePublishingHistory.pocket=%s
            """ %  sqlvalues(self, archives, status, pocket)

        if component:
            clause += (
                " AND SourcePackagePublishingHistory.component=%s"
                % sqlvalues(component)
                )

        orderBy = ['SourcePackageName.name']
        clauseTables = ['SourcePackageRelease', 'SourcePackageName']

        return SourcePackagePublishingHistory.select(
            clause, orderBy=orderBy, clauseTables=clauseTables)

    def getBinaryPackagePublishing(
        self, name=None, version=None, archtag=None, sourcename=None,
        orderBy=None, pocket=None, component=None, archive=None):
        """See IDistroSeries."""
        archives = self.distribution.archiveIdList(archive)

        query = ["""
        BinaryPackagePublishingHistory.binarypackagerelease =
            BinaryPackageRelease.id AND
        BinaryPackagePublishingHistory.distroarchrelease =
            DistroArchRelease.id AND
        BinaryPackageRelease.binarypackagename =
            BinaryPackageName.id AND
        BinaryPackageRelease.build =
            Build.id AND
        Build.sourcepackagerelease =
            SourcePackageRelease.id AND
        SourcePackageRelease.sourcepackagename =
            SourcePackageName.id AND
        DistroArchRelease.distrorelease = %s AND
        BinaryPackagePublishingHistory.archive IN %s AND
        BinaryPackagePublishingHistory.status = %s
        """ % sqlvalues(self, archives, PackagePublishingStatus.PUBLISHED)]

        if name:
            query.append('BinaryPackageName.name = %s' % sqlvalues(name))

        if version:
            query.append('BinaryPackageRelease.version = %s'
                      % sqlvalues(version))

        if archtag:
            query.append('DistroArchRelease.architecturetag = %s'
                      % sqlvalues(archtag))

        if sourcename:
            query.append(
                'SourcePackageName.name = %s' % sqlvalues(sourcename))

        if pocket:
            query.append(
                'BinaryPackagePublishingHistory.pocket = %s'
                % sqlvalues(pocket))

        if component:
            query.append(
                'BinaryPackagePublishingHistory.component = %s'
                % sqlvalues(component))

        query = " AND ".join(query)

        clauseTables = ['BinaryPackagePublishingHistory', 'DistroArchRelease',
                        'BinaryPackageRelease', 'BinaryPackageName', 'Build',
                        'SourcePackageRelease', 'SourcePackageName' ]

        result = BinaryPackagePublishingHistory.select(
            query, distinct=False, clauseTables=clauseTables, orderBy=orderBy)

        return result

    def publishedBinaryPackages(self, component=None):
        """See IDistroSeries."""
        # XXX sabdfl 2005-07-04: This can become a utility when that works
        # this is used by the debbugs import process, mkdebwatches
        pubpkgset = getUtility(IPublishedPackageSet)
        result = pubpkgset.query(distroseries=self, component=component)
        return [BinaryPackageRelease.get(pubrecord.binarypackagerelease)
                for pubrecord in result]

    def getBuildRecords(self, build_state=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        # find out the distroarchseries in question
        arch_ids = [arch.id for arch in self.architectures]
        # use facility provided by IBuildSet to retrieve the records
        return getUtility(IBuildSet).getBuildsByArchIds(
            arch_ids, build_state, name, pocket)

    def createUploadedSourcePackageRelease(
        self, sourcepackagename, version, maintainer, builddepends,
        builddependsindep, architecturehintlist, component, creator,
        urgency, changelog, dsc, dscsigningkey, section,
        dsc_maintainer_rfc822, dsc_standards_version, dsc_format,
        dsc_binaries, archive, copyright, dateuploaded=DEFAULT):
        """See IDistroSeries."""
        return SourcePackageRelease(
            uploaddistroseries=self, sourcepackagename=sourcepackagename,
            version=version, maintainer=maintainer, dateuploaded=dateuploaded,
            builddepends=builddepends, builddependsindep=builddependsindep,
            architecturehintlist=architecturehintlist, component=component,
            creator=creator, urgency=urgency, changelog=changelog, dsc=dsc,
            dscsigningkey=dscsigningkey, section=section,
            dsc_maintainer_rfc822=dsc_maintainer_rfc822, dsc_format=dsc_format,
            dsc_standards_version=dsc_standards_version, copyright=copyright,
            dsc_binaries=dsc_binaries, upload_archive=archive)

    def getComponentByName(self, name):
        """See IDistroSeries."""
        comp = Component.byName(name)
        if comp is None:
            raise NotFoundError(name)
        permitted = set(self.components)
        if comp in permitted:
            return comp
        raise NotFoundError(name)

    def getSectionByName(self, name):
        """See IDistroSeries."""
        section = Section.byName(name)
        if section is None:
            raise NotFoundError(name)
        permitted = set(self.sections)
        if section in permitted:
            return section
        raise NotFoundError(name)

    def removeOldCacheItems(self, log):
        """See IDistroSeries."""

        # get the set of package names that should be there
        bpns = set(BinaryPackageName.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(
                    self,
                    self.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.REMOVED),
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory',
                          'DistroArchRelease',
                          'BinaryPackageRelease']))

        # remove the cache entries for binary packages we no longer want
        for cache in self.binary_package_caches:
            if cache.binarypackagename not in bpns:
                log.debug(
                    "Removing binary cache for '%s' (%s)"
                    % (cache.name, cache.id))
                cache.destroySelf()

    def updateCompletePackageCache(self, log, ztm):
        """See IDistroSeries."""

        # get the set of package names to deal with
        bpns = list(BinaryPackageName.select("""
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(
                    self,
                    self.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.REMOVED),
            distinct=True,
            clauseTables=['BinaryPackagePublishingHistory',
                          'DistroArchRelease',
                          'BinaryPackageRelease']))

        # now ask each of them to update themselves. commit every 100
        # packages
        counter = 0
        for bpn in bpns:
            log.debug("Considering binary '%s'" % bpn.name)
            self.updatePackageCache(bpn, log)
            counter += 1
            if counter > 99:
                counter = 0
                if ztm is not None:
                    log.debug("Committing")
                    ztm.commit()

    def updatePackageCache(self, binarypackagename, log):
        """See IDistroSeries."""

        # get the set of published binarypackagereleases
        bprs = BinaryPackageRelease.select("""
            BinaryPackageRelease.binarypackagename = %s AND
            BinaryPackageRelease.id =
                BinaryPackagePublishingHistory.binarypackagerelease AND
            BinaryPackagePublishingHistory.distroarchrelease =
                DistroArchRelease.id AND
            DistroArchRelease.distrorelease = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.status != %s
            """ % sqlvalues(
                    binarypackagename,
                    self,
                    self.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.REMOVED),
            orderBy='-datecreated',
            clauseTables=['BinaryPackagePublishingHistory',
                          'DistroArchRelease'],
            distinct=True)
        if bprs.count() == 0:
            log.debug("No binary releases found.")
            return

        # find or create the cache entry
        cache = DistroSeriesPackageCache.selectOne("""
            distrorelease = %s AND
            binarypackagename = %s
            """ % sqlvalues(self.id, binarypackagename.id))
        if cache is None:
            log.debug("Creating new binary cache entry.")
            cache = DistroSeriesPackageCache(
                distroseries=self,
                binarypackagename=binarypackagename)

        # make sure the cached name, summary and description are correct
        cache.name = binarypackagename.name
        cache.summary = bprs[0].summary
        cache.description = bprs[0].description

        # get the sets of binary package summaries, descriptions. there is
        # likely only one, but just in case...

        summaries = set()
        descriptions = set()
        for bpr in bprs:
            log.debug("Considering binary version %s" % bpr.version)
            summaries.add(bpr.summary)
            descriptions.add(bpr.description)

        # and update the caches
        cache.summaries = ' '.join(sorted(summaries))
        cache.descriptions = ' '.join(sorted(descriptions))

    def searchPackages(self, text):
        """See IDistroSeries."""
        drpcaches = DistroSeriesPackageCache.select("""
            distrorelease = %s AND (
            fti @@ ftq(%s) OR
            DistroReleasePackageCache.name ILIKE '%%' || %s || '%%')
            """ % (quote(self.id), quote(text), quote_like(text)),
            selectAlso='rank(fti, ftq(%s)) AS rank' % sqlvalues(text),
            orderBy=['-rank'],
            prejoins=['binarypackagename'],
            distinct=True)
        return [DistroSeriesBinaryPackage(
            distroseries=self,
            binarypackagename=drpc.binarypackagename) for drpc in drpcaches]

    def newArch(self, architecturetag, processorfamily, official, owner):
        """See IDistroSeries."""
        dar = DistroArchSeries(architecturetag=architecturetag,
            processorfamily=processorfamily, official=official,
            distroseries=self, owner=owner)
        return dar

    def newMilestone(self, name, dateexpected=None):
        """See IDistroSeries."""
        return Milestone(name=name, dateexpected=dateexpected,
            distribution=self.distribution, distroseries=self)

    def getLatestUploads(self):
        """See IDistroSeries."""
        query = """
        sourcepackagerelease.id=packageuploadsource.sourcepackagerelease
        AND sourcepackagerelease.sourcepackagename=sourcepackagename.id
        AND packageuploadsource.packageupload=packageupload.id
        AND packageupload.status=%s
        AND packageupload.distrorelease=%s
        AND packageupload.archive IN %s
        """ % sqlvalues(
                PackageUploadStatus.DONE,
                self,
                self.distribution.all_distro_archive_ids)

        last_uploads = SourcePackageRelease.select(
            query, limit=5, prejoins=['sourcepackagename'],
            clauseTables=['SourcePackageName', 'PackageUpload',
                          'PackageUploadSource'],
            orderBy=['-packageupload.id'])

        distro_sprs = [
            self.getSourcePackageRelease(spr) for spr in last_uploads]

        return distro_sprs

    def createQueueEntry(self, pocket, changesfilename, changesfilecontent,
                         archive, signing_key=None):
        """See IDistroSeries."""
        # We store the changes file in the librarian to avoid having to
        # deal with broken encodings in these files; this will allow us
        # to regenerate these files as necessary.
        #
        # The use of StringIO here should be safe: we do not encoding of
        # the content in the changes file (as doing so would be guessing
        # at best, causing unpredictable corruption), and simply pass it
        # off to the librarian.
        changes_file = getUtility(ILibraryFileAliasSet).create(
            changesfilename, len(changesfilecontent),
            StringIO(changesfilecontent), 'text/plain')

        return PackageUpload(
            distroseries=self, status=PackageUploadStatus.NEW,
            pocket=pocket, archive=archive,
            changesfile=changes_file, signing_key=signing_key)

    def getPackageUploadQueue(self, state):
        """See IDistroSeries."""
        return PackageUploadQueue(self, state)

    def getQueueItems(self, status=None, name=None, version=None,
                      exact_match=False, pocket=None, archive=None):
        """See IDistroSeries."""

        default_clauses = ["""
            packageupload.distrorelease = %s""" % sqlvalues(self)]

        # Restrict result to given archives.
        archives = self.distribution.archiveIdList(archive)

        default_clauses.append("""
        packageupload.archive IN %s""" % sqlvalues(archives))

        # restrict result to a given pocket
        if pocket is not None:
            if not isinstance(pocket, list):
                pocket = [pocket]
            default_clauses.append("""
            packageupload.pocket IN %s""" % sqlvalues(pocket))

        # XXX cprov 2006-06-06:
        # We may reorganise this code, creating some new methods provided
        # by IPackageUploadSet, as: getByStatus and getByName.
        if not status:
            assert not version and not exact_match
            return PackageUpload.select(
                " AND ".join(default_clauses), orderBy=['-id'])

        if not isinstance(status, list):
            status = [status]

        default_clauses.append("""
        packageupload.status IN %s""" % sqlvalues(status))

        if not name:
            assert not version and not exact_match
            return PackageUpload.select(
                " AND ".join(default_clauses), orderBy=['-id'])

        source_where_clauses = default_clauses + ["""
            packageupload.id = packageuploadsource.packageupload
            """]

        build_where_clauses = default_clauses + ["""
            packageupload.id = packageuploadbuild.packageupload
            """]

        custom_where_clauses = default_clauses + ["""
            packageupload.id = packageuploadcustom.packageupload
            """]

        # modify source clause to lookup on sourcepackagerelease
        source_where_clauses.append("""
            packageuploadsource.sourcepackagerelease =
            sourcepackagerelease.id""")
        source_where_clauses.append(
            "sourcepackagerelease.sourcepackagename = sourcepackagename.id")

        # modify build clause to lookup on binarypackagerelease
        build_where_clauses.append(
            "packageuploadbuild.build = binarypackagerelease.build")
        build_where_clauses.append(
            "binarypackagerelease.binarypackagename = binarypackagename.id")

        # modify custom clause to lookup on libraryfilealias
        custom_where_clauses.append(
            "packageuploadcustom.libraryfilealias = "
            "libraryfilealias.id")

        # attempt to exact or similar names in builds, sources and custom
        if exact_match:
            source_where_clauses.append(
                "sourcepackagename.name = '%s'" % name)
            build_where_clauses.append("binarypackagename.name = '%s'" % name)
            custom_where_clauses.append(
                "libraryfilealias.filename='%s'" % name)
        else:
            source_where_clauses.append(
                "sourcepackagename.name LIKE '%%' || %s || '%%'"
                % quote_like(name))

            build_where_clauses.append(
                "binarypackagename.name LIKE '%%' || %s || '%%'"
                % quote_like(name))

            custom_where_clauses.append(
                "libraryfilealias.filename LIKE '%%' || %s || '%%'"
                % quote_like(name))

        # attempt for given version argument, except by custom
        if version:
            # exact or similar matches
            if exact_match:
                source_where_clauses.append(
                    "sourcepackagerelease.version = '%s'" % version)
                build_where_clauses.append(
                    "binarypackagerelease.version = '%s'" % version)
            else:
                source_where_clauses.append(
                    "sourcepackagerelease.version LIKE '%%' || %s || '%%'"
                    % quote_like(version))
                build_where_clauses.append(
                    "binarypackagerelease.version LIKE '%%' || %s || '%%'"
                    % quote_like(version))

        source_clauseTables = [
            'PackageUploadSource',
            'SourcePackageRelease',
            'SourcePackageName',
            ]
        source_orderBy = ['-sourcepackagerelease.dateuploaded']

        build_clauseTables = [
            'PackageUploadBuild',
            'BinaryPackageRelease',
            'BinaryPackageName',
            ]
        build_orderBy = ['-binarypackagerelease.datecreated']

        custom_clauseTables = [
            'PackageUploadCustom',
            'LibraryFileAlias',
            ]
        custom_orderBy = ['-LibraryFileAlias.id']

        source_where_clause = " AND ".join(source_where_clauses)
        source_results = PackageUpload.select(
            source_where_clause, clauseTables=source_clauseTables,
            orderBy=source_orderBy)

        build_where_clause = " AND ".join(build_where_clauses)
        build_results = PackageUpload.select(
            build_where_clause, clauseTables=build_clauseTables,
            orderBy=build_orderBy)

        custom_where_clause = " AND ".join(custom_where_clauses)
        custom_results = PackageUpload.select(
            custom_where_clause, clauseTables=custom_clauseTables,
            orderBy=custom_orderBy)

        return source_results.union(build_results.union(custom_results))

    def createBug(self, bug_params):
        """See canonical.launchpad.interfaces.IBugTarget."""
        # We don't currently support opening a new bug on an IDistroSeries,
        # because internally bugs are reported against IDistroSeries only when
        # targetted to be fixed in that series, which is rarely the case for a
        # brand new bug report.
        raise NotImplementedError(
            "A new bug cannot be filed directly on a distribution series, "
            "because series are meant for \"targeting\" a fix to a specific "
            "version. It's possible that we may change this behaviour to "
            "allow filing a bug on a distribution series in the "
            "not-too-distant future. For now, you probably meant to file "
            "the bug on the distribution instead.")

    def _getBugTaskContextClause(self):
        """See BugTargetBase."""
        return 'BugTask.distrorelease = %s' % sqlvalues(self)

    def initialiseFromParent(self):
        """See IDistroSeries."""
        archives = self.distribution.all_distro_archive_ids
        assert self.parentseries is not None, "Parent series must be present"
        assert SourcePackagePublishingHistory.select("""
            Distrorelease = %s AND
            Archive IN %s""" % sqlvalues(self.id, archives)).count() == 0, (
            "Source Publishing must be empty")
        for arch in self.architectures:
            assert BinaryPackagePublishingHistory.select("""
            Distroarchrelease = %s AND
            Archive IN %s""" % sqlvalues(arch, archives)).count() == 0, (
                "Binary Publishing must be empty")
            try:
                parent_arch = self.parentseries[arch.architecturetag]
                assert parent_arch.processorfamily == arch.processorfamily, (
                       "The arch tags must match the processor families.")
            except KeyError:
                raise AssertionError("Parent series lacks %s" % (
                    arch.architecturetag))
        assert self.nominatedarchindep is not None, (
               "Must have a nominated archindep architecture.")
        assert self.components.count() == 0, (
               "Component selections must be empty.")
        assert self.sections.count() == 0, (
               "Section selections must be empty.")

        # MAINTAINER: dsilvers: 20051031
        # Here we go underneath the SQLObject caching layers in order to
        # generate what will potentially be tens of thousands of rows
        # in various tables. Thus we flush pending updates from the SQLObject
        # layer, perform our work directly in the transaction and then throw
        # the rest of the SQLObject cache away to make sure it hasn't cached
        # anything that is no longer true.

        # Prepare for everything by flushing updates to the database.
        flush_database_updates()
        cur = cursor()

        # Perform the copies
        self._copy_component_and_section_selections(cur)
        self._copy_source_publishing_records(cur)
        for arch in self.architectures:
            parent_arch = self.parentseries[arch.architecturetag]
            self._copy_binary_publishing_records(cur, arch, parent_arch)
        self._copy_lucille_config(cur)

        # Finally, flush the caches because we've altered stuff behind the
        # back of sqlobject.
        flush_database_caches()

    def _copy_lucille_config(self, cur):
        """Copy all lucille related configuration from our parent series."""
        cur.execute('''
            UPDATE DistroRelease SET lucilleconfig=(
                SELECT pdr.lucilleconfig FROM DistroRelease AS pdr
                WHERE pdr.id = %s)
            WHERE id = %s
            ''' % sqlvalues(self.parentseries.id, self.id))

    def _copy_binary_publishing_records(self, cur, arch, parent_arch):
        """Copy the binary publishing records from the parent arch series
        to the given arch series in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket in the PRIMARY and PARTNER
        archives.
        """
        archive_set = getUtility(IArchiveSet)
        for archive in self.parentseries.distribution.all_distro_archives:
            # We only want to copy PRIMARY and PARTNER archives.
            if archive.purpose not in (
                    ArchivePurpose.PRIMARY, ArchivePurpose.PARTNER):
                continue
            target_archive = archive_set.ensure(
                distribution=self.distribution, purpose=archive.purpose,
                owner=None)
            cur.execute('''
                INSERT INTO SecureBinaryPackagePublishingHistory (
                    binarypackagerelease, distroarchrelease, status,
                    component, section, priority, archive, datecreated,
                    datepublished, pocket, embargo)
                SELECT bpph.binarypackagerelease, %s as distroarchrelease,
                       bpph.status, bpph.component, bpph.section, bpph.priority,
                       %s as archive, %s as datecreated, %s as datepublished,
                       %s as pocket, false as embargo
                FROM BinaryPackagePublishingHistory AS bpph
                WHERE bpph.distroarchrelease = %s AND bpph.status in (%s, %s)
                AND
                    bpph.pocket = %s and bpph.archive = %s
                ''' % sqlvalues(arch.id, target_archive, UTC_NOW, UTC_NOW,
                                PackagePublishingPocket.RELEASE,
                                parent_arch.id,
                                PackagePublishingStatus.PENDING,
                                PackagePublishingStatus.PUBLISHED,
                                PackagePublishingPocket.RELEASE,
                                archive))

    def _copy_source_publishing_records(self, cur):
        """Copy the source publishing records from our parent distro series.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket in the PRIMARY and PARTNER
        archives.
        """
        archive_set = getUtility(IArchiveSet)
        for archive in self.parentseries.distribution.all_distro_archives:
            # We only want to copy PRIMARY and PARTNER archives.
            if archive.purpose not in (
                    ArchivePurpose.PRIMARY, ArchivePurpose.PARTNER):
                continue
            target_archive = archive_set.ensure(
                distribution=self.distribution, purpose=archive.purpose,
                owner=None)
            cur.execute('''
                INSERT INTO SecureSourcePackagePublishingHistory (
                    sourcepackagerelease, distrorelease, status, component,
                    section, archive, datecreated, datepublished, pocket,
                    embargo)
                SELECT spph.sourcepackagerelease, %s as distrorelease,
                       spph.status, spph.component, spph.section, %s as archive,
                       %s as datecreated, %s as datepublished,
                       %s as pocket, false as embargo
                FROM SourcePackagePublishingHistory AS spph
                WHERE spph.distrorelease = %s AND spph.status in (%s, %s) AND
                      spph.pocket = %s and spph.archive = %s
                ''' % sqlvalues(self.id, target_archive, UTC_NOW, UTC_NOW,
                                PackagePublishingPocket.RELEASE,
                                self.parentseries.id,
                                PackagePublishingStatus.PENDING,
                                PackagePublishingStatus.PUBLISHED,
                                PackagePublishingPocket.RELEASE,
                                archive))

    def _copy_component_and_section_selections(self, cur):
        """Copy the section and component selections from the parent distro
        series into this one.
        """
        # Copy the component selections
        cur.execute('''
            INSERT INTO ComponentSelection (distrorelease, component)
            SELECT %s AS distrorelease, cs.component AS component
            FROM ComponentSelection AS cs WHERE cs.distrorelease = %s
            ''' % sqlvalues(self.id, self.parentseries.id))
        # Copy the section selections
        cur.execute('''
            INSERT INTO SectionSelection (distrorelease, section)
            SELECT %s as distrorelease, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distrorelease = %s
            ''' % sqlvalues(self.id, self.parentseries.id))

    def _copy_active_translations(self, transaction, logger):
        """Copy active translations from the parent into this one.

        This method is used in two scenarios: when a new distribution series
        is opened for translation, and during periodic updates as new
        translations from the parent series are ported to newer series that
        haven't provided translations of their own for the same strings yet.
        In the former scenario a full copy is drawn from the parent series.

        If this distroseries doesn't have any translatable resource, this
        method will clone all of the parent's current translatable resources;
        otherwise, only the translations that are in the parent but lacking in
        this one will be copied.

        If there is a status change but no translation is changed for a given
        message, we don't have a way to figure whether the change was done in
        the parent or this distroseries, so we don't migrate that.
        """
        if self.parentseries is None:
            # We don't have a parent from where we could copy translations.
            return

        translation_tables = [
            'POTemplate', 'POTMsgSet', 'POMsgIDSighting', 'POFile',
            'POMsgSet', 'POSubmission'
            ]

        full_name = "%s_%s" % (self.distribution.name, self.name)
        copier = MultiTableCopy(full_name, translation_tables, logger=logger)

        if len(self.getCurrentTranslationTemplates()) == 0:
            # We're a new distroseries; copy from scratch
            copy_active_translations_to_new_series(
                self, transaction, copier, logger)
        elif copier.needsRecovery():
            # Recover data from previous, abortive run
            logger.info("A copy was already running.  Resuming...")
            copier.pour(transaction)
        else:
            # Incremental copy of updates from parent distroseries
            copy_active_translations_as_update(self, transaction, logger)

        # XXX: JeroenVermeulen 2007-07-16 bug=124410: Fix up
        # POFile.last_touched_pomsgset for POFiles that had POMsgSets and/or
        # POSubmissions copied in.

    def copyMissingTranslationsFromParent(self, transaction, logger=None):
        """See `IDistroSeries`."""
        if logger is None:
            logger = logging

        assert self.defer_translation_imports, (
            "defer_translation_imports not set!"
            " That would corrupt translation data mixing new imports"
            " with the information being copied.")

        flush_database_updates()
        flush_database_caches()
        self._copy_active_translations(transaction, logger)

    def getPendingPublications(self, archive, pocket, is_careful):
        """See IPublishing."""
        queries = ['distrorelease = %s' % sqlvalues(self)]

        # Query main archive for this distroseries
        queries.append('archive=%s' % sqlvalues(archive))

        # Careful publishing should include all PUBLISHED rows, normal run
        # only includes PENDING ones.
        statuses = [PackagePublishingStatus.PENDING]
        if is_careful:
            statuses.append(PackagePublishingStatus.PUBLISHED)
        queries.append('status IN %s' % sqlvalues(statuses))

        # Restrict to a specific pocket.
        queries.append('pocket = %s' % sqlvalues(pocket))

        # Exclude RELEASE pocket if the distroseries was already released,
        # since it should not change for main archive.
        # We allow RELEASE publishing for PPAs.
        # We also allow RELEASE publishing for partner.
        if (not self.isUnstable() and
            not archive.allowUpdatesToReleasePocket()):
            queries.append(
            'pocket != %s' % sqlvalues(PackagePublishingPocket.RELEASE))

        publications = SourcePackagePublishingHistory.select(
            " AND ".join(queries), orderBy="-id")

        return publications

    def publish(self, diskpool, log, archive, pocket, is_careful=False):
        """See IPublishing."""
        log.debug("Publishing %s-%s" % (self.title, pocket.name))
        log.debug("Attempting to publish pending sources.")

        dirty_pockets = set()
        for spph in self.getPendingPublications(archive, pocket, is_careful):
            if not self.checkLegalPocket(spph, is_careful, log):
                continue
            spph.publish(diskpool, log)
            dirty_pockets.add((self.name, spph.pocket))

        # propagate publication request to each distroarchseries.
        for dar in self.architectures:
            more_dirt = dar.publish(
                diskpool, log, archive, pocket, is_careful)
            dirty_pockets.update(more_dirt)

        return dirty_pockets

    def checkLegalPocket(self, publication, is_careful, log):
        """Check if the publication can happen in the archive."""
        # 'careful' mode re-publishes everything:
        if is_careful:
            return True

        # PPA and PARTNER allow everything.
        if publication.archive.allowUpdatesToReleasePocket():
            return True

        # FROZEN state also allow all pockets to be published.
        if self.status == DistroSeriesStatus.FROZEN:
            return True

        # If we're not republishing, we want to make sure that
        # we're not publishing packages into the wrong pocket.
        # Unfortunately for careful mode that can't hold true
        # because we indeed need to republish everything.
        if (self.isUnstable() and
            publication.pocket != PackagePublishingPocket.RELEASE):
            log.error("Tried to publish %s (%s) into a non-release "
                      "pocket on unstable series %s, skipping"
                      % (publication.displayname, publication.id,
                         self.displayname))
            return False
        if (not self.isUnstable() and
            publication.pocket == PackagePublishingPocket.RELEASE):
            log.error("Tried to publish %s (%s) into release pocket "
                      "on stable series %s, skipping"
                      % (publication.displayname, publication.id,
                         self.displayname))
            return False

        return True

    @property
    def main_archive(self):
        return self.distribution.main_archive

    def getTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.selectBy(distroseries=self)
        result = result.prejoin(['potemplatename'])
        return sorted(
            result, key=lambda x: (-x.priority, x.potemplatename.name))

    def getCurrentTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.select('''
            distrorelease = %s AND
            iscurrent IS TRUE AND
            distrorelease = DistroRelease.id AND
            DistroRelease.distribution = Distribution.id AND
            Distribution.official_rosetta IS TRUE
            ''' % sqlvalues(self),
            clauseTables = ['DistroRelease', 'Distribution'])
        result = result.prejoin(['potemplatename'])
        return sorted(
            result, key=lambda x: (-x.priority, x.potemplatename.name))

    def getObsoleteTranslationTemplates(self):
        """See `IHasTranslationTemplates`."""
        result = POTemplate.select('''
            distrorelease = %s AND
            (iscurrent IS FALSE OR
             (distrorelease = DistroRelease.id AND
              DistroRelease.distribution = Distribution.id AND
              Distribution.official_rosetta IS FALSE))
            ''' % sqlvalues(self.distroseries),
            clauseTables = ['DistroRelease', 'Distribution'])
        result = result.prejoin(['potemplatename'])
        return sorted(
            result, key=lambda x: (-x.priority, x.potemplatename.name))


class DistroSeriesSet:
    implements(IDistroSeriesSet)

    def get(self, distroseriesid):
        """See IDistroSeriesSet."""
        return DistroSeries.get(distroseriesid)

    def translatables(self):
        """See IDistroSeriesSet."""
        return DistroSeries.select(
            "POTemplate.distrorelease=DistroRelease.id",
            clauseTables=['POTemplate'], distinct=True)

    def findByName(self, name):
        """See IDistroSeriesSet."""
        return DistroSeries.selectBy(name=name)

    def queryByName(self, distribution, name):
        """See IDistroSeriesSet."""
        return DistroSeries.selectOneBy(distribution=distribution, name=name)

    def findByVersion(self, version):
        """See IDistroSeriesSet."""
        return DistroSeries.selectBy(version=version)

    def search(self, distribution=None, isreleased=None, orderBy=None):
        """See IDistroSeriesSet."""
        where_clause = ""
        if distribution is not None:
            where_clause += "distribution = %s" % sqlvalues(distribution.id)
        if isreleased is not None:
            if where_clause:
                where_clause += " AND "
            if isreleased:
                # The query is filtered on released releases.
                where_clause += "releasestatus in (%s, %s)" % sqlvalues(
                    DistroSeriesStatus.CURRENT,
                    DistroSeriesStatus.SUPPORTED)
            else:
                # The query is filtered on unreleased releases.
                where_clause += "releasestatus in (%s, %s, %s)" % sqlvalues(
                    DistroSeriesStatus.EXPERIMENTAL,
                    DistroSeriesStatus.DEVELOPMENT,
                    DistroSeriesStatus.FROZEN)
        if orderBy is not None:
            return DistroSeries.select(where_clause, orderBy=orderBy)
        else:
            return DistroSeries.select(where_clause)

    def new(self, distribution, name, displayname, title, summary,
            description, version, parentseries, owner):
        """See IDistroSeriesSet."""
        return DistroSeries(
            distribution=distribution,
            name=name,
            displayname=displayname,
            title=title,
            summary=summary,
            description=description,
            version=version,
            status=DistroSeriesStatus.EXPERIMENTAL,
            parentseries=parentseries,
            owner=owner)

