# Copyright 2012-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'close_bugs_for_queue_item',
    'close_bugs_for_sourcepublication',
    "ProcessAcceptedBugsJob",
    ]

import logging

from debian.deb822 import Deb822Dict
from storm.locals import (
    And,
    Int,
    JSON,
    Reference,
    )
from zope.component import getUtility
from zope.interface import (
    implementer,
    provider,
    )
from zope.security.management import getSecurityPolicy

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archiveuploader.tagfiles import parse_tagfile_content
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.distroseries import DistroSeries
from lp.services.config import config
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.webapp.authorization import LaunchpadPermissiveSecurityPolicy
from lp.soyuz.enums import (
    ArchivePurpose,
    re_bug_numbers,
    re_closes,
    re_lp_closes,
    )
from lp.soyuz.interfaces.processacceptedbugsjob import (
    IProcessAcceptedBugsJob,
    IProcessAcceptedBugsJobSource,
    )
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease


def close_bug_ids_for_sourcepackagerelease(distroseries, spr, bug_ids):
    bugs = list(getUtility(IBugSet).getByNumbers(bug_ids))
    janitor = getUtility(ILaunchpadCelebrities).janitor
    target = distroseries.getSourcePackage(spr.sourcepackagename)
    assert spr.changelog_entry is not None, (
        "New source uploads should have a changelog.")
    content = (
        "This bug was fixed in the package %s"
        "\n\n---------------\n%s" % (spr.title, spr.changelog_entry))

    for bug in bugs:
        edited_task = bug.setStatus(
            target=target, status=BugTaskStatus.FIXRELEASED, user=janitor)
        if edited_task is not None:
            bug.newMessage(
                owner=janitor,
                subject=bug.followup_subject(),
                content=content)


def get_bug_ids_from_changes_file(changes_file):
    """Parse the changes file and return a list of bug IDs referenced by it.

    The bugs is specified in the Launchpad-bugs-fixed header, and are
    separated by a space character. Nonexistent bug ids are ignored.
    """
    tags = Deb822Dict(parse_tagfile_content(changes_file.read()))
    bugs_fixed = tags.get('Launchpad-bugs-fixed', '').split()
    return [int(bug_id) for bug_id in bugs_fixed if bug_id.isdigit()]


def get_bug_ids_from_changelog_entry(sourcepackagerelease, since_version):
    """Parse the changelog_entry in the sourcepackagerelease and return a
    list of bug IDs referenced by it.
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
    return closes


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
    in upload-time (see nascentupload-closing-bugs.txt).

    Skip bug-closing if the upload is target to pocket PROPOSED or if
    the upload is for a PPA.

    Set the package bugtask status to Fix Released and the changelog is added
    as a comment.
    """
    if not can_close_bugs(queue_item):
        return

    if changesfile_object is None:
        changesfile_object = queue_item.changesfile

    for source_queue_item in queue_item.sources:
        close_bugs_for_sourcepackagerelease(
            queue_item.distroseries, source_queue_item.sourcepackagerelease,
            changesfile_object)


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
        source_publication.distroseries, sourcepackagerelease,
        changesfile_object, since_version)


def close_bugs_for_sourcepackagerelease(distroseries, source_release,
                                        changesfile_object,
                                        since_version=None):
    """Close bugs for a given source.

    Given an `IDistroSeries`, an `ISourcePackageRelease`, and a
    corresponding changesfile object, close bugs mentioned in the
    changesfile in the context of the source.

    If changesfile_object is None and since_version is supplied,
    close all the bugs in changelog entries made after that version and up
    to and including the source_release's version.  It does this by parsing
    the changelog on the sourcepackagerelease.  This could be extended in
    the future to deal with the changes file as well but there is no
    requirement to do so right now.
    """
    if since_version and source_release.changelog:
        bug_ids_to_close = get_bug_ids_from_changelog_entry(
            source_release, since_version=since_version)
    elif changesfile_object:
        bug_ids_to_close = get_bug_ids_from_changes_file(changesfile_object)
    else:
        return

    # No bugs to be closed by this upload, move on.
    if not bug_ids_to_close:
        return

    if getSecurityPolicy() == LaunchpadPermissiveSecurityPolicy:
        # We're already running in a script, so we can just close the bugs
        # directly.
        close_bug_ids_for_sourcepackagerelease(
            distroseries, source_release, bug_ids_to_close)
    else:
        job_source = getUtility(IProcessAcceptedBugsJobSource)
        job_source.create(distroseries, source_release, bug_ids_to_close)


