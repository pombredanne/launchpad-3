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
'BountyDifficulty',
'BountyStatus',
'BranchReviewStatus',
'BugBranchStatus',
'BugNominationStatus',
'BugAttachmentType',
'BugTrackerType',
'BugExternalReferenceType',
'BugInfestationStatus',
'BugRelationship',
'BugTaskImportance',
'BuildStatus',
'CodereleaseRelationships',
'CodeImportReviewStatus',
'CveStatus',
'DistroSeriesStatus',
'ImportTestStatus',
'ImportStatus',
'MirrorContent',
'MirrorPulseType',
'MirrorSpeed',
'MirrorStatus',
'PackagePublishingPriority',
'PackagePublishingStatus',
'PackagePublishingPocket',
'PackagingType',
'PersonalStanding',
'PollAlgorithm',
'PollSecrecy',
'PostedMessageStatus',
'ProjectRelationship',
'ProjectStatus',
'RevisionControlSystems',
'RosettaImportStatus',
'RosettaTranslationOrigin',
'ShipItArchitecture',
'ShipItDistroSeries',
'ShipItFlavour',
'ShippingRequestStatus',
'ShippingService',
'SourcePackageFileType',
'SourcePackageFormat',
'SourcePackageRelationships',
'SourcePackageUrgency',
'SpecificationImplementationStatus',
'SpecificationFilter',
'SpecificationGoalStatus',
'SpecificationLifecycleStatus',
'SpecificationPriority',
'SpecificationSort',
'SpecificationDefinitionStatus',
'SprintSpecificationStatus',
'TextDirection',
'TranslationFileFormat',
'TranslationPriority',
'TranslationPermission',
'TranslationValidationStatus',
'PackageUploadStatus',
'PackageUploadCustomFormat',
'UpstreamFileType',
'UpstreamReleaseVersionStyle',
)

#from canonical.launchpad.webapp.enum import DBSchema
#from canonical.launchpad.webapp.enum import DBSchemaItem as Item

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


class ImportTestStatus(DBSchema):
    """An Arch Import Autotest Result

    This enum tells us whether or not a sourcesource has been put through an
    attempted import.
    """

    NEW = Item(0, """
        Untested

        The sourcesource has not yet been tested by the autotester.
        """)

    FAILED = Item(1, """
        Failed

        The sourcesource failed to import cleanly.
        """)

    SUCCEEDED = Item(2, """
        Succeeded

        The sourcesource was successfully imported by the autotester.
        """)

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


class ProjectStatus(DBSchema):
    """A Project Status

    This is an enum of the values that Project.status can assume.
    Essentially it indicates whether or not this project has been reviewed,
    and if it has whether or not it passed review and should be considered
    active.
    """

    NEW = Item(1, """
        New

        This project is new and has not been reviewed.
        """)

    ACTIVE = Item(2, """
        Active

        This Project has been reviewed and is considered active in the
        launchpad.""")

    DISABLED = Item(3, """
        Disabled

        This project has been reviewed, and has been disabled. Typically
        this is because the contents appear to be bogus. Such a project
        should not show up in searches etc.""")


class PackagingType(DBSchema):
    """Source packages.

    Source packages include software from one or more Upstream open source
    projects. This schema shows the relationship between a source package
    and the upstream open source products that it might incorporate. This
    schema is used in the Packaging table.
    """

    PRIME = Item(1, """
        Primary Product

        This is the primary product packaged in this source package. For
        example, a source package "apache2" would have a "prime" Packaging
        relationship with the "apache2" product from the Apache Project.
        The product and package don't have to have the same name.
        """)

    INCLUDES = Item(2, """
        SourcePackage Includes Product

        This source package includes some part or all of the product. For
        example, the "cadaver" source package has an "includes" Packaging
        relationship with the libneon product.
        """)


class BugBranchStatus(DBSchema):
    """The status of a bugfix branch."""

    ABANDONED = Item(10, """
        Abandoned Attempt

        A fix for this bug is no longer being worked on in this
        branch.
        """)

    INPROGRESS = Item(20, """
        Fix In Progress

        Development to fix this bug is currently going on in this
        branch.
        """)

    FIXAVAILABLE = Item(30, """
        Fix Available

        This branch contains a potentially useful fix for this bug.
        """)

    BESTFIX = Item(40, """
        Best Fix Available

        This branch contains a fix agreed upon by the community as
        being the best available branch from which to merge to fix
        this bug.
        """)


