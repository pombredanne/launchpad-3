# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Functions to copy translations from parent to child distroseries."""

__metaclass__ = type

__all__ = [ 'copy_active_translations' ]

from psycopg import ProgrammingError
from zope.interface import implements

from canonical.database.multitablecopy import MultiTableCopy
from canonical.database.postgresql import allow_sequential_scans, drop_tables
from canonical.database.sqlbase import (
    cursor, flush_database_updates, quote, sqlvalues)
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.database.pofile import POFile
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

    # Copy POFiles, making them refer to the child's copied POTemplates.
    copier.extract('POFile', ['POTemplate'])

    # Same for TranslationMessage, but a bit more complicated since it refers
    # to both POFile and POTMsgSet.
    copier.extract(
        'TranslationMessage', ['POFile', 'POTMsgSet'],
        'is_current OR is_imported')

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


class PrepareTranslationMessagePouring:
    """Prevent pouring of `TranslationMessage` whose `POFile` weren't poured.

    This is a callback, but it takes the form of a class so it can carry some
    extra parameters.
    """
    def __init__(self, lowest_pofile, highest_pofile):
        """Accept parameters that help speed up actual cleanup work.

        :param lowest_pofile: lowest POFile id that we'll be copying
            `TranslationMessage`s for.
        :param highest_pofile: highest POFile id that we'll be copying
            `TranslationMessage`s for.
        """
        self.lowest_pofile = quote(lowest_pofile)
        self.highest_pofile = quote(highest_pofile)

    def __call__(self, holding_table, source_table):
        """See `ITunableLoop`."""
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
        drop_tables(cur, ['temp_final_pofiles'])
        allow_sequential_scans(cur, False)



def _prepare_translationmessage_batch(
    holding_table, source_table, batch_size, start_id, end_id):
    """Prepare pouring of a batch of `TranslationMessage`s.

    Deletes any `TranslationMessage`s in the batch that already have
    equivalents in the source table (same potmsgset and pofile, on which the
    source table has a unique index).  Any such `TranslationMessage`s must
    have been added after the `TranslationMessage`s were extracted, so we
    assume they are newer and better than what we have in our holding table.

    Also deletes `TranslationMessage`s in the batch that refer to `POFile`s
    that do not exist.  Any such `POFile`s must have been deleted from their
    holding table after they were extracted.
    """
    batch_clause = (
        "holding.id >= %s AND holding.id < %s" % sqlvalues(start_id, end_id))
    cur = cursor()
    cur.execute("""
        DELETE FROM %s AS holding
        USING TranslationMessage tm
        WHERE %s AND
            holding.potmsgset = tm.potmsgset AND
            holding.pofile = tm.pofile AND
            COALESCE(holding.msgstr0, -1) = COALESCE(tm.msgstr0, -1) AND
            COALESCE(holding.msgstr1, -1) = COALESCE(tm.msgstr1, -1) AND
            COALESCE(holding.msgstr2, -1) = COALESCE(tm.msgstr2, -1) AND
            COALESCE(holding.msgstr3, -1) = COALESCE(tm.msgstr3, -1)
        """ % (holding_table, batch_clause))

    # Deactivate translation messages we're about to replace with better ones
    # from the parent.
    cur.execute("""
        UPDATE TranslationMessage AS tm
        SET is_current = FALSE
        FROM %s holding
        WHERE %s AND
            holding.potmsgset = tm.potmsgset AND
            holding.pofile = tm.pofile AND
            tm.is_current IS TRUE
        """ % (holding_table, batch_clause))


