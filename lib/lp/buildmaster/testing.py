# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing helpers for buildmaster code."""

__metaclass__ = type
__all__ = [
    "BuilddManagerTestFixture",
    ]

from contextlib import contextmanager
from functools import wraps

import fixtures
import transaction

from lp.services.database.transaction_policy import DatabaseTransactionPolicy


class BuilddManagerTestFixture(fixtures.Fixture):
    """Helps provide an environment more like `BuilddManager` provides.

    This mimics the default transaction access policy of `BuilddManager`,
    though it can be configured with a different policy by passing in `store`
    and/or `read_only`. See `BuilddManager.enterReadOnlyDatabasePolicy`.

    Because this will shift into a read-only database transaction access mode,
    individual tests that need to do more setup can use the `extraSetUp()`
    context manager to temporarily shift back to a read-write mode.
    """

    def __init__(self, store=None, read_only=True):
        super(BuilddManagerTestFixture, self).__init__()
        self.policy = DatabaseTransactionPolicy(
            store=store, read_only=read_only)

    def setUp(self):
        # Commit everything done so far then shift into a read-only
        # transaction access mode by default.
        super(BuilddManagerTestFixture, self).setUp()
        transaction.commit()
        self.policy.__enter__()
        self.addCleanup(self.policy.__exit__, None, None, None)

    @staticmethod
    def extraSetUp(func=None):
        """Temporarily enter a read-write transaction to do extra setup.

        For example:

          with BuilddManagerTestFixture.extraSetUp():
              removeSecurityProxy(self.build).date_finished = None

        On exit it will commit the changes and restore the previous
        transaction access mode.

        Alternatively it can be used as a decorator:

          @BuilddManagerTestFixture.extraSetUp
          def makeSomethingOrOther(self):
              return ...

        Like with the context manager, on return it will commit the changes
        and restore the previous transaction access mode.
        """
        if func is None:
            @contextmanager
            def context():
                with DatabaseTransactionPolicy(read_only=False):
                    yield
                    transaction.commit()
            return context()
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with DatabaseTransactionPolicy(read_only=False):
                    result = func(*args, **kwargs)
                    transaction.commit()
                    return result
            return wrapper
