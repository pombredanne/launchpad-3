# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for the process-accepted.py script."""

__metaclass__ = type
__all__ = [
    'close_bugs_for_queue_item',
    'close_bugs_for_sourcepackagerelease',
    'close_bugs_for_sourcepublication',
    'get_bugs_from_changes_file',
    'ProcessAccepted',
    ]

from optparse import OptionValueError
import sys

from debian.deb822 import Deb822Dict
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    )
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archiveuploader.tagfiles import parse_tagfile_content
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadStatus,
    re_bug_numbers,
    re_closes,
    re_lp_closes,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.queue import IPackageUploadSet


def get_bugs_from_changes_file(changes_file):
    """Parse the changes file and return a list of bugs referenced by it.

    The bugs is specified in the Launchpad-bugs-fixed header, and are
    separated by a space character. Nonexistent bug ids are ignored.
    """
    tags = Deb822Dict(parse_tagfile_content(changes_file.read()))
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


def get_bugs_from_changelog_entry(sourcepackagerelease, since_version):
    """Parse the changelog_entry in the sourcepackagerelease and return a
    list of `IBug`s referenced by it.
    """
    changelog = sourcepackagerelease.aggregate_changelog(since_version)
    closes = []
    # There are 2 main regexes to match.  Each match from those can then
    # have further multiple matches from the 3rd regex:
    # closes: NNN, NNN
    # lp: #NNN, #NNN
    regexes = (
        re_closes.finditer(changelog), re_lp_closes.finditer(changelog))
    for regex in regexes:
        for match in regex:
            bug_match = re_bug_numbers.findall(match.group(0))
            closes += map(int, bug_match)

    bugs = []
    for bug_id in closes:
        try:
            bug = getUtility(IBugSet).get(bug_id)
        except NotFoundError:
            continue
        else:
            bugs.append(bug)

    return bugs


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


def close_bugs_for_sourcepublication(source_publication, since_version=None):
    """Close bugs for a given sourcepublication.

    Given a `ISourcePackagePublishingHistory` close bugs mentioned in
    upload changesfile.
    """
    if not can_close_bugs(source_publication):
        return

    sourcepackagerelease = source_publication.sourcepackagerelease
    changesfile_object = sourcepackagerelease.upload_changesfile

    close_bugs_for_sourcepackagerelease(
        sourcepackagerelease, changesfile_object, since_version,
        upload_distroseries=source_publication.distroseries.distribution)


def close_bugs_for_sourcepackagerelease(source_release, changesfile_object,
                                        since_version=None,
                                        upload_distroseries=None):
    """Close bugs for a given source.

    Given a `ISourcePackageRelease` and a corresponding changesfile object,
    close bugs mentioned in the changesfile in the context of the source.

    If changesfile_object is None and since_version is supplied,
    close all the bugs in changelog entries made after that version and up
    to and including the source_release's version.  It does this by parsing
    the changelog on the sourcepackagerelease.  This could be extended in
    the future to deal with the changes file as well but there is no
    requirement to do so right now.
    """
    if since_version and source_release.changelog:
        bugs_to_close = get_bugs_from_changelog_entry(
            source_release, since_version=since_version)
    elif changesfile_object:
        bugs_to_close = get_bugs_from_changes_file(changesfile_object)
    else:
        return

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
        if upload_distroseries is not None:
            target = upload_distroseries.getSourcePackage(
                source_release.sourcepackagename)
        else:
            target = source_release.sourcepackage
        edited_task = bug.setStatus(
            target=target, status=BugTaskStatus.FIXRELEASED, user=janitor)
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


class TargetPolicy:
    """Policy describing what kinds of archives to operate on."""

    def __init__(self, logger):
        self.logger = logger

    def getTargetArchives(self, distribution):
        """Get target archives of the right sort for `distribution`."""
        raise NotImplemented("getTargetArchives")

    def describeArchive(self, archive):
        """Return textual description for `archive` in this script run."""
        raise NotImplemented("describeArchive")

    def postprocessSuccesses(self, queue_ids):
        """Optionally, post-process successfully processed queue items.

        :param queue_ids: An iterable of `PackageUpload` ids that were
            successfully processed.
        """


class PPATargetPolicy(TargetPolicy):
    """Target policy for PPA archives."""

    def getTargetArchives(self, distribution):
        """See `TargetPolicy`."""
        return distribution.getPendingAcceptancePPAs()

    def describeArchive(self, archive):
        """See `TargetPolicy`."""
        return archive.archive_url


class CopyArchiveTargetPolicy(TargetPolicy):
    """Target policy for copy archives."""

    def getTargetArchives(self, distribution):
        """See `TargetPolicy`."""
        return getUtility(IArchiveSet).getArchivesForDistribution(
            distribution, purposes=[ArchivePurpose.COPY])

    def describeArchive(self, archive):
        """See `TargetPolicy`."""
        return archive.displayname