def _prepare_translationmessage_merge(
    copier, transaction, query_parameters, holding_tables, logger):
    """`TranslationMessage` chapter of `copy_active_translations_as_update`.

    Extract copies of `TranslationMessage`s to be copied into holding table,
    and go through preparations for pouring them back.

    This function is not reusable; it only makes sense as a part of
    `copy_active_translations_as_update`.
    """
    # Exclude TranslationMessages for which one with an equivalent set of
    # translations already exists in the child series, or we'd be introducing
    # needless duplicates.
    # Don't offer replacements for messages that the child has newer ones for,
    # i.e. ones with the same (potmsgset, pofile) whose date_created is no
    # older than the one the parent has to offer.
    have_better = """
        EXISTS (
            SELECT *
            FROM TranslationMessage better
            JOIN temp_equiv_potmsgset ON
                holding.potmsgset = temp_equiv_potmsgset.id AND
                better.potmsgset = temp_equiv_potmsgset.new_id
            JOIN %(pofile_holding_table)s pfh ON
                holding.pofile = pfh.id AND
                better.pofile = pfh.new_id
            WHERE
                better.date_created >= holding.date_created OR
                ((COALESCE(better.msgstr0, -1) =
                    COALESCE(holding.msgstr0, -1)) AND
                (COALESCE(better.msgstr1, -1) =
                    COALESCE(holding.msgstr1, -1)) AND
                (COALESCE(better.msgstr2, -1) =
                    COALESCE(holding.msgstr2, -1)) AND
                (COALESCE(better.msgstr3, -1) =
                    COALESCE(holding.msgstr3, -1)))
        )
        """ % query_parameters

    cur = cursor()
    cur.execute(
        "SELECT min(new_id), max(new_id) FROM %s" % holding_tables['pofile'])
    lowest_pofile, highest_pofile = cur.fetchone()
    prepare_translationmessage_pouring = PrepareTranslationMessagePouring(
        lowest_pofile, highest_pofile)

    # We're only interested in current, complete translation messages.  See
    # TranslationMessage.is_complete for the definition of "complete."
    where_clause = """
        is_current AND
        pofile = POFile.id AND
        POFile.language = Language.id AND
        potmsgset = POTMsgSet.id AND
        msgstr0 IS NOT NULL AND
        (potmsgset.msgid_plural IS NULL OR (
         (msgstr1 IS NOT NULL OR COALESCE(Language.pluralforms,2) <= 1) AND
         (msgstr2 IS NOT NULL OR COALESCE(Language.pluralforms,2) <= 2) AND
         (msgstr3 IS NOT NULL OR COALESCE(Language.pluralforms,2) <= 3)))
        """
    copier.extract(
        'TranslationMessage', joins=['POFile'],
        where_clause=where_clause, inert_where=have_better,
        external_joins=['POTMsgSet', 'POFile', 'Language'],
        pre_pouring_callback=prepare_translationmessage_pouring,
        batch_pouring_callback=_prepare_translationmessage_batch)
    transaction.commit()
    transaction.begin()
    cur = cursor()

    # Set potmsgset to point to equivalent POTMsgSet in copy's POFile.  This
    # is similar to what MultiTableCopy would have done for us had we included
    # POTMsgSet in the copy operation.
    logger.info("Redirecting potmsgset")
    cur.execute("""
        UPDATE %(translationmessage_holding_table)s AS holding
        SET potmsgset = temp_equiv_potmsgset.new_id
        FROM temp_equiv_potmsgset
        WHERE holding.potmsgset = temp_equiv_potmsgset.id
        """ % query_parameters)

    # Map new_ids in holding to those of child distroseries' corresponding
    # TranslationMessages.
    logger.info("Re-keying inert TranslationMessages")
    cur.execute("""
        UPDATE %(translationmessage_holding_table)s AS holding
        SET new_id = tm.id
        FROM TranslationMessage tm
        WHERE
            holding.new_id IS NULL AND
            holding.potmsgset = tm.potmsgset AND
            holding.pofile = tm.pofile
        """ % query_parameters)


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
    tables = ['POFile', 'TranslationMessage']
    copier = MultiTableCopy(
        full_name, tables, restartable=False, logger=logger)

    copier.dropHoldingTables()
    drop_tables(cursor(), [
        'temp_equiv_template', 'temp_equiv_potmsgset', 'temp_changed_pofiles'])

    # Map parent POTemplates to corresponding POTemplates in child.  This will
    # come in handy later.
    cur = cursor()
    cur.execute("""
        CREATE TEMP TABLE temp_equiv_template AS
        SELECT DISTINCT pt1.id AS id, pt2.id AS new_id
        FROM POTemplate pt1, POTemplate pt2
        WHERE
            pt1.name = pt2.name AND
            pt1.translation_domain = pt2.translation_domain AND
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
            ptms1.msgid_singular = ptms2.msgid_singular AND
            (ptms1.msgid_plural = ptms2.msgid_plural OR
             (ptms1.msgid_plural IS NULL AND ptms2.msgid_plural IS NULL)) AND
            (ptms1.context = ptms2.context OR
             (ptms1.context IS NULL AND ptms2.context IS NULL))
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
        'translationmessage': copier.getHoldingTableName('TranslationMessage')
        }

    query_parameters = {
        'pofile_holding_table': holding_tables['pofile'],
        'translationmessage_holding_table':
            holding_tables['translationmessage'],
        }

    # Prepare data from a series of translation-related tables to be merged
    # back into their original tables.  This is broken down into "chapters"
    # for the POFile and TranslationMessage tables in order to keep this
    # function to a managable size.
    _prepare_pofile_merge(copier, transaction, query_parameters)
    transaction.commit()
    transaction.begin()

    _prepare_translationmessage_merge(
        copier, transaction, query_parameters, holding_tables, logger)
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
    logger.info("Filtering out inert TranslationMessages")
    cur.execute("""
        DELETE FROM %(translationmessage_holding_table)s AS holding
        USING TranslationMessage
        WHERE holding.new_id = TranslationMessage.id""" % query_parameters)
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

    # Update the statistics cache for every POFile we touched.
    logger.info("Updating statistics on POFiles")
    LoopTuner(UpdatePOFileStats(transaction), 1).run()

    # Clean up after ourselves, in case we get called again this session.
    drop_tables(cursor(), [
        'temp_equiv_template', 'temp_equiv_potmsgset', 'temp_changed_pofiles'])

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
        'POTemplate', 'POTMsgSet', 'POFile', 'TranslationMessage'
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

    # XXX: JeroenVermeulen 2007-07-16 bug=124410: Fix up date_changed and
    # lasttranslator for POFiles that had TranslationMessages copied in.

