# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Functions to copy translations from parent to child distroseries."""

__metaclass__ = type

__all__ = [ 'copy_active_translations' ]

import logging

from psycopg import ProgrammingError
from zope.interface import implements

from canonical.database.multitablecopy import MultiTableCopy
from canonical.database.postgresql import allow_sequential_scans, drop_tables
from canonical.database.sqlbase import (
    cursor, flush_database_updates, quote, sqlvalues)
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.pomsgset import POMsgSet
from canonical.launchpad.utilities.looptuner import LoopTuner


def _copy_active_translations_to_new_series(
    child, transaction, copier, logger):
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
    where = 'distroseries = %s AND iscurrent' % quote(child.parent_series)
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
            distroseries = %s,
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


def _prepare_pofile_batch(
    holding_table, source_table, batch_size, start_id, end_id):
    """Prepare pouring of a batch of POfiles.

    Deletes any POFiles in the batch that already have equivalents in the
    source table.  Such rows would violate a unique constraint on the tuple
    (potemplate, language, variant), where null variants are considered equal.

    Any such POFiles must have been added after the POFiles were extracted, so
    we assume they are newer and better than what we have in our holding
    table.
    """
    batch_clause = (
        "holding.id >= %s AND holding.id < %s" % sqlvalues(start_id, end_id))
    cursor().execute("""
        DELETE FROM %s AS holding
        USING POFile pf
        WHERE %s AND
            holding.potemplate = pf.potemplate AND
            holding.language = pf.language AND
            COALESCE(holding.variant, ''::text) =
                COALESCE(pf.variant, ''::text)
        """ % (holding_table, batch_clause))


def _prepare_pofile_merge(copier, transaction, query_parameters):
    """`POFile` chapter of `copy_active_translations_as_update`.

    Extract copies of `POFile`s from parent distroseries into holding table,
    and prepare them for pouring.

    This function is not reusable; it only makes sense as a part of
    `copy_active_translations_as_update`.
    """
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
        batch_pouring_callback=_prepare_pofile_batch,
        external_joins=['temp_equiv_template'])
    transaction.commit()
    transaction.begin()
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


class PreparePOMsgSetPouring:
    """Prevent pouring of `POMsgSet`s whose `POFile`s weren't poured.

    This is a callback, but it takes the form of a class so it can carry some
    extra parameters.
    """
    def __init__(self, lowest_pofile, highest_pofile):
        """Accept parameters that help speed up actual cleanup work.

        :param lowest_pofile: lowest POFile id that we'll be copying
            `POMsgSet`s for.
        :param highest_pofile: highest POFile id that we'll be copying
            `POMsgSet`s for.
        """
        self.lowest_pofile = quote(lowest_pofile)
        self.highest_pofile = quote(highest_pofile)

    def __call__(self, holding_table, source_table):
        cur = cursor()
        # What we'll be doing here probably requires a sequential scan, but
        # the MultiTableCopy disallows those because of index degradation
        # while pouring.  Right now, we want to give the database server the
        # freedom to choose for itself.
        allow_sequential_scans(cur, True)
        # POFile has already been poured by the time this gets invoked; we
        # recognize references to deleted POFiles by the fact that they don't
        # exist in the POFile source table.
        drop_tables(cur, ['temp_final_pofiles'])
        cur.execute("""
            CREATE TEMP TABLE temp_final_pofiles
            ON COMMIT DROP
            AS SELECT id FROM POFile
            WHERE id >= %s AND id <= %s
            ORDER BY id
            """ % (self.lowest_pofile, self.highest_pofile))
        cur.execute("""
            CREATE UNIQUE INDEX temp_final_pofiles_idx
            ON temp_final_pofiles(id)
            """)
        cur.execute("ANALYZE %s" % holding_table)
        cur.execute("ANALYZE temp_final_pofiles_idx")
        cur.execute("""
            DELETE FROM %s
            WHERE pofile NOT IN (SELECT id FROM temp_final_pofiles)
            """ % holding_table)
        allow_sequential_scans(cur, False)


