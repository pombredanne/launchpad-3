# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build interfaces."""

__metaclass__ = type

__all__ = [
    'BUILDD_MANAGER_LOG_NAME',
    'BuildStatus',
    'IBuildBase',
    ]

from zope.interface import Attribute, Interface
from zope.schema import Choice, Datetime, Object, TextLine, Timedelta
from lazr.enum import DBEnumeratedType, DBItem
from lazr.restful.declarations import exported
from lazr.restful.fields import Reference

from lp.buildmaster.interfaces.builder import IBuilder
from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.interfaces.buildqueue import IBuildQueue
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import IArchive
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad import _


BUILDD_MANAGER_LOG_NAME = "slave-scanner"


class BuildStatus(DBEnumeratedType):
    """Build status type

    Builds exist in the database in a number of states such as 'complete',
    'needs build' and 'dependency wait'. We need to track these states in
    order to correctly manage the autobuilder queues in the BuildQueue table.
    """

    NEEDSBUILD = DBItem(0, """
        Needs building

        Build record is fresh and needs building. Nothing is yet known to
        block this build and it is a candidate for building on any free
        builder of the relevant architecture
        """)

    FULLYBUILT = DBItem(1, """
        Successfully built

        Build record is an historic account of the build. The build is complete
        and needs no further work to complete it. The build log etc are all
        in place if available.
        """)

    FAILEDTOBUILD = DBItem(2, """
        Failed to build

        Build record is an historic account of the build. The build failed and
        cannot be automatically retried. Either a new upload will be needed
        or the build will have to be manually reset into 'NEEDSBUILD' when
        the issue is corrected
        """)

    MANUALDEPWAIT = DBItem(3, """
        Dependency wait

        Build record represents a package whose build dependencies cannot
        currently be satisfied within the relevant DistroArchSeries. This
        build will have to be manually given back (put into 'NEEDSBUILD') when
        the dependency issue is resolved.
        """)

    CHROOTWAIT = DBItem(4, """
        Chroot problem

        Build record represents a build which needs a chroot currently known
        to be damaged or bad in some way. The buildd maintainer will have to
        reset all relevant CHROOTWAIT builds to NEEDSBUILD after the chroot
        has been fixed.
        """)

    SUPERSEDED = DBItem(5, """
        Build for superseded Source

        Build record represents a build which never got to happen because the
        source package release for the build was superseded before the job
        was scheduled to be run on a builder. Builds which reach this state
        will rarely if ever be reset to any other state.
        """)

    BUILDING = DBItem(6, """
        Currently building

        Build record represents a build which is being build by one of the
        available builders.
        """)

    FAILEDTOUPLOAD = DBItem(7, """
        Failed to upload

        Build record is an historic account of a build that could not be
        uploaded correctly. It's mainly genereated by failures in
        process-upload which quietly rejects the binary upload resulted
        by the build procedure.
        In those cases all the build historic information will be stored (
        buildlog, datebuilt, duration, builder, etc) and the buildd admins
        will be notified via process-upload about the reason of the rejection.
        """)


