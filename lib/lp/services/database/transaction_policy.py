# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Policy for database transactions."""

__metaclass__ = type
__all__ = [
    'DatabaseTransactionPolicy',
    ]

from psycopg2.extensions import TRANSACTION_STATUS_IDLE
import transaction
from zope.component import getUtility

from canonical.database.sqlbase import quote
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.services.database.isolation import TransactionInProgress


class DatabaseTransactionPolicy:
    """Context manager for read-only transaction policy.

    Use this to define regions of code that explicitly allow or disallow
    changes to the database:

        # We want to be sure that inspect_data does not inadvertently
        # make any changes in the database, but we can't run it on the
        # slave store because it doesn't tolerate replication lag.
        with DatabaseTransactionPolicy(read_only=True):
            inspect_data()

    The simplest way to use this is as a special transaction:
     * You must commit/abort before entering the policy.
     * Exiting the policy through an exception aborts its changes.
     * Before completing a read-write policy region, you must commit or abort.

    You can also have multiple transactions inside one policy, however; the
    policy still applies after a commit or abort.

    Policies can be nested--a nested policy overrides the one it's nested in.
    After the nested policy has exited, the previous policy applies again:

        # This code needs to control the database changes it makes very
        # carefully.  Most of it is just gathering data, with one quick
        # database update at the end.
        with DatabaseTransactionPolicy(read_only=True):
            data = gather_data()
            more_data = figure_stuff_out(data)

            # End the ongoing transaction so we can go into our update.
            transaction.commit()

            # This is the only part where we update the database!
            with DatabaseTransactionPolicy(read_only=False):
                update_model(data, more_data)
                transaction.commit()

            write_logs(data)
            notify_user(more_data)
    """

    db_switch = "DEFAULT_TRANSACTION_READ_ONLY"

    def __init__(self, store=None, read_only=False):
        """Create a policy.

        Merely creating a policy has no effect.  Use it with "with" to affect
        writability of database transactions.

        :param store: The store to set policy on.  Defaults to the main master
            store.  You don't want to use this on a slave store!
        :param read_only: Allow database changes for the duration of this
            policy?
        """
        self.policy = read_only
        if store is None:
            self.store = getUtility(IStoreSelector).get(
                MAIN_STORE, MASTER_FLAVOR)
        else:
            self.store = store

    def __enter__(self):
        """Enter this policy.

        Commits the ongoing transaction, and sets the selected default
        read-only policy on the database.

        :raise TransactionInProgress: if a transaction was already ongoing.
        """
        self._checkNoTransaction(
            "Entered DatabaseTransactionPolicy while in a transaction.")
        self.previous_policy = self._getCurrentPolicy()
        self._setPolicy(self.policy)
        # Commit should include the policy itself.  If this breaks
        # because the transaction was already in a failed state before
        # we got here, too bad.
        transaction.commit()

    def __exit__(self, exc_type, *args):
        """Exit this policy.

        Commits or aborts, depending on mode of exit, and restores the
        previous default read-only policy.

        :return: True -- any exception will continue to propagate.
        :raise TransactionInProgress: if trying to exit normally from a
            read-write policy without closing its transaction first.
        """
        leaving_with_exception = (exc_type is not None)
        if leaving_with_exception:
            transaction.abort()
        elif self.policy == True:
            transaction.commit()
        else:
            self._checkNoTransaction(
                "Failed to close transaction before leaving read-write "
                "DatabaseTransactionPolicy.")

        self._setPolicy(self.previous_policy)
        transaction.commit()

        # Continue processing the exception as normal.
        return False

    def _checkNoTransaction(self, error_msg):
        """Verify that no transaction is ongoing.

        :param error_msg: The error message to use if the user got this wrong
            (i.e. if we're in a transaction).
        :raise TransactionInProgress: if we're in a transaction.
        """
        pg_connection = self.store._connection._raw_connection
        if pg_connection.get_transaction_status() != TRANSACTION_STATUS_IDLE:
            raise TransactionInProgress(error_msg)

    def _getCurrentPolicy(self):
        """Read the database session's default transaction read-only policy.

        The information is retrieved from the database, so this will give a
        sensible answer even when no DatabaseTransactionPolicy is in effect.

        :return: True for read-only policy, False for read-write policy.
        """
        db_switch_value_to_policy = {
            'on': True,
            'off': False,
        }
        show_command = "SHOW %s" % self.db_switch
        db_switch_value, = self.store.execute(show_command).get_one()
        return db_switch_value_to_policy[db_switch_value]

    def _setPolicy(self, read_only=True):
        """Set the database session's default transaction read-only policy.

        :param read_only: True for read-only policy, False for read-write
            policy.
        """
        self.store.execute(
            "SET %s TO %s" % (self.db_switch, quote(read_only)))
