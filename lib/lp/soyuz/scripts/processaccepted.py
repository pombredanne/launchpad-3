# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for the process-accepted.py script."""

__metaclass__ = type
__all__ = [
    'close_bugs',
    'close_bugs_for_queue_item',
    'close_bugs_for_sourcepackagerelease',
    'close_bugs_for_sourcepublication',
    'get_bugs_from_changes_file',
    'ProcessAccepted',
    ]

from debian.deb822 import Deb822Dict
import sys

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    )
from lp.app.errors import NotFoundError
from lp.archiveuploader.tagfiles import parse_tagfile_lines
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.scripts.base import LaunchpadScript
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import (
    IArchiveSet,
    )
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet,
    )


def get_bugs_from_changes_file(changes_file):
    """Parse the changes file and return a list of bugs referenced by it.

    The bugs is specified in the Launchpad-bugs-fixed header, and are
    separated by a space character. Nonexistent bug ids are ignored.
    """
    contents = changes_file.read()
    changes_lines = contents.splitlines(True)
    tags = Deb822Dict(parse_tagfile_lines(changes_lines, allow_unsigned=True))
    bugs_fixed_line = tags.get('Launchpad-bugs-fixed', '')
    bugs = []
    for bug_id in bugs_fixed_line.split():
        if not bug_id.isdigit():
            continue
        bug_id = int(bug_id)
        try:
            bug = getUtility(IBugSet).get(bug_id)
        except NotFoundError:
            continue
        else:
            bugs.append(bug)
    return bugs


def close_bugs(queue_ids):
    """Close any bugs referenced by the queue items.

    Retrieve PackageUpload objects for the given ID list and perform
    close_bugs_for_queue_item on each of them.
    """
    for queue_id in queue_ids:
        queue_item = getUtility(IPackageUploadSet).get(queue_id)
        close_bugs_for_queue_item(queue_item)


def can_close_bugs(target):
    """Whether or not bugs should be closed in the given target.

    ISourcePackagePublishingHistory and IPackageUpload are the
    currently supported targets.

    Source publications or package uploads targeted to pockets
    PROPOSED/BACKPORTS or any other archive purpose than PRIMARY will
    not automatically close bugs.
    """
    banned_pockets = (
        PackagePublishingPocket.PROPOSED,
        PackagePublishingPocket.BACKPORTS)

    if (target.pocket in banned_pockets or
       target.archive.purpose != ArchivePurpose.PRIMARY):
        return False

    return True


def close_bugs_for_queue_item(queue_item, changesfile_object=None):
    """Close bugs for a given queue item.

    'queue_item' is an IPackageUpload instance and is given by the user.

    'changesfile_object' is optional if not given this function will try
    to use the IPackageUpload.changesfile, which is only available after
    the upload is processed and committed.

    In practice, 'changesfile_object' is only set when we are closing bugs
    in upload-time (see
    archiveuploader/ftests/nascentupload-closing-bugs.txt).

    Skip bug-closing if the upload is target to pocket PROPOSED or if
    the upload is for a PPA.

    Set the package bugtask status to Fix Released and the changelog is added
    as a comment.
    """
    if not can_close_bugs(queue_item):
        return

    if changesfile_object is None:
        if queue_item.is_delayed_copy:
            sourcepackagerelease = queue_item.sources[0].sourcepackagerelease
            changesfile_object = sourcepackagerelease.upload_changesfile
        else:
            changesfile_object = queue_item.changesfile

    for source_queue_item in queue_item.sources:
        close_bugs_for_sourcepackagerelease(
            source_queue_item.sourcepackagerelease, changesfile_object)


def close_bugs_for_sourcepublication(source_publication):
    """Close bugs for a given sourcepublication.

    Given a `ISourcePackagePublishingHistory` close bugs mentioned in
    upload changesfile.
    """
    if not can_close_bugs(source_publication):
        return

    sourcepackagerelease = source_publication.sourcepackagerelease
    changesfile_object = sourcepackagerelease.upload_changesfile

    # No changesfile available, cannot close bugs.
    if changesfile_object is None:
        return

    close_bugs_for_sourcepackagerelease(
        sourcepackagerelease, changesfile_object)