class IBuildBase(Interface):
    """Common interface shared by farm jobs that build a package."""
    # XXX 2010-04-21 michael.nelson bug=567922. This interface
    # can be removed once all *Build classes inherit from
    # IBuildFarmJob/IPackageBuild. Until that time, to allow the shared
    # implementation of handling build status, IBuildBase needs to
    # provide aliases for buildstate, buildlog and datebuilt as follows:
    # status => buildstate
    # log => buildlog
    # date_finished => datebuilt
    status = Choice(
            title=_('State'), required=True, vocabulary=BuildStatus,
            description=_("The current build state."))
    log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the entire buildlog."))
    date_finished = Datetime(
            title=_('Date built'), required=False,
            description=_("The time when the build result got collected."))


    build_farm_job_type = Choice(
        title=_("Job type"), required=True, readonly=True,
        vocabulary=BuildFarmJobType,
        description=_("The specific type of job."))

    # XXX: wgrant 2010-01-20 bug=507712: Most of these attribute names
    # are bad.
    datecreated = exported(
        Datetime(
            title=_('Date created'), required=True, readonly=True,
            description=_("The time when the build request was created.")))

    buildstate = exported(status)

    date_first_dispatched = exported(
        Datetime(
            title=_('Date first dispatched'), required=False,
            description=_("The actual build start time. Set when the build "
                          "is dispatched the first time and not changed in "
                          "subsequent build attempts.")))

    builder = Object(
        title=_("Builder"), schema=IBuilder, required=False,
        description=_("The Builder which address this build request."))

    datebuilt = exported(date_finished)

    buildduration = Timedelta(
        title=_("Build Duration"), required=False,
        description=_("Build duration interval, calculated when the "
                      "build result gets collected."))

    buildlog = log

    build_log_url = exported(
        TextLine(
            title=_("Build Log URL"), required=False,
            description=_("A URL for the build log. None if there is no "
                          "log available.")))

    buildqueue_record = Object(
        schema=IBuildQueue, required=True,
        title=_("Corresponding BuildQueue record"))

    is_private = Attribute("Whether the build should be treated as private.")

    policy_name = TextLine(
        title=_("Policy name"), required=True,
        description=_("The upload policy to use for handling these builds."))

    archive = exported(
        Reference(
            title=_("Archive"), schema=IArchive,
            required=True, readonly=True,
            description=_("The Archive context for this build.")))

    current_component = Attribute(
        "Component where the source related to this build was last "
        "published.")

    pocket = exported(
        Choice(
            title=_('Pocket'), required=True,
            vocabulary=PackagePublishingPocket,
            description=_("The build targeted pocket.")))

    dependencies = exported(
        TextLine(
            title=_("Dependencies"), required=False,
            description=_("Debian-like dependency line that must be satisfied"
                          " before attempting to build this request.")))

    distribution = exported(
        Reference(
            schema=IDistribution,
            title=_("Distribution"), required=True,
            description=_("Shortcut for its distribution.")))

    upload_log = Object(
        schema=ILibraryFileAlias, required=False,
        title=_("The LibraryFileAlias containing the upload log for "
                "build resulting in an upload that could not be processed "
                "successfully. Otherwise it will be None."))

    upload_log_url = exported(
        TextLine(
            title=_("Upload Log URL"), required=False,
            description=_("A URL for failed upload logs."
                          "Will be None if there was no failure.")))

    title = exported(TextLine(title=_("Title"), required=False))

    def processUpload(leaf, root, logger):
        """Process an upload.
        
        :param leaf: Leaf for this particular upload
        :param root: Root directory for the uploads
        :param logger: A logger object
        """

    def getUploadLogContent(root, leaf):
        """Retrieve the upload log contents.

        :param root: Root directory for the uploads
        :param leaf: Leaf for this particular upload
        :return: Contents of log file or message saying no log file was found.
        """

    def handleStatus(status, librarian, slave_status):
        """Handle a finished build status from a slave.

        :param status: Slave build status string with 'BuildStatus.' stripped.
        :param slave_status: A dict as returned by IBuilder.slaveStatus
        """

    def getLogFromSlave(build):
        """Get last buildlog from slave.

        Invoke getFileFromSlave method with 'buildlog' identifier.
        """

    def queueBuild(build, suspended=False):
        """Create a BuildQueue entry for this build.

        :param suspended: Whether the associated `Job` instance should be
            created in a suspended state.
        """

    def estimateDuration():
        """Estimate the build duration."""

    def storeBuildInfo(build, librarian, slave_status):
        """Store available information for the build job.

        Subclasses can override this as needed, and call it from custom status
        handlers, but it should not be called externally.
        """

    def verifySuccessfulUpload():
        """Verify that the upload of this build completed succesfully."""

    def storeUploadLog(content):
        """Store the given content as the build upload_log.

        :param content: string containing the upload-processor log output for
            the binaries created in this build.
        """

    def notify(extra_info=None):
        """Notify current build state to related people via email."""

    def makeJob():
        """Construct and return an `IBuildFarmJob` for this build."""
