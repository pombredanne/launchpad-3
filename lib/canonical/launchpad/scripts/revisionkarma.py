# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The actual script class to allocate revisions."""

__metaclass__ = type
__all__ = ['RevisionKarmaAllocator']

import transaction

from zope.component import getUtility

from canonical.launchpad.interfaces.revision import IRevisionSet
from canonical.launchpad.scripts.base import LaunchpadCronScript


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
        revisions = list(
            revision_set.getRevisionsNeedingKarmaAllocated()[:100])
        while len(revisions) > 0:
            for revision in revisions:
                # Find the appropriate branch, and allocate karma to it.
                # Make sure we don't grab a junk branch though, as we don't
                # allocate karma for junk branches.
                branch = revision.getBranch(
                    allow_private=True, allow_junk=False)
                revision.allocateKarma(branch)
                count += 1
            self.logger.debug("%s processed", count)
            transaction.commit()
            revisions = list(
                revision_set.getRevisionsNeedingKarmaAllocated()[:100])
        self.logger.info("Finished updating revision karma")