def close_bugs_for_sourcepackagerelease(source_release, changesfile_object):
    """Close bugs for a given source.

    Given a `ISourcePackageRelease` and a corresponding changesfile object,
    close bugs mentioned in the changesfile in the context of the source.
    """
    bugs_to_close = get_bugs_from_changes_file(changesfile_object)

    # No bugs to be closed by this upload, move on.
    if not bugs_to_close:
        return

    janitor = getUtility(ILaunchpadCelebrities).janitor
    for bug in bugs_to_close:
        # We need to remove the security proxy here because the bug
        # might be private and if this code is called via someone using
        # the +queue page they will get an OOPS.  Ideally, we should
        # migrate this code to the Job system though, but that's a lot
        # of work.  If you don't do that and you're changing stuff in
        # here, BE CAREFUL with the unproxied bug object and look at
        # what you're doing with it that might violate security.
        bug = removeSecurityProxy(bug)
        edited_task = bug.setStatus(
            target=source_release.sourcepackage,
            status=BugTaskStatus.FIXRELEASED,
            user=janitor)
        if edited_task is not None:
            assert source_release.changelog_entry is not None, (
                "New source uploads should have a changelog.")
            content = (
                "This bug was fixed in the package %s"
                "\n\n---------------\n%s" % (
                source_release.title, source_release.changelog_entry))
            bug.newMessage(
                owner=janitor,
                subject=bug.followup_subject(),
                content=content)


class ProcessAccepted(LaunchpadScript):
    """Queue/Accepted processor.

    Given a distribution to run on, obtains all the queue items for the
    distribution and then gets on and deals with any accepted items, preparing
    them for publishing as appropriate.
    """

    def add_my_options(self):
        """Command line options for this script."""
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

        self.parser.add_option(
            "--ppa", action="store_true",
            dest="ppa", metavar="PPA", default=False,
            help="Run only over PPA archives.")

        self.parser.add_option(
            "--copy-archives", action="store_true",
            dest="copy_archives", metavar="COPY_ARCHIVES",
            default=False, help="Run only over COPY archives.")

    @property
    def lockfilename(self):
        """Override LaunchpadScript's lock file name."""
        return "/var/lock/launchpad-upload-queue.lock"

    def main(self):
        """Entry point for a LaunchpadScript."""
        if len(self.args) != 1:
            self.logger.error(
                "Need to be given exactly one non-option argument. "
                "Namely the distribution to process.")
            return 1

        if self.options.ppa and self.options.copy_archives:
            self.logger.error(
                "Specify only one of copy archives or ppa archives.")
            return 1

        distro_name = self.args[0]

        processed_queue_ids = []
        try:
            self.logger.debug("Finding distribution %s." % distro_name)
            distribution = getUtility(IDistributionSet).getByName(distro_name)

            # target_archives is a tuple of (archive, description).
            if self.options.ppa:
                target_archives = [
                    (archive, archive.archive_url)
                    for archive in distribution.getPendingAcceptancePPAs()]
            elif self.options.copy_archives:
                copy_archives = getUtility(
                    IArchiveSet).getArchivesForDistribution(
                        distribution, purposes=[ArchivePurpose.COPY])
                target_archives = [
                    (archive, archive.displayname)
                    for archive in copy_archives]
            else:
                target_archives = [
                    (archive, archive.purpose.title)
                    for archive in distribution.all_distro_archives]

            for archive, description in target_archives:
                for distroseries in distribution.series:

                    self.logger.debug("Processing queue for %s %s" % (
                        distroseries.name, description))

                    queue_items = distroseries.getQueueItems(
                        PackageUploadStatus.ACCEPTED, archive=archive)
                    for queue_item in queue_items:
                        try:
                            queue_item.realiseUpload(self.logger)
                        except Exception:
                            message = "Failure processing queue_item %d" % (
                                queue_item.id)
                            properties = [('error-explanation', message)]
                            request = ScriptRequest(properties)
                            error_utility = ErrorReportingUtility()
                            error_utility.raising(sys.exc_info(), request)
                            self.logger.error('%s (%s)' % (message,
                                request.oopsid))
                        else:
                            processed_queue_ids.append(queue_item.id)

            if not self.options.dryrun:
                self.txn.commit()
            else:
                self.logger.debug("Dry Run mode.")

            if not self.options.ppa and not self.options.copy_archives:
                self.logger.debug("Closing bugs.")
                close_bugs(processed_queue_ids)

            if not self.options.dryrun:
                self.txn.commit()

        finally:
            self.logger.debug("Rolling back any remaining transactions.")
            self.txn.abort()

        return 0