def _prepare_pomsgset_batch(
    holding_table, source_table, batch_size, start_id, end_id):
    """Prepare pouring of a batch of `POMsgSet`s.

    Deletes any `POMsgSet`s in the batch that already have equivalents in the
    source table (same potmsgset and pofile, on which the source table has a
    unique index).  Any such `POMsgSet`s must have been added after the
    `POMsgSet`s were extracted, so we assume they are newer and better than
    what we have in our holding table.

    Also deletes `POMsgSet`s in the batch that refer to `POFile`s that do not
    exist.  Any such `POFile`s must have been deleted from their holding table
    after they were extracted.
    """
    batch_clause = (
        "holding.id >= %s AND holding.id < %s" % sqlvalues(start_id, end_id))
    cur = cursor()
    cur.execute("""
        DELETE FROM %s AS holding
        USING POMsgSet pms
        WHERE %s AND
            holding.potmsgset = pms.potmsgset AND
            holding.pofile = pms.pofile
        """ % (holding_table, batch_clause))


def _prepare_pomsgset_merge(
    copier, transaction, query_parameters, holding_tables, logger):
    """`POFile` chapter of `copy_active_translations_as_update`.

    Extract copies of `POMsgSet`s from parent distroseries, and prepare them
    for pouring.

    This function is not reusable; it only makes sense as a part of
    `copy_active_translations_as_update`.
    """
    # We'll extract POMsgSets that already have equivalents in the child
    # distroseries, to make it easier to copy POSubmissions for them later,
    # but we won't actually copy those POMsgSets.
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

    cur = cursor()
    cur.execute(
        "SELECT min(new_id), max(new_id) FROM %s" % holding_tables['pofile'])
    lowest_pofile, highest_pofile = cur.fetchone()
    prepare_pomsgset_pouring = PreparePOMsgSetPouring(
        lowest_pofile, highest_pofile)

    copier.extract(
        'POMsgSet', joins=['POFile'], inert_where=pomsgset_inert_where,
        pre_pouring_callback=prepare_pomsgset_pouring,
        batch_pouring_callback=_prepare_pomsgset_batch)
    transaction.commit()
    transaction.begin()
    cur = cursor()
    # Make sure we can do fast joins on (potmsgset, pofile) to speed up the
    # delete statement that protects uniqueness of POMsgSets in the POMsgSet
    # batch pouring callback.
    logger.info("Indexing POMsgSet holding table: (potmsgset, pofile)")
    cur.execute(
        "CREATE UNIQUE INDEX pomsgset_holding_potmsgset_pofile "
        "ON %s (potmsgset, pofile)" % holding_tables['pomsgset'])

    # Set potmsgset to point to equivalent POTMsgSet in copy's POFile.  This
    # is similar to what MultiTableCopy would have done for us had we included
    # POTMsgSet in the copy operation.
    logger.info("Redirecting potmsgset")
    cur.execute("""
        UPDATE %(pomsgset_holding_table)s AS holding
        SET potmsgset = temp_equiv_potmsgset.new_id
        FROM temp_equiv_potmsgset
        WHERE holding.potmsgset = temp_equiv_potmsgset.id
        """ % query_parameters)

    # Map new_ids in holding to those of child distroseries' corresponding
    # POMsgSets.
    logger.info("Re-keying inert POMsgSets")
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
    logger.info("Noting inert POMsgSets")
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
    logger.info("Indexing inert POMsgSets")
    cur.execute(
        "CREATE UNIQUE INDEX inert_pomsgset_idx "
        "ON temp_inert_pomsgsets(id)")
    logger.info("Indexing inert POMsgSets: new_id")
    cur.execute(
        "CREATE UNIQUE INDEX inert_pomsgset_newid_idx "
        "ON temp_inert_pomsgsets(new_id)")
    cur.execute("ANALYZE temp_inert_pomsgsets")