class DistroTargetPolicy(TargetPolicy):
    """Target policy for distro archives."""

    def getTargetArchives(self, distribution):
        """See `TargetPolicy`."""
        return distribution.all_distro_archives

    def describeArchive(self, archive):
        """See `TargetPolicy`."""
        return archive.purpose.title

    def postprocessSuccesses(self, queue_ids):
        """See `TargetPolicy`."""
        self.logger.debug("Closing bugs.")
        for queue_id in queue_ids:
            queue_item = getUtility(IPackageUploadSet).get(queue_id)
            close_bugs_for_queue_item(queue_item)


class ProcessAccepted(LaunchpadCronScript):
    """Queue/Accepted processor.

    Given a distribution to run on, obtains all the queue items for the
    distribution and then gets on and deals with any accepted items, preparing
    them for publishing as appropriate.
    """

    @property
    def lockfilename(self):
        """See `LaunchpadScript`."""
        # Avoid circular imports.
        from lp.archivepublisher.publishing import GLOBAL_PUBLISHER_LOCK
        return GLOBAL_PUBLISHER_LOCK

    def add_my_options(self):
        """Command line options for this script."""
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

        self.parser.add_option(
            '-D', '--derived', action="store_true", dest="derived",
            default=False, help="Process all Ubuntu-derived distributions.")

        self.parser.add_option(
            "--ppa", action="store_true", dest="ppa", default=False,
            help="Run only over PPA archives.")

        self.parser.add_option(
            "--copy-archives", action="store_true", dest="copy_archives",
            default=False, help="Run only over COPY archives.")

    def _commit(self):
        """Commit transaction (unless in dry-run mode)."""
        if self.options.dryrun:
            self.logger.debug("Skipping commit: dry-run mode.")
        else:
            self.txn.commit()

    def findNamedDistro(self, distro_name):
        """Find the `Distribution` called `distro_name`."""
        self.logger.debug("Finding distribution %s.", distro_name)
        distro = getUtility(IDistributionSet).getByName(distro_name)
        if distro is None:
            raise LaunchpadScriptFailure(
                "Distribution '%s' not found." % distro_name)
        return distro

    def findTargetDistros(self):
        """Find the distribution(s) to process, based on arguments."""
        if self.options.derived:
            return getUtility(IDistributionSet).getDerivedDistributions()
        else:
            return [self.findNamedDistro(self.args[0])]

    def validateArguments(self):
        """Validate command-line arguments."""
        if self.options.ppa and self.options.copy_archives:
            raise OptionValueError(
                "Specify only one of copy archives or ppa archives.")
        if self.options.derived:
            if len(self.args) != 0:
                raise OptionValueError(
                    "Can't combine --derived with a distribution name.")
        else:
            if len(self.args) != 1:
                raise OptionValueError(
                    "Need to be given exactly one non-option argument. "
                    "Namely the distribution to process.")

    def makeTargetPolicy(self):
        """Pick and instantiate a `TargetPolicy` based on given options."""
        if self.options.ppa:
            policy_class = PPATargetPolicy
        elif self.options.copy_archives:
            policy_class = CopyArchiveTargetPolicy
        else:
            policy_class = DistroTargetPolicy
        return policy_class(self.logger)

    def processQueueItem(self, queue_item):
        """Attempt to process `queue_item`.

        This method swallows exceptions that occur while processing the
        item.

        :param queue_item: A `PackageUpload` to process.
        :return: True on success, or False on failure.
        """
        self.logger.debug("Processing queue item %d" % queue_item.id)
        try:
            queue_item.realiseUpload(self.logger)
        except Exception:
            message = "Failure processing queue_item %d" % queue_item.id
            properties = [('error-explanation', message)]
            request = ScriptRequest(properties)
            ErrorReportingUtility().raising(sys.exc_info(), request)
            self.logger.error('%s (%s)', message, request.oopsid)
            return False
        else:
            self.logger.debug(
                "Successfully processed queue item %d", queue_item.id)
            return True

    def processForDistro(self, distribution, target_policy):
        """Process all queue items for a distribution.

        Commits between items, except in dry-run mode.

        :param distribution: The `Distribution` to process queue items for.
        :param target_policy: The applicable `TargetPolicy`.
        :return: A list of all successfully processed items' ids.
        """
        processed_queue_ids = []
        for archive in target_policy.getTargetArchives(distribution):
            description = target_policy.describeArchive(archive)
            for distroseries in distribution.series:

                self.logger.debug("Processing queue for %s %s" % (
                    distroseries.name, description))

                queue_items = distroseries.getPackageUploads(
                    status=PackageUploadStatus.ACCEPTED, archive=archive)
                for queue_item in queue_items:
                    if self.processQueueItem(queue_item):
                        processed_queue_ids.append(queue_item.id)
                    # Commit even on error; we may have altered the
                    # on-disk archive, so the partial state must
                    # make it to the DB.
                    self._commit()
        return processed_queue_ids

    def main(self):
        """Entry point for a LaunchpadScript."""
        self.validateArguments()
        target_policy = self.makeTargetPolicy()
        try:
            for distro in self.findTargetDistros():
                queue_ids = self.processForDistro(distro, target_policy)
                self._commit()
                target_policy.postprocessSuccesses(queue_ids)
                self._commit()

        finally:
            self.logger.debug("Rolling back any remaining transactions.")
            self.txn.abort()

        return 0
