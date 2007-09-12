# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'IBuild',
    'IBuildSet',
    'IHasBuildRecords'
    ]

from zope.interface import Interface, Attribute

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

    # Properties
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
        "not limitted and ordered by name.")
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
    is_trusted = Attribute(
        "whether or not the record corresponds to a source targeted to "
        "the distribution main_archive (archive == distro.main_archive).")

    def retry():
        """Restore the build record to its initial state.

        Build record loses its history, is moved to NEEDSBUILD and a new
        empty BuildQueue entry is created for it.
        """

    def __getitem__(name):
        """Mapped to getBinaryPackageRelease."""

    def getBinaryPackageRelease(name):
        """Return the binary package from this build with the given name, or
        raise NotFoundError if no such package exists.
        """

    def createBinaryPackageRelease(binarypackagename, version,
                                   summary, description,
                                   binpackageformat, component,
                                   section, priority, shlibdeps,
                                   depends, recommends, suggests,
                                   conflicts, replaces, provides,
                                   essential, installedsize,
                                   architecturespecific):
        """Create a binary package release with the provided args, attached
        to this specific build.
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


class IHasBuildRecords(Interface):
    """An Object that has build records"""

    def getBuildRecords(build_state=None, name=None, pocket=None):
        """Return build records owned by the object.

        The optional 'build_state' argument selects build records in a specific
        state. Excludes the build records generated by Gina selecting
        not empty datebuilt when buildstate is FULLYBUILT. Order results
        by descending datebuilt, NEEDSBUILD records are special, they are
        ordered by decrescent BuildQueue.lastscore.If optional 'name'
        argument is passed try to find only those builds which the
        sourcepackagename matches (SQL LIKE).
        If pocket is specified return only builds for this pocket, otherwise
        return all.
        """
