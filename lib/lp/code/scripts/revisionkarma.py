# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The actual script class to allocate revisions."""

__metaclass__ = type
__all__ = ['RevisionKarmaAllocator']

import transaction
from zope.component import getUtility

from lp.code.interfaces.revision import IRevisionSet
from lp.services.scripts.base import LaunchpadCronScript


class RevisionKarmaAllocator(LaunchpadCronScript):
    def main(self):
        """Allocate karma for revisions.

        Under normal circumstances, karma is allocated for revisions by the
        branch scanner as it is scanning the revisions.

        There are a number of circumstances where this doesn't happen:
          * The revision author is not linked to a Launchpad person
          * The branch is +junk

        When a branch is moved from +junk to a project we want to be able to
        allocate karma for the revisions that are now in the project.

        When a person validates an email address, a link is made with a
        `RevisionAuthor` if the revision author has that email address.  In
        this situation we want to allocate karma for the revisions that have
        the newly linked revision author as the and allocate karma for the
        person.
        """
        self.logger.info("Updating revision karma")

        count = 0
        revision_set = getUtility(IRevisionSet)
        # Break into bits.
        while True:
            revisions = list(
                revision_set.getRevisionsNeedingKarmaAllocated(100))
            if len(revisions) == 0:
                break
            for revision in revisions:
                # Find the appropriate branch, and allocate karma to it.
                # Make sure we don't grab a junk branch though, as we don't
                # allocate karma for junk branches.
                branch = revision.getBranch(
                    allow_private=True, allow_junk=False)
                karma = revision.allocateKarma(branch)
                if karma is None:
                    error_msg = (
                        'No karma generated for revid: %s (%s)' %
                        (revision.revision_id, revision.id))
                    self.logger.critical(error_msg)
                    # Stop now to avoid infinite loop.
                    raise AssertionError(error_msg)
                count += 1
            self.logger.debug("%s processed", count)
            transaction.commit()
        self.logger.info("Finished updating revision karma")