class PreparePOSubmissionPouring:
    """Prevent pouring of `POSubmission`s without `POMsgSet`s."""

    def __init__(self, lowest_pomsgset, highest_pomsgset):
        self.lowest_pomsgset = quote(lowest_pomsgset)
        self.highest_pomsgset = quote(highest_pomsgset)

    def __call__(self, holding_table, source_table):
        """See `ITunableLoop`."""
        # POMsgSet has already been poured.  Delete from POSubmission
        # holding table any rows referring to nonexistent POMsgSets.
        cur = cursor()
        drop_tables(cur, ['temp_final_pomsgsets'])
        allow_sequential_scans(cur, True)
        cur.execute("""
            CREATE TEMP TABLE temp_final_pomsgsets
            ON COMMIT DROP
            AS SELECT id FROM POMsgSet
            WHERE id >= %s AND id <= %s
            ORDER BY id
            """ % (self.lowest_pomsgset, self.highest_pomsgset))
        cur.execute("""
            CREATE UNIQUE INDEX temp_final_pomsgsets_idx
            ON temp_final_pomsgsets(id)
            """)
        cur.execute("ANALYZE %s" % holding_table)
        cur.execute("ANALYZE temp_final_pomsgsets")
        cur.execute("""
            DELETE FROM %s
            WHERE pomsgset NOT IN (SELECT id FROM temp_final_pomsgsets)
            """ % holding_table)
        allow_sequential_scans(cur, False)


class PreparePOSubmissionBatch:
    """Perform regular in-transaction cleanups before pouring a batch."""

    lowest_id = None
    highest_id = None

    def __call__(
        self, holding_table, source_table, batch_size, start_id, end_id):
        """Prepare pouring of a batch of `POSubmission`s.  See `ITunableLoop`.

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
        cur = cursor()

        # If we've covered about 20% of the total id range, ANALYZE the
        # holding table to prevent the server from falling back on slower or
        # badly-chosen algorithms.
        recently_covered = start_id - self.lowest_id
        if recently_covered > (self.highest_id - self.lowest_id) / 5:
            cur.execute("ANALYZE %s" % holding_table)
            self.lowest_id = start_id

        batch_clause = (
            "holding.id >= %s AND holding.id < %s"
            % sqlvalues(start_id, end_id))

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


def _prepare_posubmission_merge(copier, transaction, holding_tables, logger):
    """`POSubmission` chapter of `copy_active_translations_as_update`.

    Extract `POSubmission`s to be copied into holding table, and go through
    preparations for pouring them back.

    This function is not reusable; it only makes sense as a part of
    `copy_active_translations_as_update`.
    """
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

    cur = cursor()

    cur.execute(
        "SELECT min(new_id), max(new_id) FROM %s"
        % holding_tables['pomsgset'])
    lowest_pomsgset, highest_pomsgset = cur.fetchone()
    prepare_posubmission_pouring = PreparePOSubmissionPouring(
        lowest_pomsgset, highest_pomsgset)

    prepare_posubmission_batch = PreparePOSubmissionBatch()

    copier.extract(
        'POSubmission', joins=['POMsgSet'],
        where_clause="""
            active AND POSubmission.pomsgset = pms.id AND pms.iscomplete""",
        external_joins=['POMsgSet pms'],
        pre_pouring_callback=prepare_posubmission_pouring,
        batch_pouring_callback=prepare_posubmission_batch,
        inert_where=have_better)
    transaction.commit()
    transaction.begin()
    cur = cursor()

    cur.execute(
        "SELECT min(new_id), max(new_id) FROM %s"
        % holding_tables['posubmission'])
    lowest_posubmission, highest_posubmission = cur.fetchone()
    prepare_posubmission_batch.lowest_id = lowest_posubmission
    prepare_posubmission_batch.highest_id = highest_posubmission

    # Make sure we can do fast joins on (potranslation, pomsgset, pluralform)
    # to speed up the delete statement that protects uniqueness of active
    # submissions in the POSubmission batch pouring callback.
    logger.info("Indexing POSUbmission holding table: "
        "(potranslation, pomsgset, pluralform)")
    cur.execute(
        "CREATE UNIQUE INDEX posubmission_holding_triplet "
        "ON %s (potranslation, pomsgset, pluralform)"
        % holding_tables['posubmission'])


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


class UpdatePOMsgSetFlags:
    """Update flags on `POMsgSets` that may have been completed.

    Implemented using `LoopTuner`, this sets the iscomplete, isfuzzy, and
    isupdated flags appropriately.  This is done atop the object persistence
    layer, so should not be too arbitrarily mixed with SQL manipulation.
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

    This action modifies the `POFile` table and could run for some time.  The
    work is broken into brief chunks to avoid locking out other client
    processes.

    Uses the object persistence layer, so be careful when mixing with direct
    database access.
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