class ProjectRelationship(DBSchema):
    """Project Relationship

    Launchpad tracks different open source projects, and the relationships
    between them. This schema is used to describe the relationship between
    two open source projects.
    """

    AGGREGATES = Item(1, """
        Subject Project Aggregates Object Project

        Some open source projects are in fact an aggregation of several
        other projects. For example, the Gnome Project aggregates
        Gnumeric, Abiword, EOG, and many other open source projects.
        """)

    SIMILAR = Item(2, """
        Subject Project is Similar to Object Project

        Often two different groups will start open source projects
        that are similar to one another. This relationship is used
        to describe projects that are similar to other projects in
        the system.
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


class UpstreamFileType(DBSchema):
    """Upstream File Type

    When upstream open source project release a product they will
    include several files in the release. All of these files are
    stored in Launchpad (we throw nothing away ;-). This schema
    gives the type of files that we know about.
    """

    CODETARBALL = Item(1, """
        Code Release Tarball

        This file contains code in a compressed package like
        a tar.gz or tar.bz or .zip file.
        """)

    README = Item(2, """
        README File

        This is a README associated with the upstream
        release. It might be in .txt or .html format, the
        filename would be an indicator.
        """)

    RELEASENOTES = Item(3, """
        Release Notes

        This file contains the release notes of the new
        upstream release. Again this could be in .txt or
        in .html format.
        """)

    CHANGELOG = Item(4, """
        ChangeLog File

        This file contains information about changes in this
        release from the previous release in the series. This
        is usually not a detailed changelog, but a high-level
        summary of major new features and fixes.
        """)

    INSTALLER = Item(5, """
        Installer file

        This file contains an installer for a product.  It may
        be a Debian package, an RPM file, an OS X disk image, a
        Windows installer, or some other type of installer.
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


class SpecificationImplementationStatus(DBSchema):
    # Note that some of the states associated with this schema correlate to
    # a "not started" definition. See Specification.started_clause for
    # further information, and make sure that it is updated (together with
    # the relevant database checks) if additional states are added that are
    # also "not started".
    """Specification Delivery Status

    This tracks the implementation or delivery of the feature being
    specified. The status values indicate the progress that is being made in
    the actual coding or configuration that is needed to realise the
    feature.
    """
    # NB this state is considered "not started"
    UNKNOWN = Item(0, """
        Unknown

        We have no information on the implementation of this feature.
        """)

    # NB this state is considered "not started"
    NOTSTARTED = Item(5, """
        Not started

        No work has yet been done on the implementation of this feature.
        """)

    # NB this state is considered "not started"
    DEFERRED = Item(10, """
        Deferred

        There is no chance that this feature will actually be delivered in
        the targeted release. The specification has effectively been
        deferred to a later date of implementation.
        """)

    NEEDSINFRASTRUCTURE = Item(40, """
        Needs Infrastructure

        Work cannot proceed, because the feature depends on
        infrastructure (servers, databases, connectivity, system
        administration work) that has not been supplied.
        """)

    BLOCKED = Item(50, """
        Blocked

        Work cannot proceed on this specification because it depends on
        a separate feature that has not yet been implemented.
        (The specification for that feature should be listed as a blocker of
        this one.)
        """)

    STARTED = Item(60, """
        Started

        Work has begun, but has not yet been published
        except as informal branches or patches. No indication is given as to
        whether or not this work will be completed for the targeted release.
        """)

    SLOW = Item(65, """
        Slow progress

        Work has been slow on this item, and it has a high risk of not being
        delivered on time. Help is wanted with the implementation.
        """)

    GOOD = Item(70, """
        Good progress

        The feature is considered on track for delivery in the targeted release.
        """)

    BETA = Item(75, """
        Beta Available

        A beta version, implementing substantially all of the feature,
        has been published for widespread testing in personal package
        archives or a personal release. The code is not yet in the
        main archive or mainline branch. Testing and feedback are solicited.
        """)

    NEEDSREVIEW = Item(80, """
        Needs Code Review

        The developer is satisfied that the feature has been well
        implemented. It is now ready for review and final sign-off,
        after which it will be marked implemented or deployed.
        """)

    AWAITINGDEPLOYMENT = Item(85, """
        Deployment

        The implementation has been done, and can be deployed in the production
        environment, but this has not yet been done by the system
        administrators. (This status is typically used for Web services where
        code is not released but instead is pushed into production.
        """)

    IMPLEMENTED = Item(90, """
        Implemented

        This functionality has been delivered for the targeted release, the
        code has been uploaded to the main archives or committed to the
        targeted product series, and no further work is necessary.
        """)

    INFORMATIONAL = Item(95, """
        Informational

        This specification is informational, and does not require
        any implementation.
        """)


class SpecificationLifecycleStatus(DBSchema):
    """The current "lifecycle" status of a specification. Specs go from
    NOTSTARTED, to STARTED, to COMPLETE.
    """

    NOTSTARTED = Item(10, """
        Not started

        No work has yet been done on this feature.
        """)

    STARTED = Item(20, """
        Started

        This feature is under active development.
        """)

    COMPLETE = Item(30, """
        Complete

        This feature has been marked "complete" because no further work is
        expected. Either the feature is done, or it has been abandoned.
        """)


class SpecificationPriority(DBSchema):
    """The Priority with a Specification must be implemented.

    This enum is used to prioritise work.
    """

    NOTFORUS = Item(0, """
        Not

        This feature has been proposed but the project leaders have decided
        that it is not appropriate for inclusion in the mainline codebase.
        See the status whiteboard or the
        specification itself for the rationale for this decision. Of course,
        you are welcome to implement it in any event and publish that work
        for consideration by the community and end users, but it is unlikely
        to be accepted by the mainline developers.
        """)

    UNDEFINED = Item(5, """
        Undefined

        This feature has recently been proposed and has not yet been
        evaluated and prioritised by the project leaders.
        """)

    LOW = Item(10, """
        Low

        We would like to have it in the
        code, but it's not on any critical path and is likely to get bumped
        in favour of higher-priority work. The idea behind the specification
        is sound and the project leaders would incorporate this
        functionality if the work was done. In general, "low" priority
        specifications will not get core resources assigned to them.
        """)

    MEDIUM = Item(50, """
        Medium

        The project developers will definitely get to this feature,
        but perhaps not in the next major release or two.
        """)

    HIGH = Item(70, """
        High

        Strongly desired by the project leaders.
        The feature will definitely get review time, and contributions would
        be most effective if directed at a feature with this priority.
        """)

    ESSENTIAL = Item(90, """
        Essential

        The specification is essential for the next release, and should be
        the focus of current development. Use this state only for the most
        important of all features.
        """)


class SpecificationFilter(DBSchema):
    """An indicator of the kinds of specifications that should be returned
    for a listing of specifications.

    This is used by browser classes that are generating a list of
    specifications for a person, or product, or project, to indicate what
    kinds of specs they want returned. The different filters can be OR'ed so
    that multiple pieces of information can be used for the filter.
    """
    ALL = Item(0, """
        All

        This indicates that the list should simply include ALL
        specifications for the underlying object (person, product etc).
        """)

    COMPLETE = Item(5, """
        Complete

        This indicates that the list should include only the complete
        specifications for this object.
        """)

    INCOMPLETE = Item(10, """
        Incomplete

        This indicates that the list should include the incomplete items
        only. The rules for determining if a specification is incomplete are
        complex, depending on whether or not the spec is informational.
        """)

    INFORMATIONAL = Item(20, """
        Informational

        This indicates that the list should include only the informational
        specifications.
        """)

    PROPOSED = Item(30, """
        Proposed

        This indicates that the list should include specifications that have
        been proposed as goals for the underlying objects, but not yet
        accepted or declined.
        """)

    DECLINED = Item(40, """
        Declined

        This indicates that the list should include specifications that were
        declined as goals for the underlying productseries or distroseries.
        """)

    ACCEPTED = Item(50, """
        Accepted

        This indicates that the list should include specifications that were
        accepted as goals for the underlying productseries or distroseries.
        """)

    VALID = Item(55, """
        Valid

        This indicates that the list should include specifications that are
        not obsolete or superseded.
        """)

    CREATOR = Item(60, """
        Creator

        This indicates that the list should include specifications that the
        person registered in Launchpad.
        """)

    ASSIGNEE = Item(70, """
        Assignee

        This indicates that the list should include specifications that the
        person has been assigned to implement.
        """)

    APPROVER = Item(80, """
        Approver

        This indicates that the list should include specifications that the
        person is supposed to review and approve.
        """)

    DRAFTER = Item(90, """
        Drafter

        This indicates that the list should include specifications that the
        person is supposed to draft. The drafter is usually only needed
        during spec sprints when there's a bottleneck on guys who are
        assignees for many specs.
        """)

    SUBSCRIBER = Item(100, """
        Subscriber

        This indicates that the list should include all the specifications
        to which the person has subscribed.
        """)

    FEEDBACK = Item(110, """
        Feedback

        This indicates that the list should include all the specifications
        which the person has been asked to provide specific feedback on.
        """)


class SpecificationSort(DBSchema):
    """A preferred sorting scheme for the results of a query about
    specifications.

    This is usually used in interfaces which ask for a filtered list of
    specifications, so that you can tell which specifications you would
    expect to see first.

    NB: this is not really a "dbschema" in that is doesn't map to an int
    that is stored in the db. In future, we will likely have a different way
    of defining such enums.
    """
    DATE = Item(10, """
        Date

        This indicates a preferred sort order of date of creation, newest
        first.
        """)

    PRIORITY = Item(20, """
        Priority

        This indicates a preferred sort order of priority (highest first)
        followed by status. This is the default sort order when retrieving
        specifications from the system.
        """)


class SpecificationDefinitionStatus(DBSchema):
    """The current status of a Specification

    This enum tells us whether or not a specification is approved, or still
    being drafted, or implemented, or obsolete in some way. The ordinality
    of the values is important, it's the order (lowest to highest) in which
    we probably want them displayed by default.
    """

    APPROVED = Item(10, """
        Approved

        The project team believe that the specification is ready to be
        implemented, without substantial issues being encountered.
        """)

    PENDINGAPPROVAL = Item(15, """
        Pending Approval

        Reviewed and considered ready for final approval.
        The reviewer believes the specification is clearly written,
        and adequately addresses all important issues that will
        be raised during implementation.
        """)

    PENDINGREVIEW = Item(20, """
        Review

        Has been put in a reviewer's queue. The reviewer will
        assess it for clarity and comprehensiveness, and decide
        whether further work is needed before the spec can be considered for
        actual approval.
        """)

    DRAFT = Item(30, """
        Drafting

        The specification is actively being drafted, with a drafter in place
        and frequent revision occurring.
        Do not park specs in the "drafting" state indefinitely.
        """)

    DISCUSSION = Item(35, """
        Discussion

        Still needs active discussion, at a sprint for example.
        """)

    NEW = Item(40, """
        New

        No thought has yet been given to implementation strategy, dependencies,
        or presentation/UI issues.
        """)

    SUPERSEDED = Item(60, """
        Superseded

        Still interesting, but superseded by a newer spec or set of specs that
        clarify or describe a newer way to implement the desired feature.
        Please use the newer specs and not this one.
        """)

    OBSOLETE = Item(70, """
        Obsolete

        The specification has been obsoleted, probably because it was decided
        against. People should not put any effort into implementing it.
        """)


class SpecificationGoalStatus(DBSchema):
    """The target status for this specification

    This enum allows us to show whether or not the specification has been
    approved or declined as a target for the given product series or distro
    release.
    """

    ACCEPTED = Item(10, """
        Accepted

        The drivers have confirmed that this specification is targeted to
        the stated distribution release or product series.
        """)

    DECLINED = Item(20, """
        Declined

        The drivers have decided not to accept this specification as a goal
        for the stated distribution release or product series.
        """)

    PROPOSED = Item(30, """
        Proposed

        This spec has been submitted as a potential goal for the stated
        product series or distribution release, but the drivers have not yet
        accepted or declined that goal.
        """)


class SprintSpecificationStatus(DBSchema):
    """The current approval status of the spec on this sprint's agenda.

    This enum allows us to know whether or not the meeting admin team has
    agreed to discuss an item.
    """

    ACCEPTED = Item(10, """
        Accepted

        The meeting organisers have confirmed this topic for the meeting
        agenda.
        """)

    DECLINED = Item(20, """
        Declined

        This spec has been declined from the meeting agenda
        because of a lack of available resources, or uncertainty over
        the specific requirements or outcome desired.
        """)

    PROPOSED = Item(30, """
        Proposed

        This spec has been submitted for consideration by the meeting
        organisers. It has not yet been accepted or declined for the
        agenda.
        """)


class ImportStatus(DBSchema):
    """This schema describes the states that a SourceSource record can take
    on."""

    DONTSYNC = Item(1, """
        Do Not Import

        Launchpad will not attempt to make a Bazaar import.
        """)

    TESTING = Item(2, """
        Testing

        Launchpad has not yet attempted this import. The vcs-imports operator
        will review the source details and either mark the series \"Do not
        sync\", or perform a test import. If the test import is successful, a
        public import will be created. After the public import completes, it
        will be updated automatically.
        """)

    TESTFAILED = Item(3, """
        Test Failed

        The test import has failed. We will do further tests, and plan to
        complete this import eventually, but it may take a long time. For more
        details, you can ask on the launchpad-users@canonical.com mailing list
        or on IRC in the #launchpad channel on irc.freenode.net.
        """)

    AUTOTESTED = Item(4, """
        Test Successful

        The test import was successful. The vcs-imports operator will lock the
        source details for this series and perform a public Bazaar import.
        """)

    PROCESSING = Item(5, """
        Processing

        The public Bazaar import is being created. When it is complete, a
        Bazaar branch will be published and updated automatically. The source
        details for this series are locked and can only be modified by
        vcs-imports members and Launchpad administrators.
        """)

    SYNCING = Item(6, """
        Online

        The Bazaar import is published and automatically updated to reflect the
        upstream revision control system. The source details for this series
        are locked and can only be modified by vcs-imports members and
        Launchpad administrators.
        """)

    STOPPED = Item(7, """
        Stopped

        The Bazaar import has been suspended and is no longer updated. The
        source details for this series are locked and can only be modified by
        vcs-imports members and Launchpad administrators.
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


class TranslationPriority(DBSchema):
    """Translation Priority

    Translations in Rosetta can be assigned a priority. This is used in a
    number of places. The priority stored on the translation itself is set
    by the upstream project maintainers, and used to identify the
    translations they care most about. For example, if Apache were nearing a
    big release milestone they would set the priority on those POTemplates
    to 'high'. The priority is also used by TranslationEfforts to indicate
    how important that POTemplate is to the effort. And lastly, an
    individual translator can set the priority on his personal subscription
    to a project, to determine where it shows up on his list.  """

    HIGH = Item(1, """
        High

        This translation should be shown on any summary list of translations
        in the relevant context. For example, 'high' priority projects show
        up on the home page of a TranslationEffort or Project in Rosetta.
        """)

    MEDIUM = Item(2, """
        Medium

        A medium priority POTemplate should be shown on longer lists and
        dropdowns lists of POTemplates in the relevant context.  """)

    LOW = Item(3, """
        Low

        A low priority POTemplate should only show up if a comprehensive
        search or complete listing is requested by the user.  """)


class TranslationPermission(DBSchema):
    """Translation Permission System

    Projects, products and distributions can all have content that needs to
    be translated. In this case, Launchpad Translations allows them to decide
    how open they want that translation process to be. At one extreme, anybody
    can add or edit any translation, without review. At the other, only the
    designated translator for that group in that language can add or edit its
    translation files. This schema enumerates the options.
    """

    OPEN = Item(1, """
        Open

        This group allows totally open access to its translations. Any
        logged-in user can add or edit translations in any language, without
        any review.""")

    STRUCTURED = Item(20, """
        Structured

        This group has designated translators for certain languages. In
        those languages, people who are not designated translators can only
        make suggestions. However, in languages which do not yet have a
        designated translator, anybody can edit the translations directly,
        with no further review.""")

    RESTRICTED = Item(100, """
        Restricted

        This group allows only designated translators to edit the
        translations of its files. You can become a designated translator
        either by joining an existing language translation team for this
        project, or by getting permission to start a new team for a new
        language. People who are not designated translators can still make
        suggestions for new translations, but those suggestions need to be
        reviewed before being accepted by the designated translator.""")

    CLOSED = Item(200, """
        Closed

        This group allows only designated translators to edit or add
        translations. You can become a designated translator either by
        joining an existing language translation team for this
        project, or by getting permission to start a new team for a new
        language. People who are not designated translators will not be able
        to add suggestions.""")


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
        one is marked as "superseded".  """)

    PENDINGREMOVAL = Item(6, """
        PendingRemoval

        Once a package is ready to be removed from the archive is is put
        into this state and the removal will be acted upon when a period of
        time has passed. When the package is moved to this state the
        scheduleddeletiondate column is filled out. When that date has
        passed the archive maintainance tools will remove the package from
        the on-disk archive and remove the publishing record.  """)

    REMOVED = Item(7, """
        Removed

        Once a package is removed from the archive, its publishing record
        is set to this status. This means it won't show up in the SPP view
        and thus will not be considered in most queries about source
        packages in distroseriess. """)


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


class BountyDifficulty(DBSchema):
    """Bounty Difficulty

    An indicator of the difficulty of a particular bounty."""

    TRIVIAL = Item(10, """
        Trivial

        This bounty requires only very basic skills to complete the task. No
        real domain knowledge is required, only simple system
        administration, writing or configuration skills, and the ability to
        publish the work.""")

    BASIC = Item(20, """
        Basic

        This bounty requires some basic programming skills, in a high level
        language like Python or C# or... BASIC. However, the project is
        being done "standalone" and so no knowledge of existing code is
        required.""")

    STRAIGHTFORWARD = Item(30, """
        Straightforward

        This bounty is easy to implement but does require some broader
        understanding of the framework or application within which the work
        must be done.""")

    NORMAL = Item(50, """
        Normal

        This bounty requires a moderate amount of programming skill, in a
        high level language like HTML, CSS, JavaScript, Python or C#. It is
        an extension to an existing application or package so the work will
        need to follow established project coding standards.""")

    CHALLENGING = Item(60, """
        Challenging

        This bounty requires knowledge of a low-level programming language
        such as C or C++.""")

    DIFFICULT = Item(70, """
        Difficult

        This project requires knowledge of a low-level programming language
        such as C or C++ and, in addition, requires extensive knowledge of
        an existing codebase into which the work must fit.""")

    VERYDIFFICULT = Item(90, """
        Very Difficult

        This project requires exceptional programming skill and knowledge of
        very low level programming environments, such as assembly language.""")

    EXTREME = Item(100, """
        Extreme

        In order to complete this work, detailed knowledge of an existing
        project is required, and in addition the work itself must be done in
        a low-level language like assembler or C on multiple architectures.""")


class BountyStatus(DBSchema):
    """Bounty Status

    An indicator of the status of a particular bounty. This can be edited by
    the bounty owner or reviewer."""

    OPEN = Item(1, """
        Open

        This bounty is open. People are still welcome to contact the creator
        or reviewer of the bounty, and submit their work for consideration
        for the bounty.""")

    WITHDRAWN = Item(9, """
        Withdrawn

        This bounty has been withdrawn.
        """)

    CLOSED = Item(10, """
        Closed

        This bounty is closed. No further submissions will be considered.
        """)


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


class CodereleaseRelationships(DBSchema):
    """Coderelease Relationships

    Code releases are both upstream releases and distribution source package
    releases, and in this schema we document the relationships that Launchpad
    understands between these two.
    """

    PACKAGES = Item(1, """
        Packages

        The subject is a distribution packing of the object. For example,
        apache2-2.0.48-1 "packages" the upstream apache2.0.48.tar.gz.
        """)

    REPLACES = Item(2, """
        Replaces

        A subsequent release in the same product series typically
        "replaces" the prior release. For example, apache2.0.48
        "replaces" apache2.0.47. Similarly, within the distribution
        world, apache-2.0.48-3ubuntu2 "replaces" apache2-2.0.48-3ubuntu2.
        """)

    DERIVESFROM = Item(3, """
        Derives From

        The subject package derives from the object package. It is common
        for distributions to build on top of one another's work, creating
        source packages that are modified versions of the source package
        in a different distribution, and this relationship captures that
        concept.
        """)


class CodeImportReviewStatus(DBSchema):
    """CodeImport review status.

    Before a code import is performed, it is reviewed. Only reviewed imports
    are processed.
    """

    NEW = Item(1, """Pending Review

    This code import request has recently been filed an has not been reviewed
    yet.
    """)

    INVALID = Item(10, """Invalid

    This code import will not be processed.
    """)

    REVIEWED = Item(20, """Reviewed

    This code import has been approved and will be processed.
    """)

    SUSPENDED = Item(30, """Suspended

    This code import has been approved, but it has been suspended and is not
    processed.""")


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


class BranchReviewStatus(DBSchema):
    """Branch Review Cycle

    This is an indicator of what the project thinks about this branch.
    Typically, it will be set by the upstream as part of a review process
    before the branch lands on an official series.
    """

    NONE = Item(10, """
        None

        This branch has not been queued for review, and no review has been
        done on it.
        """)

    REQUESTED = Item(20, """
        Requested

        The author has requested a review of the branch. This usually
        indicates that the code is mature and ready for merging, but it may
        also indicate that the author would like some feedback on the
        direction in which he is headed.
        """)

    NEEDSWORK = Item(30, """
        Needs Further Work

        The reviewer feels that this branch is not yet ready for merging, or
        is not on the right track. Detailed comments would be found in the
        reviewer discussion around the branch, see those for a list of the
        issues to be addressed or discussed.
        """)

    MERGECONDITIONAL = Item(50, """
        Conditional Merge Approved

        The reviewer has said that this branch can be merged if specific
        issues are addressed. The review feedback will be contained in the
        branch discussion. Once those are addressed by the author the branch
        can be merged without further review.
        """)

    MERGEAPPROVED = Item(60, """
        Merge Approved

        The reviewer is satisfied that the branch can be merged without
        further changes.
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


class UpstreamReleaseVersionStyle(DBSchema):
    """Upstream Release Version Style

    Sourcerer will actively look for new upstream releases, and it needs
    to know roughly what version numbering format upstream uses. The
    release version number schemes understood by Sourcerer are documented
    in this schema. XXX andrew please fill in!
    """

    GNU = Item(1, """
        GNU-style Version Numbers

        XXX Andrew need description here
        """)


class RevisionControlSystems(DBSchema):
    """Revision Control Systems

    Bazaar brings code from a variety of upstream revision control
    systems into Arch. This schema documents the known and supported
    revision control systems.
    """

    CVS = Item(1, """
        Concurrent Version System

        The Concurrent Version System is very widely used among
        older open source projects, it was the first widespread
        open source version control system in use.
        """)

    SVN = Item(2, """
        Subversion

        Subversion aims to address some of the shortcomings in
        CVS, but retains the central server bottleneck inherent
        in the CVS design.
        """)


class RosettaTranslationOrigin(DBSchema):
    """Rosetta Translation Origin

    Translation sightings in Rosetta can come from a variety
    of sources. We might see a translation for the first time
    in CVS, or we might get it through the web, for example.
    This schema documents those options.
    """

    SCM = Item(1, """
        Source Control Management Source

        This translation sighting came from a PO File we
        analysed in a source control managements sytem first.
        """)

    ROSETTAWEB = Item(2, """
        Rosetta Web Source

        This translation was presented to Rosetta via
        the community web site.
        """)


class RosettaImportStatus(DBSchema):
    """Rosetta Import Status

    Define the status of an import on the Import queue. It could have one
    of the following states: approved, imported, deleted, failed, needs_review
    or blocked.
    """

    APPROVED = Item(1, """
        Approved

        The entry has been approved by a Rosetta Expert or was able to be
        approved by our automatic system and is waiting to be imported.
        """)

    IMPORTED = Item(2, """
        Imported

        The entry has been imported.
        """)

    DELETED = Item(3, """
        Deleted

        The entry has been removed before being imported.
        """)

    FAILED = Item(4, """
        Failed

        The entry import failed.
        """)

    NEEDS_REVIEW = Item(5, """
        Needs Review

        A Rosetta Expert needs to review this entry to decide whether it will
        be imported and where it should be imported.
        """)

    BLOCKED = Item(6, """
        Blocked

        The entry has been blocked to be imported by a Rosetta Expert.
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


class PersonalStanding(DBSchema):
    """A person's standing.

    Standing is currently (just) used to determine whether a person's posts to
    a mailing list require first-post moderation or not.  Any person with good
    or excellent standing may post directly to the mailing list without
    moderation.  Any person with unknown or poor standing must have their
    first-posts moderated.
    """

    UNKNOWN = Item(0, """
        Unknown standing

        Nothing about this person's standing is known.
        """)

    POOR = Item(100, """
        Poor standing

        This person has poor standing.
        """)

    GOOD = Item(200, """
        Good standing

        This person has good standing and may post to a mailing list without
        being subject to first-post moderation rules.
        """)

    EXCELLENT = Item(300, """
        Excellent standing

        This person has excellent standing and may post to a mailing list
        without being subject to first-post moderation rules.
        """)


class PollSecrecy(DBSchema):
    """The secrecy of a given Poll."""

    OPEN = Item(1, """
        Public Votes (Anyone can see a person's vote)

        Everyone who wants will be able to see a person's vote.
        """)

    ADMIN = Item(2, """
        Semi-secret Votes (Only team administrators can see a person's vote)

        All team owners and administrators will be able to see a person's vote.
        """)

    SECRET = Item(3, """
        Secret Votes (It's impossible to track a person's vote)

        We don't store the option a person voted in our database,
        """)


class PollAlgorithm(DBSchema):
    """The algorithm used to accept and calculate the results."""

    SIMPLE = Item(1, """
        Simple Voting

        The most simple method for voting; you just choose a single option.
        """)

    CONDORCET = Item(2, """
        Condorcet Voting

        One of various methods used for calculating preferential votes. See
        http://www.electionmethods.org/CondorcetEx.htm for more information.
        """)


class PostedMessageStatus(DBSchema):
    """The status of a posted message.

    When a message posted to a mailing list is subject to first-post
    moderation, the message gets one of these statuses.
    """

    NEW = Item(0, """
        New status

        The message has been posted and held for first-post moderation, but no
        disposition of the message has yet been made.
        """)

    APPROVED = Item(1, """
        Approved

        A message held for first-post moderation has been approved.
        """)

    REJECTED = Item(2, """
        Rejected

        A message held for first-post moderation has been rejected.
        """)


class TranslationFileFormat(DBSchema):
    """Translation File Format

    This is an enumeration of the different sorts of file that Launchpad
    Translations knows about.
    """

    PO = Item(1, """
        PO format

        Gettext's standard text file format.
        """)

    MO = Item(2, """
        MO format

        Gettext's standard binary file format.
        """)

    XPI = Item(3, """
        Mozilla XPI format

        The .xpi format as used by programs from Mozilla foundation.
        """)


class TranslationValidationStatus(DBSchema):
    """Translation Validation Status

    Every time a translation is added to Rosetta we should checked that
    follows all rules to be a valid translation inside a .po file.
    This schema documents the status of that validation.
    """

    UNKNOWN = Item(0, """
        Unknown

        This translation has not been validated yet.
        """)

    OK = Item(1, """
        Ok

        This translation has been validated and no errors were discovered.
        """)

    UNKNOWNERROR = Item(2, """
        Unknown Error

        This translation has an unknown error.
        """)


class TextDirection(DBSchema):
    """The base text direction for a language."""

    LTR = Item(0, """
        Left to Right

        Text is normally written from left to right in this language.
        """)

    RTL = Item(1, """
        Right to Left

        Text is normally written from left to right in this language.
        """)


class ArchivePurpose(DBSchema):
    """The purpose, or type, of an archive.

    A distribution can be associated with different archives and this
    schema item enumerates the different archive types and their purpose.
    For example, old distro releases may need to be obsoleted so their
    archive would be OBSOLETE_ARCHIVE.
    """

    PRIMARY = Item(1, """
        Primary Archive.

        This is the primary Ubuntu archive.
        """)

    PPA = Item(2, """
        PPA Archive.

        This is a Personal Package Archive.
        """)

    EMBARGOED = Item(3, """
        Embargoed Archive.

        This is the archive for embargoed packages.
        """)

    COMMERCIAL = Item(4, """
        Commercial Archive.

        This is the archive for commercial packages.
        """)

    OBSOLETE = Item(5, """
        Obsolete Archive.

        This is the archive for obsolete packages.
        """)
