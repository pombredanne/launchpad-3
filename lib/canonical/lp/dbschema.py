# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
#
"""Database schemas

Use them like this:

  from canonical.lp.dbschema import BugTaskImportance

  print "SELECT * FROM Bug WHERE Bug.importance='%d'" % BugTaskImportance.CRITICAL

"""
__metaclass__ = type

# MAINTAINER:
#
# When you add a new DBSchema subclass, add its name to the __all__ tuple
# below.
#
# If you do not do this, from canonical.lp.dbschema import * will not
# work properly, and the thing/lp:SchemaClass will not work properly.
__all__ = (
'ArchivePurpose',
'BinaryPackageFileType',
'BinaryPackageFormat',
'BugNominationStatus',
'BugAttachmentType',
'BugTrackerType',
'BugExternalReferenceType',
'BugInfestationStatus',
'BugRelationship',
'BugTaskImportance',
'BuildStatus',
'CveStatus',
'DistroSeriesStatus',
'MirrorContent',
'MirrorPulseType',
'MirrorSpeed',
'MirrorStatus',
'PackagePublishingPriority',
'PackagePublishingStatus',
'PackagePublishingPocket',
'ShippingRequestStatus',
'ShippingService',
'SourcePackageFileType',
'SourcePackageFormat',
'SourcePackageRelationships',
'SourcePackageUrgency',
'PackageUploadStatus',
'PackageUploadCustomFormat',
)

from canonical.lazr import DBEnumeratedType as DBSchema
from canonical.lazr import DBItem as Item


class BinaryPackageFormat(DBSchema):
    """Binary Package Format

    Launchpad tracks a variety of binary package formats. This schema
    documents the list of binary package formats that are supported
    in Launchpad.
    """

    DEB = Item(1, """
        Ubuntu Package

        This is the binary package format used by Ubuntu and all similar
        distributions. It includes dependency information to allow the
        system to ensure it always has all the software installed to make
        any new package work correctly.  """)

    UDEB = Item(2, """
        Ubuntu Installer Package

        This is the binary package format use by the installer in Ubuntu and
        similar distributions.  """)

    EBUILD = Item(3, """
        Gentoo Ebuild Package

        This is the Gentoo binary package format. While Gentoo is primarily
        known for being a build-it-from-source-yourself kind of
        distribution, it is possible to exchange binary packages between
        Gentoo systems.  """)

    RPM = Item(4, """
        RPM Package

        This is the format used by Mandrake and other similar distributions.
        It does not include dependency tracking information.  """)


class BugTrackerType(DBSchema):
    """The Types of BugTracker Supported by Launchpad

    This enum is used to differentiate between the different types of Bug
    Tracker that are supported by Malone in the Launchpad.
    """

    BUGZILLA = Item(1, """
        Bugzilla

        The godfather of open source bug tracking, the Bugzilla system was
        developed for the Mozilla project and is now in widespread use. It
        is big and ugly but also comprehensive.
        """)

    DEBBUGS = Item(2, """
        Debbugs

        The debbugs tracker is email based, and allows you to treat every
        bug like a small mailing list.
        """)

    ROUNDUP = Item(3, """
        Roundup

        Roundup is a lightweight, customisable and fast web/email based bug
        tracker written in Python.
        """)

    TRAC = Item(4, """
        Trac

        Trac is an enhanced wiki and issue tracking system for
        software development projects.
        """)

    SOURCEFORGE = Item(5, """
        SourceForge

        SourceForge is a project hosting service which includes bug,
        support and request tracking.
        """)

    MANTIS = Item(6, """
        Mantis

        Mantis is a web-based bug tracking system written in PHP.
        """)


class CveStatus(DBSchema):
    """The Status of this item in the CVE Database

    When a potential problem is reported to the CVE authorities they assign
    a CAN number to it. At a later stage, that may be converted into a CVE
    number. This indicator tells us whether or not the issue is believed to
    be a CAN or a CVE.
    """

    CANDIDATE = Item(1, """
        Candidate

        The vulnerability is a candidate, it has not yet been confirmed and
        given "Entry" status.
        """)

    ENTRY = Item(2, """
        Entry

        This vulnerability or threat has been assigned a CVE number, and is
        fully documented. It has been through the full CVE verification
        process.
        """)

    DEPRECATED = Item(3, """
        Deprecated

        This entry is deprecated, and should no longer be referred to in
        general correspondence. There is either a newer entry that better
        defines the problem, or the original candidate was never promoted to
        "Entry" status.
        """)


