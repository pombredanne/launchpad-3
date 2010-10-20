# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the branch merge queue view classes and templates."""

from __future__ import with_statement

__metaclass__ = type

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    person_logged_in,
    )


class TestBranchMergeQueueIndex(BrowserTestCase):
    """Test the Branch Merge Queue index page."""

    layer = DatabaseFunctionalLayer

    def test_index(self):
        """Test the index page of a branch merge queue."""
        with person_logged_in(ANONYMOUS):
            queue = self.factory.makeBranchMergeQueue()
            queue_url = canonical_url(queue)

        browser = self.getUserBrowser(canonical_url(queue), user=queue.owner)