def _update_statistics_and_flags_post_merge(
    transaction, holding_tables, logger):
    """Final chapter of `copy_active_translations_as_update`.

    Patch up statistics and flags that don't need to be absolutely current all
    the time after pouring translations over from parent distroseries.

    This function is not reusable; it only makes sense as a part of
    `copy_active_translations_as_update`.
    """
    # Where corresponding POMsgSets already exist but are not complete, and
    # so may have been completed, update review-related status.
    logger.info("Updating review information")
    updater = UpdateReviewInfo(holding_tables['pomsgset'], transaction)
    LoopTuner(updater, 2, 500).run()

    # Update other POMsgSet flags.  This uses SQLObject, not raw SQL.
    logger.info("Updating status flags on POMsgSets")
    updater = UpdatePOMsgSetFlags(holding_tables['pomsgset'], transaction)
    LoopTuner(updater, 1).run()

    # Update the statistics cache for every POFile we touched.
    logging.info("Updating statistics on POFiles")
    LoopTuner(UpdatePOFileStats(transaction), 1).run()


def _copy_active_translations_as_update(child, transaction, logger):
    """Update child distroseries with translations from parent."""
    # This function makes extensive use of temporary tables.  Testing with
    # regular persistent tables revealed frequent lockups as the algorithm
    # waited for autovacuum to go over the holding tables.  Using temporary
    # tables means that we cannot let our connection be reset at the end of
    # every transaction.
    original_reset_setting = transaction.reset_after_transaction
    transaction.reset_after_transaction = False
    full_name = "%s_%s" % (child.distribution.name, child.name)
    tables = ['POFile', 'POMsgSet', 'POSubmission']
    copier = MultiTableCopy(
        full_name, tables, restartable=False, logger=logger)

    copier.dropHoldingTables()
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
            pt1.distroseries = %s AND
            pt2.distroseries = %s
        """ % sqlvalues(child.parent_series, child))
    cur.execute(
        "CREATE UNIQUE INDEX temp_equiv_template_pkey "
        "ON temp_equiv_template(id)")
    cur.execute(
        "CREATE UNIQUE INDEX temp_equiv_template_new_id "
        "ON temp_equiv_template(new_id)")
    cur.execute("ANALYZE temp_equiv_template")

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
    cur.execute("ANALYZE temp_equiv_potmsgset")
    transaction.commit()
    transaction.begin()

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

    # Prepare data from a series of translation-related tables to be merged
    # back into their original tables.  This is broken down into "chapters"
    # for the POFile, POMsgSet, and POSubmission tables (in that order) to
    # keep this function to a managable size.
    _prepare_pofile_merge(copier, transaction, query_parameters)
    transaction.commit()
    transaction.begin()

    _prepare_pomsgset_merge(
        copier, transaction, query_parameters, holding_tables, logger)
    transaction.commit()
    transaction.begin()

    _prepare_posubmission_merge(copier, transaction, holding_tables, logger)
    transaction.commit()
    transaction.begin()

    # Remember which POFiles we will affect, so we can update their stats
    # later.
    logger.info("Recording affected POFiles")
    cur.execute(
        "CREATE TEMP TABLE temp_changed_pofiles "
        "AS SELECT new_id AS id FROM %s" % holding_tables['pofile'])
    cur.execute(
        "CREATE UNIQUE INDEX temp_changed_pofiles_pkey "
        "ON temp_changed_pofiles(id)")
    cur.execute("ANALYZE temp_changed_pofiles")

    # Now get rid of those inert rows whose new_ids we messed with, or
    # horrible things will happen during pouring.
    logger.info("Filtering out inert POFiles")
    cur.execute("""
        DELETE FROM %(pofile_holding_table)s AS holding
        USING POFile
        WHERE holding.id = POFile.id""" % query_parameters)
    logger.info("Filtering out inert POMsgSets")
    cur.execute("""
        DELETE FROM %(pomsgset_holding_table)s AS holding
        USING POMsgSet
        WHERE holding.new_id = POMsgSet.id""" % query_parameters)
    transaction.commit()
    transaction.begin()
    cur = cursor()

    # We're about to pour.  If the database doesn't have current statistics,
    # it may botch the optimization.  So we try to make it refresh its
    # information.
    # This isn't something we're supposed to do in regular situations, and it
    # will block (possibly even deadlock) if a vacuum runs at the same time.
    # To minimize the pain, we try to analyze but move on if we can't acquire
    # the necessary locks.
    for holding_table in holding_tables.values():
        logger.info("Updating statistics on %s." % holding_table)
        try:
            cur.execute("LOCK TABLE %s IN SHARE UPDATE EXCLUSIVE MODE NOWAIT"
                % holding_table)
        except ProgrammingError, message:
            logger.info(message)
            transaction.abort()
        else:
            cur.execute("ANALYZE %s" % holding_table)
            transaction.commit()
        transaction.begin()
        cur = cursor()

    # Pour copied rows back to source tables.  Contrary to appearances, this
    # is where the heavy lifting is done.
    copier.pour(transaction)

    _update_statistics_and_flags_post_merge(
        transaction, holding_tables, logger)

    # Clean up after ourselves, in case we get called again this session.
    drop_tables(cursor(), [
        'temp_equiv_template', 'temp_equiv_potmsgset',
        'temp_inert_pomsgsets', 'temp_changed_pofiles'])

    flush_database_updates()
    transaction.commit()
    transaction.reset_after_transaction = original_reset_setting


def copy_active_translations(child_series, transaction, logger):
    """Copy active translations from the parent into this one.

    This function is used in two scenarios: when a new distribution series is
    opened for translation, and during periodic updates as new translations
    from the parent series are ported to newer series that haven't provided
    translations of their own for the same strings yet.  In the former
    scenario a full copy is drawn from the parent series.

    If the distroseries doesn't have any translatable resources, th function
    will clone all of the parent's current translatable resources; otherwise,
    only the translations that are in the parent but lacking in this one will
    be copied.

    If there is a status change but no translation is changed for a given
    message, we don't have a way to figure whether the change was originally
    made in the parent or the child distroseries, so we don't migrate that.
    """
    if child_series.parent_series is None:
        # We don't have a parent from where we could copy translations.
        return

    translation_tables = [
        'POTemplate', 'POTMsgSet', 'POMsgIDSighting', 'POFile',
        'POMsgSet', 'POSubmission'
        ]

    full_name = "%s_%s" % (child_series.distribution.name, child_series.name)
    copier = MultiTableCopy(full_name, translation_tables, logger=logger)

    if len(child_series.getCurrentTranslationTemplates()) == 0:
        # This is a new distroseries; copy from scratch
        _copy_active_translations_to_new_series(
            child_series, transaction, copier, logger)
    else:
        # Incremental copy of updates from parent distroseries
        _copy_active_translations_as_update(child_series, transaction, logger)

    # XXX: JeroenVermeulen 2007-07-16 bug=124410: Fix up
    # POFile.last_touched_pomsgset for POFiles that had POMsgSets and/or
    # POSubmissions copied in.