class DistroSeriesStatus(DBSchema):
    """Distribution Release Status

    A DistroSeries (warty, hoary, or grumpy for example) changes state
    throughout its development. This schema describes the level of
    development of the distroseries. The typical sequence for a
    distroseries is to progress from experimental to development to
    frozen to current to supported to obsolete, in a linear fashion.
    """

    EXPERIMENTAL = Item(1, """
        Experimental

        This distroseries contains code that is far from active
        release planning or management. Typically, distroseriess
        that are beyond the current "development" release will be
        marked as "experimental". We create those so that people
        have a place to upload code which is expected to be part
        of that distant future release, but which we do not want
        to interfere with the current development release.
        """)

    DEVELOPMENT = Item(2, """
        Active Development

        The distroseries that is under active current development
        will be tagged as "development". Typically there is only
        one active development release at a time. When that freezes
        and releases, the next release along switches from "experimental"
        to "development".
        """)

    FROZEN = Item(3, """
        Pre-release Freeze

        When a distroseries is near to release the administrators
        will freeze it, which typically means that new package uploads
        require significant review before being accepted into the
        release.
        """)

    CURRENT = Item(4, """
        Current Stable Release

        This is the latest stable release. Normally there will only
        be one of these for a given distribution.
        """)

    SUPPORTED = Item(5, """
        Supported

        This distroseries is still supported, but it is no longer
        the current stable release. In Ubuntu we normally support
        a distroseries for 2 years from release.
        """)

    OBSOLETE = Item(6, """
        Obsolete

        This distroseries is no longer supported, it is considered
        obsolete and should not be used on production systems.
        """)


class SourcePackageFormat(DBSchema):
    """Source Package Format

    Launchpad supports distributions that use source packages in a variety
    of source package formats. This schema documents the types of source
    package format that we understand.
    """

    DPKG = Item(1, """
        The DEB Format

        This is the source package format used by Ubuntu, Debian, Linspire
        and similar distributions.
        """)

    RPM = Item(2, """
        The RPM Format

        This is the format used by Red Hat, Mandrake, SUSE and other similar
        distributions.
        """)

    EBUILD = Item(3, """
        The Ebuild Format

        This is the source package format used by Gentoo.
        """)


class SourcePackageUrgency(DBSchema):
    """Source Package Urgency

    When a source package is released it is given an "urgency" which tells
    distributions how important it is for them to consider bringing that
    package into their archives. This schema defines the possible values
    for source package urgency.
    """

    LOW = Item(1, """
        Low Urgency

        This source package release does not contain any significant or
        important updates, it might be a cleanup or documentation update
        fixing typos and speling errors, or simply a minor upstream
        update.
        """)

    MEDIUM = Item(2, """
        Medium Urgency

        This package contains updates that are worth considering, such
        as new upstream or packaging features, or significantly better
        documentation.
        """)

    HIGH = Item(3, """
        Very Urgent

        This update contains updates that fix security problems or major
        system stability problems with previous releases of the package.
        Administrators should urgently evaluate the package for inclusion
        in their archives.
        """)

    EMERGENCY = Item(4, """
        Critically Urgent

        This release contains critical security or stability fixes that
        affect the integrity of systems using previous releases of the
        source package, and should be installed in the archive as soon
        as possible after appropriate review.
        """)