@implementer(IProcessAcceptedBugsJob)
# Oddly, BaseRunnableJob inherits from BaseRunnableJobSource so this class
# is both the factory for jobs (the "implementer", above) and the source for
# runnable jobs (not the constructor of the job source, the class provides
# the IJobSource interface itself).
@provider(IProcessAcceptedBugsJobSource)
class ProcessAcceptedBugsJob(StormBase, BaseRunnableJob):
    """Base class for jobs to close bugs for accepted package uploads."""

    __storm_table__ = "ProcessAcceptedBugsJob"

    config = config.IProcessAcceptedBugsJobSource

    # The Job table contains core job details.
    job_id = Int("job", primary=True)
    job = Reference(job_id, Job.id)

    distroseries_id = Int(name="distroseries")
    distroseries = Reference(distroseries_id, DistroSeries.id)

    sourcepackagerelease_id = Int(name="sourcepackagerelease")
    sourcepackagerelease = Reference(
        sourcepackagerelease_id, SourcePackageRelease.id)

    metadata = JSON('json_data')

    def __init__(self, distroseries, sourcepackagerelease, bug_ids):
        self.job = Job()
        self.distroseries = distroseries
        self.sourcepackagerelease = sourcepackagerelease
        self.metadata = {"bug_ids": list(bug_ids)}
        super(ProcessAcceptedBugsJob, self).__init__()

    @property
    def bug_ids(self):
        return self.metadata["bug_ids"]

    @classmethod
    def create(cls, distroseries, sourcepackagerelease, bug_ids):
        """See `IProcessAcceptedBugsJobSource`."""
        assert distroseries is not None, "No distroseries specified."
        assert sourcepackagerelease is not None, (
            "No sourcepackagerelease specified.")
        assert sourcepackagerelease.changelog_entry is not None, (
            "New source uploads should have a changelog.")
        assert bug_ids, "No bug IDs specified."
        job = ProcessAcceptedBugsJob(
            distroseries, sourcepackagerelease, bug_ids)
        IMasterStore(ProcessAcceptedBugsJob).add(job)
        job.celeryRunOnCommit()
        return job

    def getOperationDescription(self):
        """See `IRunnableJob`."""
        return "closing bugs for accepted package upload"

    def run(self):
        """See `IRunnableJob`."""
        logger = logging.getLogger()
        spr = self.sourcepackagerelease
        logger.info(
            "Closing bugs for %s/%s (%s)" %
            (spr.name, spr.version, self.distroseries))
        close_bug_ids_for_sourcepackagerelease(
            self.distroseries, spr, self.metadata["bug_ids"])

    def __repr__(self):
        """Returns an informative representation of the job."""
        parts = ["%s to close bugs [" % self.__class__.__name__]
        parts.append(", ".join(str(bug_id) for bug_id in self.bug_ids))
        spr = self.sourcepackagerelease
        parts.append(
            "] for %s/%s (%s)" % (spr.name, spr.version, self.distroseries))
        return "<%s>" % "".join(parts)

    @staticmethod
    def iterReady():
        """See `IJobSource`."""
        return IStore(ProcessAcceptedBugsJob).find((ProcessAcceptedBugsJob),
            And(ProcessAcceptedBugsJob.job == Job.id,
                Job.id.is_in(Job.ready_jobs)))

    def makeDerived(self):
        """Support UniversalJobSource.

        (Most Job ORM classes are generic, because their database table is
        used for several related job types.  Therefore, they have derived
        classes to implement the specific Job.

        ProcessAcceptedBugsJob implements the specific job, so its
        makeDerived returns itself.)
        """
        return self

    def getDBClass(self):
        return self.__class__
