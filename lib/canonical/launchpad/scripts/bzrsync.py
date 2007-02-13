#!/usr/bin/python
# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Import version control metadata from a Bazaar branch into the database."""

__metaclass__ = type

__all__ = [
    "BzrSync",
    ]

import sys
import os
import logging
from datetime import datetime, timedelta
from StringIO import StringIO

import pytz
from zope.component import getUtility
from bzrlib.branch import Branch
from bzrlib.diff import show_diff_trees
from bzrlib.errors import NoSuchRevision
from bzrlib.log import log_formatter, show_log
from bzrlib.revision import NULL_REVISION

from sqlobject import AND
from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel)
from canonical.launchpad.helpers import (
    contactEmailAddresses, get_email_template)
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IBranchSet, IRevisionSet)
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.webapp import canonical_url

UTC = pytz.timezone('UTC')


class RevisionModifiedError(Exception):
    """An error indicating that a revision has been modified."""
    pass


class BzrSync:
    """Import version control metadata from Bazaar2 branches into the database.

    If the contructor succeeds, a read-lock for the underlying bzrlib branch is
    held, and must be released by calling the `close` method.
    """
    def __init__(self, trans_manager, branch, branch_url=None, logger=None):
        self.trans_manager = trans_manager
        self._admin = getUtility(ILaunchpadCelebrities).admin
        self.email_from = config.noreply_from_address
        
        if logger is None:
            logger = logging.getLogger(self.__class__.__name__)
        self.logger = logger
        
        self.db_branch = branch
        self.db_revision_history = getUtility(
            IRevisionSet).getRevisionHistoryForBranch(branch)
        
        if branch_url is None:
            branch_url = self.db_branch.url
        self.bzr_branch = Branch.open(branch_url)
        self.bzr_branch.lock_read()
        self.curr = 0
        self.last = 0
        try:
            self.bzr_history = self.bzr_branch.revision_history()
        except:
            self.bzr_branch.unlock()
            raise

    def close(self):
        """Explicitly release resources."""
        # release the read lock on the bzrlib branch
        self.bzr_branch.unlock()
        # prevent further use of that object
        self.bzr_branch = None
        self.db_branch = None
        self.bzr_history = None

    def syncHistoryAndClose(self):
        """Import all revisions in the branch and release resources.

        Convenience method that implements the proper try/finally idiom for the
        common case of calling `syncHistory` and immediately `close`.
        """
        try:
            self.syncHistory()
        finally:
            self.close()

    def syncHistory(self):
        """Import all revisions in the branch."""
        # Keep track if something was actually loaded in the database.
        did_something = False

        self.logger.info(
            "synchronizing ancestry for branch: %s", self.bzr_branch.base)

        # synchronise Revision objects
        ancestry = self.bzr_branch.repository.get_ancestry(
            self.bzr_branch.last_revision())
        self.curr = 0
        self.last = len(ancestry)
        for revision_id in ancestry:
            self.curr += 1
            if revision_id is None:
                self.logger.debug("%d of %d: revision_id is None",
                                  self.curr, self.last)
                continue
            # If the revision is a ghost, it won't appear in the repository.
            try:
                revision = self.bzr_branch.repository.get_revision(revision_id)
            except NoSuchRevision:
                self.logger.debug("%d of %d: %s is a ghost",
                                  self.curr, self.last, revision_id)
                continue
            if self.syncRevision(revision):
                did_something = True

        # now synchronise the RevisionNumber objects
        if self.syncRevisionNumbers():
            did_something = True

        # If we have got to here, email out the revision updates.
        self.sendRevisionNotificationEmails()

        return did_something

    def syncRevision(self, bzr_revision):
        """Import the revision with the given revision_id.

        :param bzr_revision: the revision to import
        :type bzr_revision: bzrlib.revision.Revision
        """
        revision_id = bzr_revision.revision_id
        self.logger.debug("%d of %d: synchronizing revision: %s",
                          self.curr, self.last, revision_id)

        # If did_something is True, new information was found and
        # loaded into the database.
        did_something = False

        self.trans_manager.begin()

        db_revision = getUtility(IRevisionSet).getByRevisionId(revision_id)
        if db_revision is not None:
            # Verify that the revision in the database matches the
            # revision from the branch.  Currently we just check that
            # the parent revision list matches.
            db_parents = db_revision.parents
            bzr_parents = bzr_revision.parent_ids

            seen_parents = set()
            for sequence, parent_id in enumerate(bzr_parents):
                if parent_id in seen_parents:
                    continue
                seen_parents.add(parent_id)
                matching_parents = [db_parent for db_parent in db_parents
                                    if db_parent.parent_id == parent_id]
                if len(matching_parents) == 0:
                    raise RevisionModifiedError(
                        'parent %s was added since last scan' % parent_id)
                elif len(matching_parents) > 1:
                    raise RevisionModifiedError(
                        'parent %s is listed multiple times in db' % parent_id)
                if matching_parents[0].sequence != sequence:
                    raise RevisionModifiedError(
                        'parent %s reordered (old index %d, new index %d)'
                        % (parent_id, matching_parents[0].sequence, sequence))
            if len(seen_parents) != len(db_parents):
                removed_parents = [db_parent.parent_id
                                   for db_parent in db_parents
                                   if db_parent.parent_id not in seen_parents]
                raise RevisionModifiedError(
                    'some parents removed since last scan: %s'
                    % (removed_parents,))
        else:
            # Revision not yet in the database. Load it.
            db_revision = getUtility(IRevisionSet).new(
                revision_id=revision_id,
                log_body=bzr_revision.message,
                revision_date=self._timestampToDatetime(bzr_revision.timestamp),
                revision_author=bzr_revision.committer,
                owner=self._admin,
                parent_ids=bzr_revision.parent_ids)
            did_something = True

        if did_something:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

        return did_something

    def _timestampToDatetime(self, timestamp):
        """Convert the given timestamp to a datetime object.

        This works around a bug in Python that causes datetime.fromtimestamp
        to raise an exception if it is given a negative, fractional timestamp.

        :param timestamp: A timestamp from a bzrlib.revision.Revision
        :type timestamp: float

        :return: A datetime corresponding to the given timestamp.
        """
        # Work around Python bug #1646728.
        # See https://launchpad.net/bugs/81544.
        int_timestamp = int(timestamp)
        revision_date = datetime.fromtimestamp(int_timestamp, tz=UTC)
        revision_date += timedelta(seconds=timestamp - int_timestamp)
        return revision_date

    def syncRevisionNumbers(self):
        """Synchronise the revision numbers for the branch."""
        self.logger.info(
            "synchronizing revision numbers for branch: %s",
            self.bzr_branch.base)

        did_something = False
        self.trans_manager.begin()
        # now synchronise the RevisionNumber objects
        for (index, revision_id) in enumerate(self.bzr_history):
            # sequence numbers start from 1
            sequence = index + 1
            if self.syncRevisionNumber(sequence, revision_id):
                did_something = True

        # finally truncate any further revision numbers (if they exist):
        if self.db_branch.truncateHistory(len(self.bzr_history) + 1):
            did_something = True

        # record that the branch has been updated.
        if len(self.bzr_history) > 0:
            last_revision = self.bzr_history[-1]
        else:
            last_revision = NULL_REVISION

        revision_count = len(self.bzr_history)
        if (last_revision != self.db_branch.last_scanned_id) or \
           (revision_count != self.db_branch.revision_count):
            self.db_branch.updateScannedDetails(last_revision, revision_count)
            did_something = True

        if did_something:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

        return did_something

    def syncRevisionNumber(self, sequence, revision_id):
        """Import the revision number with the given sequence and revision_id

        :param sequence: the sequence number for this revision number
        :type sequence: int
        :param revision_id: GUID of the revision
        :type revision_id: str
        """
        did_something = False

        self.trans_manager.begin()

        db_revision = getUtility(IRevisionSet).getByRevisionId(revision_id)
        db_revno = self.db_branch.getRevisionNumber(sequence)

        # If the database revision history has diverged, so we
        # truncate the database history from this point on.  The
        # replacement revision numbers will be created in their place.
        if db_revno is not None and db_revno.revision != db_revision:
            if self.db_branch.truncateHistory(sequence):
                did_something = True
            db_revno = None

        if db_revno is None:
            db_revno = self.db_branch.createRevisionNumber(
                sequence, db_revision)
            did_something = True

        if did_something:
            self.trans_manager.commit()
        else:
            self.trans_manager.abort()

        return did_something

    def getDiff(self, bzr_revision):
        repo = self.bzr_branch.repository
        if bzr_revision.parent_ids:
            ids = (bzr_revision.revision_id, bzr_revision.parent_ids[0])
            tree_new, tree_old = repo.revision_trees(ids)
        else:
            # can't get both trees at once, so one at a time
            tree_new = repo.revision_tree(bzr_revision.revision_id)
            tree_old = repo.revision_tree(None)
            
        diff_content = StringIO()
        show_diff_trees(tree_old, tree_new, diff_content)
        return diff_content.getvalue()

    def getRevisionMessage(self, bzr_revision):
        outf = StringIO()
        lf = log_formatter('long', to_file=outf)
        rev_id = bzr_revision.revision_id
        rev1 = rev2 = self.bzr_branch.revision_id_to_revno(rev_id)
        if rev1 == 0:
            rev1 = None
            rev2 = None

        show_log(self.bzr_branch,
                 lf,
                 start_revision=rev1,
                 end_revision=rev2,
                 verbose=True
                 )
        return outf.getvalue()

    def sendRevisionNotificationEmails(self):
        initial = self.db_revision_history
        updated = getUtility(
            IRevisionSet).getRevisionHistoryForBranch(self.db_branch)
        # Almost all the time the initial revision history
        # will be a subset of the updated history.
        if initial == updated:
            # Nothing to do here.
            return

        # An individual may be subscribed to a branch
        # more than once (like through a team).
        # Only send the email once, and use the maximum
        # line count.
        email_details = {}
        for subscription in self.db_branch.subscriptions:
            if subscription.notification_level in (
                    BranchSubscriptionNotificationLevel.DIFFSONLY,
                    BranchSubscriptionNotificationLevel.FULL):
                addresses = contactEmailAddresses(subscription.person)
                for address in addresses:
                    curr = email_details.get(
                        address, BranchSubscriptionDiffSize.NODIFF)
                    email_details[address] = max(
                        curr, subscription.max_diff_lines)

        if not email_details:
            # No one is interested.
            return

        if len(initial) == 0:
            # This is the first scan of a new branch.
            if len(updated) == 1:
                revisions = '1 revision'
            else:
                revisions = '%d revisions' % len(updated)
            contents = ('First scan of the branch detected %s'
                        ' in the revision history of the branch.' %
                        revisions)
            for address in email_details:
                self.sendEmail(address, contents)
            return

        # XXX: need to make sure that emails don't
        # get sent for the initial scan of a new branch.

        size = len(initial)
        if updated[:len(initial)] == initial:
            updated = updated[len(initial):]
        else:
            # Branch has been overwritten.
            updated = self.sendReductionEmail(email_details, updated)        

        # From here the following holds true:
        #   updated only holds the revision ids of the
        #   new revisions
        for rev_id in updated: 
            revision = self.bzr_branch.repository.get_revision(rev_id)
            diff = self.getDiff(revision)
            message = self.getRevisionMessage(revision)
            for address, max_diff in email_details.iteritems():
                self.sendDiffEmail(address, max_diff, diff, message)
                
    def sendReductionEmail(self, email_details, updated):
        # First thing to do is to work out the number
        # of revisions removed.
        initial = self.db_revision_history
        match_position = min(len(updated), len(initial))
        while match_position > 0 and (
                initial[:match_position] != updated[:match_position]):
            match_position -= 1
        number_removed = len(initial) - match_position

        if number_removed == 1:
            contents = '1 revision was removed from the branch.'
        else:
            contents = ('%d revisions were removed from the branch.'
                        % number_removed)
        for address in email_details:
            self.sendEmail(address, contents)

        return updated[match_position:]

    def sendDiffEmail(self, address, max_diff, diff, message):
        diff_size = diff.count('\n') + 1

        if max_diff != BranchSubscriptionDiffSize.WHOLEDIFF:
            if max_diff == BranchSubscriptionDiffSize.NODIFF:
                diff = ''
            elif diff_size >  max_diff.value:
                diff = ('The size of the diff (%d lines) is larger than your '
                        'specified limit of %d lines' % (
                    diff_size, max_diff.value))

        contents = "%s\n%s" % (message, diff)
        self.sendEmail(address, contents)

    def sendEmail(self, address, contents):
        branch = self.db_branch
        subject = '[Branch %s] %s' % (branch.unique_name, branch.title)
        headers = {}
        headers["X-Launchpad-Branch"] = branch.unique_name

        body = get_email_template('branch-modified.txt') % {
            'contents': contents,
            'branch_title': branch.title,
            'branch_url': canonical_url(branch),
            'unsubscribe_url': canonical_url(branch) + '/+edit-subscription' }
       
        simple_sendmail(self.email_from, address, subject, body)