class SourcePackageFileType(DBSchema):
    """Source Package File Type

    Launchpad tracks files associated with a source package release. These
    files are stored on one of the inner servers, and a record is kept in
    Launchpad's database of the file's name and location. This schema
    documents the files we know about.
    """

    EBUILD = Item(1, """
        Ebuild File

        This is a Gentoo Ebuild, the core file that Gentoo uses as a source
        package release. Typically this is a shell script that pulls in the
        upstream tarballs, configures them and builds them into the
        appropriate locations.  """)

    SRPM = Item(2, """
        Source RPM

        This is a Source RPM, a normal RPM containing the needed source code
        to build binary packages. It would include the Spec file as well as
        all control and source code files.  """)

    DSC = Item(3, """
        DSC File

        This is a DSC file containing the Ubuntu source package description,
        which in turn lists the orig.tar.gz and diff.tar.gz files used to
        make up the package.  """)

    ORIG = Item(4, """
        Orig Tarball

        This file is an Ubuntu "orig" file, typically an upstream tarball or
        other lightly-modified upstreamish thing.  """)

    DIFF = Item(5, """
        Diff File

        This is an Ubuntu "diff" file, containing changes that need to be
        made to upstream code for the packaging on Ubuntu. Typically this
        diff creates additional directories with patches and documentation
        used to build the binary packages for Ubuntu.  """)

    TARBALL = Item(6, """
        Tarball

        This is a tarball, usually of a mixture of Ubuntu and upstream code,
        used in the build process for this source package.  """)


class PackageUploadStatus(DBSchema):
    """Distro Release Queue Status

    An upload has various stages it must pass through before becoming part
    of a DistroSeries. These are managed via the Upload table
    and related tables and eventually (assuming a successful upload into the
    DistroSeries) the effects are published via the PackagePublishing and
    SourcePackagePublishing tables.  """

    NEW = Item(0, """
        New

        This upload is either a brand-new source package or contains a
        binary package with brand new debs or similar. The package must sit
        here until someone with the right role in the DistroSeries checks
        and either accepts or rejects the upload. If the upload is accepted
        then entries will be made in the overrides tables and further
        uploads will bypass this state """)

    UNAPPROVED = Item(1, """
        Unapproved

        If a DistroSeries is frozen or locked out of ordinary updates then
        this state is used to mean that while the package is correct from a
        technical point of view; it has yet to be approved for inclusion in
        this DistroSeries. One use of this state may be for security
        releases where you want the security team of a DistroSeries to
        approve uploads.  """)

    ACCEPTED = Item(2, """
        Accepted

        An upload in this state has passed all the checks required of it and
        is ready to have its publishing records created.  """)

    DONE = Item(3, """
        Done

        An upload in this state has had its publishing records created if it
        needs them and is fully processed into the DistroSeries. This state
        exists so that a logging and/or auditing tool can pick up accepted
        uploads and create entries in a journal or similar before removing
        the queue item.  """)

    REJECTED = Item(4, """
        Rejected

        An upload which reaches this state has, for some reason or another
        not passed the requirements (technical or human) for entry into the
        DistroSeries it was targetting. As for the 'done' state, this state
        is present to allow logging tools to record the rejection and then
        clean up any subsequently unnecessary records.  """)


# If you change this (add items, change the meaning, whatever) search for
# the token ##CUSTOMFORMAT## e.g. database/queue.py or nascentupload.py and
# update the stuff marked with it.
class PackageUploadCustomFormat(DBSchema):
    """Custom formats valid for the upload queue

    An upload has various files potentially associated with it, from source
    package releases, through binary builds, to specialist upload forms such
    as a debian-installer tarball or a set of translations.
    """

    DEBIAN_INSTALLER = Item(0, """
        raw-installer

        A raw-installer file is a tarball. This is processed as a version
        of the debian-installer to be unpacked into the archive root.
        """)

    ROSETTA_TRANSLATIONS = Item(1, """
        raw-translations

        A raw-translations file is a tarball. This is passed to the rosetta
        import queue to be incorporated into that package's translations.
        """)

    DIST_UPGRADER = Item(2, """
        raw-dist-upgrader

        A raw-dist-upgrader file is a tarball. It is simply published into
        the archive.
        """)

    DDTP_TARBALL = Item(3, """
        raw-ddtp-tarball

        A raw-ddtp-tarball contains all the translated package description
        indexes for a component.
        """)


