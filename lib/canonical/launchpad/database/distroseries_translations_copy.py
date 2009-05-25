# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Functions to copy translations from parent to child distroseries."""

__metaclass__ = type

__all__ = [ 'copy_active_translations' ]

from psycopg2 import DatabaseError
from zope.interface import implements

from canonical.database.multitablecopy import MultiTableCopy
from canonical.database.postgresql import allow_sequential_scans, drop_tables
from canonical.database.sqlbase import (
    cursor, flush_database_updates, quote, sqlvalues)
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.translationmessage import (
    make_plurals_sql_fragment)
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
    parent = child.parent_series
    logger.info(
        "Populating blank distroseries %s with translations from %s." %
        sqlvalues(child, parent))

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

    # Clean up any remains from a previous run.  If we got here, that means
    # that any such remains are unsalvagable.
    copier.dropHoldingTables()

    # Copy relevant POTemplates from existing series into a holding table,
    # complete with their original id fields.
    where = 'distroseries = %s AND iscurrent' % quote(parent)
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


    # Copy each TranslationTemplateItem whose template we copied, and let MultiTableCopy
    # replace each potemplate reference with a reference to our copy of the
    # original POTMsgSet's potemplate.
    copier.extract('TranslationTemplateItem', ['POTemplate'], 'sequence > 0')

    # Copy POFiles, making them refer to the child's copied POTemplates.
    copier.extract('POFile', ['POTemplate'])

    # Same for POFileTranslator
    copier.extract('POFileTranslator', ['POFile'])

    # Finally, pour the holding tables back into the originals.
    copier.pour(transaction)


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
        'POTemplate', 'TranslationTemplateItem', 'POFile', 'POFileTranslator'
        ]

    full_name = "%s_%s" % (child_series.distribution.name, child_series.name)
    copier = MultiTableCopy(full_name, translation_tables, logger=logger)

    # Incremental copy of updates is no longer supported
    assert len(child_series.getTranslationTemplates()) == 0, (
           "The child series must not yet have any translation templates.")

    _copy_active_translations_to_new_series(
        child_series, transaction, copier, logger)

    # XXX: JeroenVermeulen 2007-07-16 bug=124410: Fix up date_changed and
    # lasttranslator for POFiles that had TranslationMessages copied in.

