# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [ 'MultiTableCopy' ]

import time

from canonical.database import postgresql
from canonical.database.sqlbase import (cursor, quoteIdentifier)


class MultiTableCopy:
    """Copy interlinked data spanning multiple tables in a coherent fashion.

    This allows data from a combination of tables, possibly with foreign-key
    references between them, to be copied to a set of corresponding "holding
    tables;" processed and modified there; and then be inserted back to the
    original tables.  The holding tables are created on demand and dropped
    upon completion.

    You can tell the algorithm to redirect foreign keys.  Say you're copying a
    row x1 in a table X, and x1 has a foreign key referring to a row y1 in a
    table Y that you're also copying.  You will get copied rows x2 and y2
    respectively.  But if you declare the foreign-key relationship between X
    and Y to the algorithm, then x2's instance of that foreign key will refer
    not to y1 but to the new y2.  Any rows in X whose associated rows of Y are
    not copied, are also not copied.  This can be useful when copying data in
    entire sub-trees of the schema graph, e.g. "one distrorelease and all the
    translations associated with it."

    All this happens in a two-stage process:

    1. Extraction stage.  Use the extractToHoldingTable method to copy
    selected data to a holding table, one table at a time.  Ordering matters:
    always do this in such an order that the table you are extracting has no
    foreign-key references to another table that you are yet to extract.

    This stage is relatively fast and holds no locks on the database.  Do any
    additional processing on the copied rows in the holding tables, during or
    after the extraction stage, so you do not hold any locks on the source
    tables yourself.  It's up to you to make sure that all of the rows in the
    holding tables can be inserted into their source tables: if you leave
    primary keys and such unchanged, unique constraints will be violated in
    the next stage.

    2. Pouring stage.  All data from the holding tables is inserted back into
    the source tables.  This entire stage, which normally takes the bulk of
    the copying time, is performed by calling the pourHoldingTables method.

    This stage will lock the rows that are being inserted in the source
    tables, if the database is so inclined (e.g. when using postgres with
    SERIALIZABLE isolation level).  For that reason, the pouring is done in
    smaller, controlled batches.  If you give the object a database
    transaction to work with, that transaction will be committed and restarted
    between batches.

    A MultiTableCopy is restartable.  If the process should fail for any
    reason, the holding tables will be left in one of two states: if stage 1
    has not completed, hasRecoverableData will return False.  In that case,
    drop the holding tables using dropHoldingTables and either start again (or
    give up).  But if a previous run did complete the extraction stage, the
    holding tables will remain and contain valid data.  In that case, run
    pourHoldingTables again to continue the work (and hopefully complete it
    this time).

    Holding tables will have names like "temp_POMsgSet_holding_ubuntu_feisty",
    in this case for one holding data extracted from source table POMsgSet by
    a MultiTableCopy called "ubuntu_feisty".

    The tables to be copied must meet a number of conventions:

     * First column must be an integer primary key called "id."

     * id values must be assigned by a sequence, with a name that can be used
       in SQL without quoting.

     * Every foreign-key column that refers to a table that is also being
       copied, must have the same name as the table it refers to.

     * Foreign-key column names and the tables they refer to can be used in
       SQL without quoting.

     * For any foreign key column "x" referring to another table that is also
       being copied, there must not be a column called "new_x"
    """
    # XXX: JeroenVermeulen 2007-05-24, More quoting, fewer assumptions!

    def __init__(self, name, tables, logger=None, time_goal=4):
        """Define a MultiTableCopy, including an in-order list of tables.

        The name parameter is a unique identifier for this MultiTableCopy
        operation, e.g. "ubuntu_feisty".  The name will be included in the
        names of holding tables.

        You must provide a list of tables that will be extracted and poured,
        in the order in which they will be extracted (and later, poured).
        This is essential when analyzing recoverable state.  You may perform
        multiple extractions from the same table, but all tables listed must
        be extracted.  If you do not wish to copy any rows from a source
        table, extract with "false" in its where clause.

        Pass a time goal (in seconds) to define how long, ideally, the
        algorithm should be allowed to hold locks on the source tables.
        """
        self.name = name
        self.tables = tables
        self.logger = logger
        self.time_goal = time_goal
        self.last_extracted_table = None

    def dropHoldingTables(self):
        """Drop any holding tables that may exist for this MultiTableCopy."""
        postgresql.drop_tables(cursor(),
            [self.getHoldingTableName(t) for t in self.tables])

    def getRawHoldingTableName(self, tablename, suffix=''):
        """Name for a holding table, but without quotes.  Use with care."""
        if suffix:
            suffix = '_%s' % suffix
        return "temp_%s_holding_%s%s" % (
            str(tablename), str(self.name), suffix)

    def getHoldingTableName(self, tablename, suffix=''):
        """Name for a holding table to hold data being copied in tablename.

        Return value is properly quoted for use as an SQL identifier.
        """
        return str(
            quoteIdentifier(self.getRawHoldingTableName(tablename, suffix)))


    def extractToHoldingTable(self,
            source_table,
            joins=None,
            where_clause=None,
            id_sequence=None):
        """Extract (selected) rows from source_table into a holding table.

        The holding table gets an additional new_id column with identifiers in
        the seqid sequence; the name seqid defaults to the original table name
        in lower case, with "_seq_id" appended.  Apart from this extra column,
        indexes, and constraints, the holding table is schematically identical
        to source_table.  A unique index is created for the original id
        column.

        There is a special facility for redirecting foreign keys to other
        tables copied in the same way.  If the joins argument is a nonempty
        list, the selection used in creating the new table  will be joined
        with each of the tables named in joins, on foreign keys in the current
        table.  The foreign keys in the holding table will point to the
        new_ids of the copied rows, rather than the original ids.  Rows in
        source_table will only be copied to their holding table if all rows
        they are joined with in those other tables were also copied to holding
        tables of their own.

        The foreign keys are assumed to have the same names as the tables
        they refer to, but written in lower-case letters.

        When joining, the added tables' columns are not included in the
        holding table, but where_clause may select on them.

        The id_sequence argument gives the name of the database sequence that
        assigns values for the id column.  It must be a simple identifier (no
        quoting required) and it defaults to the name of the source table,
        converted to all lower-case, with "_id_seq" appended.
        """
        if id_sequence is None:
            id_sequence = "%s_id_seq" % source_table.lower()

        if joins is None:
            joins = []

        self._checkExtractionOrder(source_table)

        holding_table = self.getHoldingTableName(source_table)

        self._log_info('Extracting from %s into %s...' % (
            source_table,holding_table))

        starttime = time.time()

        # Selection clauses for our foreign keys
        new_fks = [
            "%s.new_id AS new_%s" % (self.getHoldingTableName(j), j.lower())
            for j in joins
        ]

        # Combined "where" clauses
        where = [
            "%s = %s.id" % (j.lower(), self.getHoldingTableName(j))
            for j in joins
        ]
        if where_clause is not None:
            where.append('(%s)' % where_clause)

        cur = cursor()

        # We use a regular, persistent table rather than a temp table for
        # this so that we get a chance to resume interrupted copies, and
        # analyse failures.  If we used temp tables, they'd be gone by the
        # time we knew something went wrong.
        # For each row we append at the end any new foreign key values, and
        # finally a "new_id" holding its future id field.  This new_id value
        # is allocated from the original table's id sequence, so it will be
        # unique in the original table.
        fk_list = ', '.join(['%s.*' % source_table] + new_fks)
        from_list = ', '.join([source_table] +
                              ['%s' % self.getHoldingTableName(j)
                               for j in joins])

        where_list = ''
        if len(where) > 0:
            where_list = 'WHERE %s' % ' AND '.join(where)

        cur.execute('''
            CREATE TABLE %s AS
            SELECT %s, nextval('%s'::regclass) AS new_id
            FROM %s
            %s''' % (holding_table,
                      fk_list,
                      id_sequence,
                      from_list,
                      where_list))

        if len(joins) > 0:
            # Replace foreign keys with their "new_" variants, then drop those
            # "new_" columns we added.
            fkupdates = [
                "%s = new_%s" % (j.lower(),j.lower()) for j in joins
            ]
            updatestr = ', '.join(fkupdates)
            self._log_info("Redirecting foreign keys: %s" % updatestr)
            cur.execute('''
                UPDATE %s
                SET %s
            ''' % (holding_table, updatestr))
            for j in joins:
                column = j.lower()
                self._log_info("Dropping foreign-key column %s" % column)
                cur.execute('''
                    ALTER TABLE %s DROP COLUMN new_%s''' % (holding_table,
                                                            column))

        # Now that our new holding table is in a stable state, index its id
        self._log_info("Indexing %s" % holding_table)
        cur.execute('''
            CREATE UNIQUE INDEX %s
            ON %s (id)
        ''' % (self.getHoldingTableName(source_table, 'id'), holding_table))
        self._log_info('...Extracted in %.3f seconds' %
            (time.time()-starttime))


    def hasRecoverableHoldingTables(self):
        """Do we have holding tables with recoverable data from previous run?

        Returns Boolean answer.
        """

        cur = cursor()

        # If there are any holding tables to be poured into their source
        # tables, there must at least be one for the last table that
        # pourHoldingTables() processes.
        if not postgresql.have_table(cur,
                self.getRawHoldingTableName(self.tables[-1])):
            return False

        # If the first table in our list also still exists, and it still has
        # its new_id column, then the pouring process had not begun yet.
        # Assume the data was not ready for pouring.
        if postgresql.table_has_column(cur,
                self.getRawHoldingTableName(self.tables[0]),
                'new_id'):
            self._log_info(
                "Previous run aborted too early for recovery; redo all")
            return False

        self._log_info("Recoverable data found")
        return True


    def pourHoldingTables(self, ztm=None):
        """Pour data from holding tables back into source tables.

        The transaction ztm, if any, is committed and re-opened after every
        batch run.

        Batch sizes are dynamically adjusted to meet the stated time goal.
        """

        if self.last_extracted_table is not None and (
                self.last_extracted_table != len(self.tables)-1):
            raise AssertionError(
                "Not safe to pour: last table '%s' was not extracted" %
                    self.tables[-1])

        cur = self._commit(ztm)

        # Main loop: for each of the source tables involved in copying
        # translations from our parent distrorelease, see if there's a
        # matching holding table; prepare it, pour it back into the source
        # table, and drop.
        for table in self.tables:
            holding_table = self.getHoldingTableName(table)
            holding_table_unquoted = self.getRawHoldingTableName(table)

            if not postgresql.have_table(cur, holding_table_unquoted):
                # We know we're in a suitable state for pouring.  If this
                # table does not exist, it must be because it's been poured
                # out completely and dropped in an earlier instance of this
                # loop, before the failure we're apparently recovering from.
                continue

            # XXX: JeroenVermeulen 2007-05-02, Lock holding table maybe, to
            # protect against accidental concurrent runs?  Insouciant as it
            # may seem not to do that, all but one run would fail anyway
            # because of the unique index on id.  But a lock would give us a
            # more helpful error message.
            self._log_info("Pouring %s back into %s..." %
                (holding_table, table))

            tablestarttime = time.time()

            if postgresql.table_has_column(cur, holding_table_unquoted,
                                           'new_id'):
                # Update ids in holding table from originals to copies.
                # (If this is where we got interrupted by a failure in a
                # previous run, no harm in doing it again)
                cur.execute("UPDATE %s SET id=new_id" % holding_table)
                # Restore table to original schema
                cur.execute("ALTER TABLE %s DROP COLUMN new_id" %
                    holding_table)
                self._log_info("...rearranged ids in %.3f seconds..." %
                    (time.time()-tablestarttime))

            # Now pour holding table's data into its source table.  This is
            # where we start writing to tables that other clients will be
            # reading, so row locks are a concern.  Break the writes up in
            # batches of a few thousand rows.  The goal is to have these
            # transactions running no longer than five seconds or so each.

            postgresql.allow_sequential_scans(cur, False)

            # We batch simply by breaking the range of ids in our table down
            # into fixed-size intervals.  Some of those fixed-size intervals
            # may not have any rows in them, or very few.  That's not likely
            # to be a problem though since we allocated all these ids in one
            # single SQL statement.  No time for gaps to form.
            cur.execute("SELECT min(id), max(id) FROM %s" % holding_table)
            lowest_id, highest_id = cur.fetchall()[0]

            if lowest_id is None:
                # Table is empty.  Drop it and move on.
                postgresql.drop_tables(cur, holding_table)
                continue

            total_rows = highest_id + 1 - lowest_id
            self._log_info("Up to %d rows in holding table" % total_rows)

            cur = self._commit(ztm, cur)

            # Minimum batch size.  We never process fewer rows than this in
            # one batch because at that level, we expect to be running into
            # more or less constant transaction costs.  Reducing batch size
            # any further is not likely to help much, but will make the
            # overall procedure take much longer.
            min_batch_size = 1000

            batch_size = min_batch_size
            while lowest_id <= highest_id:
                # Step through ids backwards.  This appears to be faster,
                # possibly because we're removing records from the end of the
                # table instead of from the beginning, or perhaps it makes
                # rebalancing the index a bit easier.
                next = highest_id - batch_size
                self._log_info("Moving %d ids: %d-%d..." % (
                    highest_id - next, next, highest_id))
                batchstarttime = time.time()

                cur.execute('''
                    INSERT INTO %s (
                        SELECT *
                        FROM %s
                        WHERE id >= %d
                    )''' % (table, holding_table, next))
                cur.execute('''
                    DELETE FROM %s
                    WHERE id >= %d
                ''' % (holding_table, next))

                cur = self._commit(ztm, cur)

                highest_id = next

                time_taken = time.time() - batchstarttime
                self._log_info("...batch done in %.3f seconds (%d%%)." % (
                    time_taken,
                    100*(total_rows + lowest_id - highest_id)/total_rows))


                # Adjust batch_size to approximate time_goal.  The new
                # batch_size is the average of two values: the previous value
                # for batch_size, and an estimate of how many rows would take
                # us to exactly time_goal seconds.  The estimate is very
                # simple: rows per second on the last commit.
                # The weight in this estimate of any given historic datum
                # decays exponentially with an exponent of 1/2.  This softens
                # the blows from spikes and dips in processing time.
                # Set a reasonable minimum for time_taken, just in case we get
                # weird values for whatever reason and destabilize the
                # algorithm.
                time_taken = max(self.time_goal/10, time_taken)
                batch_size = batch_size*(1 + self.time_goal/time_taken)/2
                batch_size = max(batch_size, min_batch_size)

            cur = self._commit(ztm, cur)

            self._log_info(
                "Pouring %s took %.3f seconds." %
                    (holding_table, time.time()-tablestarttime))

            postgresql.drop_tables(cur, holding_table)

    def _checkExtractionOrder(self, source_table):
        """Verify order in which tables are extracted against tables list.

        Check that the caller follows the stated plan, extracting from tables
        in the same order as in self.tables.
        """
        try:
            table_number = self.tables.index(source_table)
        except ValueError:
            raise AssertionError(
                "Can't extract '%s': not in list of tables" % source_table)

        if self.last_extracted_table is None:
            # Can't skip the first table!
            if table_number > 0:
                raise AssertionError(
                    "Can't extract: skipped first table '%s'" %
                        self.tables[0])
        else:
            if table_number < self.last_extracted_table:
                raise AssertionError(
                    "Table '%s' extracted after its turn" % source_table)
            if table_number > self.last_extracted_table+1:
                raise AssertionError(
                    "Table '%s' extracted before its turn" % source_table)
            if table_number == self.last_extracted_table:
                raise AssertionError(
                    "Table '%s' extracted again" % source_table)

        self.last_extracted_table = table_number


    def _commit(self, ztm, cur=None):
        """If we have a transaction, commit it and offer replacement cursor.

        Use this as "cur = self._commit(cur)" to commit a transaction, restart
        it, and replace cur with a cursor that lives within the new
        transaction.
        """
        if ztm is None:
            return cur or cursor()

        start = time.time()
        ztm.commit()
        self._log_info("Committed in %.3f seconds" % (time.time()-start))
        ztm.begin()
        return cursor()

    def _log_info(self, message):
        """Write an info-level message to our logger, if we have one."""
        if self.logger is not None:
            self.logger.info(message)