class PackagePublishingStatus(DBSchema):
    """Package Publishing Status

     A package has various levels of being published within a DistroSeries.
     This is important because of how new source uploads dominate binary
     uploads bit-by-bit. Packages (source or binary) enter the publishing
     tables as 'Pending', progress through to 'Published' eventually become
     'Superseded' and then become 'PendingRemoval'. Once removed from the
     DistroSeries the publishing record is also removed.
     """

    PENDING = Item(1, """
        Pending

        This [source] package has been accepted into the DistroSeries and
        is now pending the addition of the files to the published disk area.
        In due course, this source package will be published.
        """)

    PUBLISHED = Item(2, """
        Published

        This package is currently published as part of the archive for that
        distroseries. In general there will only ever be one version of any
        source/binary package published at any one time. Once a newer
        version becomes published the older version is marked as superseded.
        """)

    SUPERSEDED = Item(3, """
        Superseded

        When a newer version of a [source] package is published the existing
        one is marked as "superseded".
        """)

    DELETED = Item(4, """
        Deleted

        When a publication was "deleted" from the archive by user request.
        Records in this state contain a reference to the Launchpad user
        responsible for the deletion and a text comment with the removal
        reason.
        """)


class PackagePublishingPriority(DBSchema):
    """Package Publishing Priority

    Binary packages have a priority which is related to how important
    it is to have that package installed in a system. Common priorities
    range from required to optional and various others are available.
    """

    REQUIRED = Item(50, """
        Required

        This priority indicates that the package is required. This priority
        is likely to be hard-coded into various package tools. Without all
        the packages at this priority it may become impossible to use dpkg.
        """)

    IMPORTANT = Item(40, """
        Important

        If foo is in a package; and "What is going on?! Where on earth is
        foo?!?!" would be the reaction of an experienced UNIX hacker were
        the package not installed, then the package is important.
        """)

    STANDARD = Item(30, """
        Standard

        Packages at this priority are standard ones you can rely on to be in
        a distribution. They will be installed by default and provide a
        basic character-interface userland.
        """)

    OPTIONAL = Item(20, """
        Optional

        This is the software you might reasonably want to install if you did
        not know what it was or what your requiredments were. Systems such
        as X or TeX will live here.
        """)

    EXTRA = Item(10, """
        Extra

        This contains all the packages which conflict with those at the
        other priority levels; or packages which are only useful to people
        who have very specialised needs.
        """)


class PackagePublishingPocket(DBSchema):
    """Package Publishing Pocket

    A single distroseries can at its heart be more than one logical
    distroseries as the tools would see it. For example there may be a
    distroseries called 'hoary' and a SECURITY pocket subset of that would
    be referred to as 'hoary-security' by the publisher and the distro side
    tools.
    """

    RELEASE = Item(0, """
        Release

        The package versions that were published
        when the distribution release was made.
        For releases that are still under development,
        packages are published here only.
        """)

    SECURITY = Item(10, """
        Security

        Package versions containing security fixes for the released
        distribution.
        It is a good idea to have security updates turned on for your system.
        """)

    UPDATES = Item(20, """
        Updates

        Package versions including new features after the distribution
        release has been made.
        Updates are usually turned on by default after a fresh install.
        """)

    PROPOSED = Item(30, """
        Proposed

        Package versions including new functions that should be widely
        tested, but that are not yet part of a default installation.
        People who "live on the edge" will test these packages before they
        are accepted for use in "Updates".
        """)

    BACKPORTS = Item(40, """
        Backports

        Backported packages.
        """)


class SourcePackageRelationships(DBSchema):
    """Source Package Relationships

    Launchpad tracks many source packages. Some of these are related to one
    another. For example, a source package in Ubuntu called "apache2" might
    be related to a source package in Mandrake called "httpd". This schema
    defines the relationships that Launchpad understands.
    """

    REPLACES = Item(1, """
        Replaces

        The subject source package was designed to replace the object source
        package.  """)

    REIMPLEMENTS = Item(2, """
        Reimplements

        The subject source package is a completely new packaging of the same
        underlying products as the object package.  """)

    SIMILARTO = Item(3, """
        Similar To

        The subject source package is similar, in that it packages software
        that has similar functionality to the object package.  For example,
        postfix and exim4 would be "similarto" one another.  """)

    DERIVESFROM = Item(4, """
        Derives From

        The subject source package derives from and tracks the object source
        package. This means that new uploads of the object package should
        trigger a notification to the maintainer of the subject source
        package.  """)

    CORRESPONDSTO = Item(5, """
        Corresponds To

        The subject source package includes the same products as the object
        source package, but for a different distribution. For example, the
        "apache2" Ubuntu package "correspondsto" the "httpd2" package in Red
        Hat.  """)


