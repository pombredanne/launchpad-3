# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the branch merge queue view classes and templates."""

from __future__ import with_statement

__metaclass__ = type

from mechanize import LinkNotFoundError

from canonical.launchpad.testing.pages import (
    extract_text,
    find_main_content,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
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
            queue_owner = queue.owner.displayname
            queue_registrant = queue.registrant.displayname
            queue_description = queue.description
            queue_url = canonical_url(queue)

            branch = self.factory.makeBranch()
            branch_name = branch.bzr_identity
            with person_logged_in(branch.owner):
                branch.addToQueue(queue)

        browser = self.getUserBrowser(canonical_url(queue), user=queue.owner)


        pattern = """\
            %(queue_name)s queue owned by %(owner_name)s

            %(owner_name)s Code

            Created by %(registrant_name)s .*

            Description
            %(queue_description)s

            The following branches are managed by this queue:
            %(branch_name)s""" % {
                'queue_name': queue.name,
                'owner_name': queue_owner,
                'registrant_name': queue_registrant,
                'queue_description': queue_description,
                'branch_name': branch_name,
                }

        main_text = extract_text(find_main_content(browser.contents))
        self.assertTextMatchesExpressionIgnoreWhitespace(
            pattern, main_text)

    def test_create(self):
        """Test that branch merge queues can be created from a branch."""
        with person_logged_in(ANONYMOUS):
            rockstar = self.factory.makePerson(name='rockstar')
            branch = self.factory.makeBranch(owner=rockstar)
            self.factory.makeBranch(product=branch.product)
            owner_name = branch.owner.name

        browser = self.getUserBrowser(canonical_url(branch), user=rockstar)
        browser.getLink('Create a new queue').click()

        browser.getControl('Name').value = 'libbob-queue'
        browser.getControl('Description').value = (
            'This is a queue for the libbob projects.')
        browser.getControl('Create Queue').click()

        self.assertEqual(
            'http://code.launchpad.dev/~rockstar/+merge-queues/libbob-queue',
            browser.url)

    def test_create_unauthorized(self):
        """Test that queues can't be created by unauthorized users."""
        with person_logged_in(ANONYMOUS):
            branch = self.factory.makeBranch()
            self.factory.makeBranch(product=branch.product)

        browser = self.getUserBrowser(canonical_url(branch))
        self.assertRaises(
            LinkNotFoundError,
            browser.getLink,
            'Create a new queue')
