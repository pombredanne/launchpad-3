# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing helpers for buildmaster code."""

__metaclass__ = type
__all__ = [
    "BuilddManagerDatabasePolicyFixture",
    ]

import fixtures
import transaction

from lp.services.database.transaction_policy import DatabaseTransactionPolicy


class BuilddManagerDatabasePolicyFixture(fixtures.Fixture):
    """Mimics the default transaction access policy of `BuilddManager`.

    See `BuilddManager.enterReadOnlyDatabasePolicy`.
    """

    def __init__(self, store=None, read_only=False):
        super(BuilddManagerDatabasePolicyFixture, self).__init__()
        self.policy = DatabaseTransactionPolicy(
            store=store, read_only=read_only)

    def setUp(self):
        # Commit everything done so far then apply  shift into a read-only
        # transaction access mode by default.
        transaction.commit()
        self.policy.__enter__()
        self.addCleanup(self.policy.__exit__, None, None, None)