class BinaryPackageFileType(DBSchema):
    """Binary Package File Type

    Launchpad handles a variety of packaging systems and binary package
    formats. This schema documents the known binary package file types.
    """

    DEB = Item(1, """
        DEB Format

        This format is the standard package format used on Ubuntu and other
        similar operating systems.
        """)

    UDEB = Item(3, """
        UDEB Format

        This format is the standard package format used on Ubuntu and other
        similar operating systems for the installation system.
        """)

    RPM = Item(2, """
        RPM Format

        This format is used on mandrake, Red Hat, Suse and other similar
        distributions.
        """)


class BugInfestationStatus(DBSchema):
    """Bug Infestation Status

    Malone is the bug tracking application that is part of Launchpad. It
    tracks the status of bugs in different distributions as well as
    upstream. This schema documents the kinds of infestation of a bug
    in a coderelease.
    """

    AFFECTED = Item(60, """
        Affected

        It is believed that this bug affects that coderelease. The
        verifiedby field will indicate whether that has been verified
        by a package maintainer.
        """)

    DORMANT = Item(50, """
        Dormant

        The bug exists in the code of this coderelease, but it is dormant
        because that codepath is unused in this release.
        """)

    VICTIMIZED = Item(40, """
        Victimized

        This code release does not actually contain the buggy code, but
        it is affected by the bug nonetheless because of the way it
        interacts with the products or packages that are actually buggy.
        Often users will report a bug against the package which displays
        the symptoms when the bug itself lies elsewhere.
        """)

    FIXED = Item(30, """
        Fixed

        It is believed that the bug is actually fixed in this release of code.
        Setting the "fixed" flag allows us to generate lists of bugs fixed
        in a release.
        """)

    UNAFFECTED = Item(20, """
        Unaffected

        It is believed that this bug does not infest this release of code.
        """)

    UNKNOWN = Item(10, """
        Unknown

        We don't know if this bug infests that coderelease.
        """)


class BugNominationStatus(DBSchema):
    """Bug Nomination Status

    The status of the decision to fix a bug in a specific release.
    """

    PROPOSED = Item(10, """
        Nominated

        This nomination hasn't yet been reviewed, or is still under
        review.
        """)

    APPROVED = Item(20, """
        Approved

        The release management team has approved fixing the bug for this
        release.
        """)

    DECLINED = Item(30, """
        Declined

        The release management team has declined fixing the bug for this
        release.
        """)


class BugTaskImportance(DBSchema):
    """Bug Task Importance

    Importance is used by developers and their managers to indicate how
    important fixing a bug is. Importance is typically a combination of the
    harm caused by the bug, and how often it is encountered.
    """

    UNKNOWN = Item(999, """
        Unknown

        The severity of this bug task is unknown.
        """)

    CRITICAL = Item(50, """
        Critical

        This bug is essential to fix as soon as possible. It affects
        system stability, data integrity and / or remote access
        security.
        """)

    HIGH = Item(40, """
        High

        This bug needs urgent attention from the maintainer or
        upstream. It affects local system security or data integrity.
        """)

    MEDIUM = Item(30, """
        Medium

        This bug warrants an upload just to fix it, but can be put
        off until other major or critical bugs have been fixed.
        """)

    LOW = Item(20, """
        Low

        This bug does not warrant an upload just to fix it, but
        should if possible be fixed when next the maintainer does an
        upload. For example, it might be a typo in a document.
        """)

    WISHLIST = Item(10, """
        Wishlist

        This is not a bug, but is a request for an enhancement or
        new feature that does not yet exist in the package. It does
        not affect system stability, it might be a usability or
        documentation fix.
        """)

    UNDECIDED = Item(5, """
        Undecided

        A relevant developer or manager has not yet decided how
        important this bug is.
        """)


class BugExternalReferenceType(DBSchema):
    """Bug External Reference Type

    Malone allows external information references to be attached to
    a bug. This schema lists the known types of external references.
    """

    CVE = Item(1, """
        CVE Reference

        This external reference is a CVE number, which means it
        exists in the CVE database of security bugs.
        """)

    URL = Item(2, """
        URL

        This external reference is a URL. Typically that means it
        is a reference to a web page or other internet resource
        related to the bug.
        """)


