# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the branch merge queue view classes and templates."""

from __future__ import with_statement

__metaclass__ = type

from canonical.launchpad.testing.pages import (
    extract_text,
    find_main_content,
    find_tags_by_class,
    )
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


class TestBranchMergeQueue(BrowserTestCase):
    """Test the Branch Merge Queue index page."""

    layer = DatabaseFunctionalLayer

    def test_index(self):
        """Test the index page of a branch merge queue."""
        with person_logged_in(ANONYMOUS):
            queue = self.factory.makeBranchMergeQueue()
            queue_url = canonical_url(queue)

        browser = self.getUserBrowser(canonical_url(queue), user=queue.owner)


        pattern = """\
            %(queue_name)s queue owned by %(owner_name)s

            %(owner_name)s Code

            Created by %(registrant_name)s .*

            Description
            %(queue_description)s

            The following branches are managed by this queue:""" % {
                'queue_name': queue.name,
                'owner_name': queue.owner.displayname,
                'registrant_name': queue.registrant.displayname,
                'queue_description': queue.description,
                }

        main_text = extract_text(find_main_content(browser.contents))
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)
