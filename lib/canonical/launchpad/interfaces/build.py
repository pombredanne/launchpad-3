# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'BuildStatus',
    'IBuild',
    'IBuildSet',
    'IHasBuildRecords'
    ]

from zope.interface import Interface, Attribute
from zope.schema import Timedelta

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem

class IBuild(Interface):
    """A Build interface"""
    id = Attribute("The build ID.")
    datecreated = Attribute("Date of BinPackage Creation")
    processor = Attribute("BinaryPackage Processor")
    distroarchseries = Attribute("The Distro Arch Series")
    buildstate = Attribute("BinaryBuild State")
    datebuilt = Attribute("Binary Date of Built")
    buildduration = Attribute("Build Duration Interval")
    buildlog = Attribute("The Build LOG Referency")
    builder = Attribute("The Builder")
    sourcepackagerelease = Attribute("SourcePackageRelease reference")
    pocket = Attribute("Target pocket of this build")
    dependencies = Attribute("Debian-like dependency line for DEPWAIT builds")
    archive = Attribute("The archive")
    estimated_build_duration = Timedelta(
        title=_("Estimated Build Duration"), required=False,
        description=_("Estimated build duration interval"))

    # Properties
    current_component = Attribute(
        "Component where the ISourcePackageRelease related to "
        "this build was published.")
    title = Attribute("Build Title")
    changesfile = Attribute("The Build Changesfile object, returns None if "
                            "it is a gina-inserted record.")
    distroseries = Attribute("Direct parent needed by CanonicalURL")
    buildqueue_record = Attribute("Corespondent BuildQueue record")
    was_built = Attribute("Whether or not modified by the builddfarm.")
    build_icon = Attribute("Return the icon url correspondent to buildstate.")
    distribution = Attribute("Shortcut for its distribution.")
    distributionsourcepackagerelease = Attribute("The page showing the "
        "details for this sourcepackagerelease in this distribution.")
    binarypackages = Attribute(
        "A list of binary packages that resulted from this build, "
        "not limited and ordered by name.")
    distroarchseriesbinarypackages = Attribute(
        "A list of distroarchseriesbinarypackages that resulted from this"
        "build, ordered by name.")

    can_be_rescored = Attribute(
        "Whether or not this build record can be rescored manually.")

    can_be_retried = Attribute(
        "Whether or not this build record can be retried.")

    calculated_buildstart = Attribute(
        "Emulates a buildstart timestamp by calculating it from "
        "datebuilt - buildduration.")

    is_virtualized = Attribute(
        "Whether or not this build requires a virtual build host or not.")

    package_upload = Attribute(
        "The PackageUpload for this build, or None if there is "
        "no build.")

    component_dependencies = Attribute(
        "Return a dictionary which maps a component name to a list of "
        "component names it could depend of.")

    ogre_components = Attribute(
        "The components this build is allowed to use. It returns a string "
        "that can be used directly at the end of sources.list lines.")

    def retry():
        """Restore the build record to its initial state.

        Build record loses its history, is moved to NEEDSBUILD and a new
        non-scored BuildQueue entry is created for it.
        """

    def updateDependencies():
        """Update the build-dependencies line within the targeted context."""

    def __getitem__(name):
        """Mapped to getBinaryPackageRelease."""

    def getBinaryPackageRelease(name):
        """Return the binary package from this build with the given name, or
        raise NotFoundError if no such package exists.
        """

    def createBinaryPackageRelease(
        binarypackagename, version, summary, description, binpackageformat,
        component, section, priority, shlibdeps, depends, recommends,
        suggests, conflicts, replaces, provides, pre_depends, enhances,
        breaks, essential, installedsize, architecturespecific):
        """Create and return a `BinaryPackageRelease`.

        The binarypackagerelease will be attached to this specific build.
        """

    def createBuildQueueEntry():
        """Create a BuildQueue entry for this build record."""

    def notify():
        """Notify current build state to related people via email.

        If config.buildmaster.build_notification is disable, simply
        return.

        If config.builddmaster.notify_owner is enabled and SPR.creator
        has preferredemail it will send an email to the creator, Bcc:
        to the config.builddmaster.default_recipient. If one of the
        conditions was not satisfied, no preferredemail found (autosync
        or untouched packages from debian) or config options disabled,
        it will only send email to the specified default recipient.

        This notification will contain useful information about
        the record in question (all states are supported), see
        doc/build-notification.txt for further information.
        """


class IBuildSet(Interface):
    """Interface for BuildSet"""

    def getBuildBySRAndArchtag(sourcepackagereleaseID, archtag):
        """Return a build for a SourcePackageRelease and an ArchTag"""

    def getByBuildID(id):
        """Return the exact build specified.

        id is the numeric ID of the build record in the database.
        I.E. getUtility(IBuildSet).getByBuildID(foo).id == foo
        """

    def getPendingBuildsForArchSet(archseries):
        """Return all pending build records within a group of ArchSerieses

        Pending means that buildstatus is NEEDSBUILDING.
        """

    def getBuildsForBuilder(builder_id, status=None, name=None):
        """Return build records touched by a builder.

        If status is provided, only builders with that status will
        be returned. If name is passed, return only build which the
        sourcepackagename matches (SQL LIKE).
        """

    def getBuildsForArchive(archive, status=None, name=None, pocket=None):
        """Return build records targeted to a given IArchive.

        If status is provided, only builders with that status will
        be returned. If name is passed, return only build which the
        sourcepackagename matches (SQL LIKE).
        """

    def getBuildsByArchIds(arch_ids, status=None, name=None, pocket=None):
        """Retrieve Build Records for a given arch_ids list.

        Optionally, for a given status and/or pocket, if ommited return all
        records. If name is passed return only the builds which the
        sourcepackagename matches (SQL LIKE).
        """
    def retryDepWaiting(distroarchseries):
        """Re-process all MANUALDEPWAIT builds for a given IDistroArchSeries.

        This method will update all the dependency lines of all MANUALDEPWAIT
        records in the given architecture and those with all dependencies
        satisfied at this point will be automatically retried and re-scored.
        """


class IHasBuildRecords(Interface):
    """An Object that has build records"""

    def getBuildRecords(build_state=None, name=None, pocket=None,
                        user=None):
        """Return build records owned by the object.

        The optional 'build_state' argument selects build records in a specific
        state. This excludes the build records generated by Gina by selecting
        a null datebuilt when buildstate is FULLYBUILT. Results are ordered
        by descending datebuilt. NEEDSBUILD records are special, they are
        ordered by descending BuildQueue.lastscore.  If the optional 'name'
        argument is passed try to find only those builds which the
        sourcepackagename matches (SQL LIKE).
        If pocket is specified return only builds for this pocket, otherwise
        return all.
        "user" is the requesting user and if specified can be used in
        permission checks to see if he is allowed to view the build.
        """


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