class BugRelationship(DBSchema):
    """Bug Relationship

    Malone allows for rich relationships between bugs to be specified,
    and this schema lists the types of relationships supported.
    """

    RELATED = Item(1, """
        Related Bug

        This indicates that the subject and object bugs are related in
        some way. The order does not matter. When displaying one bug, it
        would be appropriate to list the other bugs which are related to it.
        """)


class BugAttachmentType(DBSchema):
    """Bug Attachment Type.

    An attachment to a bug can be of different types, since for example
    a patch is more important than a screenshot. This schema describes the
    different types.
    """

    PATCH = Item(1, """
        Patch

        This is a patch that potentially fixes the bug.
        """)

    UNSPECIFIED = Item(2, """
        Unspecified

        This is everything else. It can be a screenshot, a log file, a core
        dump, etc. Basically anything that adds more information to the bug.
        """)


class BuildStatus(DBSchema):
    """Build status type

    Builds exist in the database in a number of states such as 'complete',
    'needs build' and 'dependency wait'. We need to track these states in
    order to correctly manage the autobuilder queues in the BuildQueue table.
    """

    NEEDSBUILD = Item(0, """
        Needs building

        Build record is fresh and needs building. Nothing is yet known to
        block this build and it is a candidate for building on any free
        builder of the relevant architecture
        """)

    FULLYBUILT = Item(1, """
        Successfully built

        Build record is an historic account of the build. The build is complete
        and needs no further work to complete it. The build log etc are all
        in place if available.
        """)

    FAILEDTOBUILD = Item(2, """
        Failed to build

        Build record is an historic account of the build. The build failed and
        cannot be automatically retried. Either a new upload will be needed
        or the build will have to be manually reset into 'NEEDSBUILD' when
        the issue is corrected
        """)

    MANUALDEPWAIT = Item(3, """
        Dependency wait

        Build record represents a package whose build dependencies cannot
        currently be satisfied within the relevant DistroArchRelease. This
        build will have to be manually given back (put into 'NEEDSBUILD') when
        the dependency issue is resolved.
        """)

    CHROOTWAIT = Item(4, """
        Chroot problem

        Build record represents a build which needs a chroot currently known
        to be damaged or bad in some way. The buildd maintainer will have to
        reset all relevant CHROOTWAIT builds to NEEDSBUILD after the chroot
        has been fixed.
        """)

    SUPERSEDED = Item(5, """
        Build for superseded Source

        Build record represents a build which never got to happen because the
        source package release for the build was superseded before the job
        was scheduled to be run on a builder. Builds which reach this state
        will rarely if ever be reset to any other state.
        """)

    BUILDING = Item(6, """
        Currently building

        Build record represents a build which is being build by one of the
        available builders.
        """)

    FAILEDTOUPLOAD = Item(7, """
        Failed to upload

        Build record is an historic account of a build that could not be
        uploaded correctly. It's mainly genereated by failures in
        process-upload which quietly rejects the binary upload resulted
        by the build procedure.
        In those cases all the build historic information will be stored (
        buildlog, datebuilt, duration, builder, etc) and the buildd admins
        will be notified via process-upload about the reason of the rejection.
        """)


class ArchivePurpose(DBSchema):
    """The purpose, or type, of an archive.

    A distribution can be associated with different archives and this
    schema item enumerates the different archive types and their purpose.
    For example, old distro releases may need to be obsoleted so their
    archive would be OBSOLETE_ARCHIVE.
    """

    PRIMARY = Item(1, """
        Primary Archive

        This is the primary Ubuntu archive.
        """)

    PPA = Item(2, """
        PPA Archive

        This is a Personal Package Archive.
        """)

    EMBARGOED = Item(3, """
        Embargoed Archive

        This is the archive for embargoed packages.
        """)

    PARTNER = Item(4, """
        Partner Archive

        This is the archive for partner packages.
        """)

    OBSOLETE = Item(5, """
        Obsolete Archive

        This is the archive for obsolete packages.
        """)

