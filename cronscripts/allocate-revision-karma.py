#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

import _pythonpath

import transaction

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.revision import IRevisionSet
from canonical.launchpad.scripts.base import LaunchpadCronScript


class RevisonKarmaAllocator(LaunchpadCronScript):
    def main(self):
        """Allocate karma for revisions.

        Under normal circumstances karma is allocated for revisions by the
        branch scanner as it is scanning the revisions.

        There are a number of circumstances where this doesn't happen though:
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

        # In order to only iterate over the revisions that we actually care
        # about, we are looking for the following:
        #   * karma not allocated
        #   * revision author linked to a Launchpad person
        #   * revision in a branch associated with a product

        revision_set = getUtility(IRevisionSet)
        for revision in revision_set.getRevisionsNeedingKarmaAllocated():
            # Find the appropriate branch, and allocate karma to it.
            branch = revision.getBranch(allow_private=True)
            revision.allocateKarma(branch)
            self.logger.debug(
                "Allocating karma for branch %s to %s" % (
                    branch.bzr_identity,
                    revision.revision_author.person.name))
        transaction.commit()
        self.logger.info("Finished updating revision karma")


if __name__ == '__main__':
    script = RevisonKarmaAllocator('allocate-revision-karma',
        dbuser=config.launchpad.dbuser)
    script.lock_and_run(implicit_begin=True)
