# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Database schemas

Use them like this:

  from canonical.lp.dbschema import BugSeverity

  print "SELECT * FROM Bug WHERE Bug.severity='%d'" % BugSeverity.CRITICAL

"""
__metaclass__ = type

# MAINTAINER:
#
# When you add a new DBSchema subclass, add its name to the __all__ tuple
# below.
#
# If you do not do this, from canonical.lp.dbschema import * will not
# work properly, and the thing/lp:SchemaClass will not work properly.

# This should be in alphabetical order. please keep it that way.
__all__ = (
'ArchArchiveType',
'BinaryPackageFileType',
'BinaryPackageFormat',
'BinaryPackagePriority',
'BranchRelationships',
'BugAssignmentStatus',
'BugExternalReferenceType',
'BugInfestationStatus',
'BugPriority',
'BugRelationship',
'BugSeverity',
'BugSubscription',
'CodereleaseRelationships',
'DistributionReleaseState',
'DistributionRole',
'DOAPRole',
'EmailAddressStatus',
'HashAlgorithms',
'ImportTestStatus',
'KarmaField',
'ManifestEntryType',
'MembershipRole',
'MembershipStatus',
'PackagePublishingPriority',
'PackagePublishingStatus',
'Packaging',
'ProjectRelationship',
'ProjectStatus',
'RevisionControlSystems',
'RosettaImportStatus',
'RosettaTranslationOrigin',
'SourcePackageFileType',
'SourcePackageFormat',
'SourcePackageRelationships',
'SourcePackageUrgency',
'TranslationPriority',
'UpstreamFileType',
'UpstreamReleaseVersionStyle',
)

from zope.interface.advice import addClassAdvisor
import sys


def docstring_to_title_descr(string):
    """When given a classically formatted docstring, returns a tuple
    (title, description).

    >>> class Foo:
    ...     '''
    ...     Title of foo
    ...
    ...     Description of foo starts here.  It may
    ...     spill onto multiple lines.  It may also have
    ...     indented examples:
    ...
    ...       Foo
    ...       Bar
    ...
    ...     like the above.
    ...     '''
    ...
    >>> title, descr = docstring_to_title_descr(Foo.__doc__)
    >>> print title
    Title of foo
    >>> for num, line in enumerate(descr.splitlines()):
    ...    print num, line
    ...
    0 Description of foo starts here.  It may
    1 spill onto multiple lines.  It may also have
    2 indented examples:
    3 
    4   Foo
    5   Bar
    6 
    7 like the above.

    """
    lines = string.splitlines()
    # title is the first non-blank line
    for num, line in enumerate(lines):
        line = line.strip()
        if line:
            title = line
            break
    else:
        raise ValueError
    assert not lines[num+1].strip()
    descrlines = lines[num+2:]
    descr1 = descrlines[0]
    indent = len(descr1) - len(descr1.lstrip())
    descr = '\n'.join([line[indent:] for line in descrlines])
    return title, descr

class OrderedMapping:

    def __init__(self, mapping):
        self.mapping = mapping

    def __getitem__(self, key):
        return self.mapping[key]

    def __iter__(self):
        L = self.mapping.items()
        L.sort()
        for k, v in L:
            yield v


class ItemsDescriptor:

    def __get__(self, inst, cls=None):
        return OrderedMapping(cls._items)


class Item:
    """An item in an enumerated type.

    An item has a name, title and description.  It also has an integer value.
    """
    def __init__(self, value, title, description=None):
        frame = sys._getframe(1)
        locals = frame.f_locals

        # Try to make sure we were called from a class def
        if (locals is frame.f_globals) or ('__module__' not in locals):
            raise TypeError("Item can be used only from a class definition.")

        addClassAdvisor(self._setClassFromAdvice)
        try:
            self.value = int(value)
        except ValueError:
            raise TypeError("value must be an int, not %r" % (value,))
        if description is None:
            self.title, self.description = docstring_to_title_descr(title)
        else:
            self.title = title
            self.description = description

    def _setClassFromAdvice(self, cls):
        self._class = cls
        names = [k for k, v in cls.__dict__.iteritems() if v is self]
        assert len(names) == 1
        self.name = names[0]
        if not hasattr(cls, '_items'):
            cls._items = {}
        cls._items[self.value] = self
        return cls

    def __int__(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<Item %s (%d) from %s>" % (self.name, self.value, self._class)

    def __eq__(self, other):
        if isinstance(other, int):
            return self.value == other
        elif isinstance(other, Item):
            return self.value == other.value
        else:
            return False

    def __hash__(self):
        return self.value

# TODO: make a metaclass for dbschemas that looks for ALLCAPS attributes
#       and makes the introspectible.
#       Also, makes the description the same as the docstring.
#       Also, sets the name on each Item based on its name.
#       (Done by crufty class advice at present.)
#       Also, set the name on the DBSchema according to the class name.
#
#       Also, make item take just one string, optionally, and parse that
#       to make something appropriate.

class DBSchema:
    """Base class for database schemas."""

    # TODO: Make description a descriptor that automatically refers to the
    #       docstring.
    description = "See body of class's __doc__ docstring."
    title = "See first line of class's __doc__ docstring."
    name = "See lower-cased-spaces-inserted class name."
    items = ItemsDescriptor()


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


class ManifestEntryType(DBSchema):
    """A Sourcerer Manifest.

    This is a list of branches that are brought together to make up a source
    package. Each branch can be included in the package in a number of
    different ways, and the Manifest Entry Type tells sourcerer how to bring
    that branch into the package.
    """

    TAR = Item(1, """
        A Tar File

        This branch will be tarred up and installed in the source
        package as a tar file. Typically, the package build system
        will know how to untar that code and use it during the build.
        """)

    PATCH = Item(2, """
        Patch File

        This branch will be brought into the source file as a patch
        against another branch. Usually, the patch is stored in the
        "patches" directory, then applied at build time by the source
        package build scripts.
        """)

    COPY = Item(3, """
        Copied Source code

        This branch will simply be copied into the source package at
        a specified location. Typically this is used where a source
        package includes chunks of code such as libraries or reference
        implementation code, and builds it locally for static linking
        rather than depending on a system-installed shared library.
        """)

    DIR = Item(4, """
        A Directory

        This is a special case of Manifest Entry Type, and tells
        sourcerer simply to create an empty directory with the given name.
        """)

    IGNORE = Item(5, """
        An Item To Ignore

        This manifest entry type tells sourcerer to ignore something
        in the source package. For example, there might be a file which
        looks like a patch but isn't one (a shell script called xxx.patch
        is typical).
        """)


class Packaging(DBSchema):
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

##XXX: (gpg+dbschema) cprov 20041004
## the data structure should be rearranged to support 4 field
## needed: keynumber(1,16,17,20), keyalias(R,g,D,G), title and description
class GPGKeyAlgorithms(DBSchema):
    """
    GPG Compilant Key Algorithms Types:

    1 : "R", # RSA
    16: "g", # ElGamal
    17: "D", # DSA
    20: "G", # ElGamal, compromised

    FIXME
    Rewrite it according the experimental API retuning also a name attribute
    tested on 'algorithmname' attribute

    """

    R = Item(1, """
        R

        RSA""")

    g = Item(16, """
        g

        ElGamal""")

    D = Item(17, """
        D

        DSA""")

    G = Item(20, """
        G

        ElGamal, compromised""")


class BranchRelationships(DBSchema):
    """Branch relationships.

    In Arch, everything is a branch. Your patches are all branches. Your
    brother, sister and hifi system are all branches. If it moves, it's
    a branch. And Buttress (the Arch subsystem of Launchpad) tracks the
    relationships between those branches.
    """

    TRACKS = Item(1, """
        Subject Branch Tracks Object Branch

        The source branch "tracks" the destination branch. This means that
        we generally try to merge changes made in branch B into branch A.
        For example, if we have inlcuded a fix-branch into a source
        package, and there is an upstream for that fix-branch, then we will
        try to make our fix-branch "track" the upstream fix, so that our
        package inherits the latest fixes.
        """)

    CONTINUES = Item(2, """
        Subject Branch is a continuation of Object Branch

        The term "continuation" is an Arch term meaning that the branch was
        tagged from another one.
        """)

    RELEASES = Item(3, """
        Subject Branch is a "Release Branch" of Object Branch

        A "release branch" is a branch that is designed to capture the extra
        bits that are added to release tarballs and which are not in the
        project revision control system. For example, when a product is
        released, the project administrators will typically tag the
        code in the revision system, then pull that code into a clean
        directory. The files at this stage represent what is in the
        revision control system. They will often then add other files, for
        example files created by the Gnu Automake and Autoconf system,
        before tarring up the directory and pushing that tarball out as the
        release. Those extra files are included in a release branch.
        """)

    FIXES = Item(4, """
        Subject Branch is a fix for Object Branch

        This relationship indicates that Subject Branch includes a fix
        for the Object Branch. It is used to indicate that Subject
        Branch's main purpose is for the development of a fix to a
        specific issue in Object Branch. The description and title of the
        Subject will usually include information about the issue and the
        fix. Such fixes are usually merged when the fix is considered
        stable.
        """)

    PORTS = Item(5, """
        Subject Branch is a porting branch of B

        This relationship indicates that Subject Branch is a port of
        Object Branch to a different architecture or operating system.
        Such changes will usually be merged back at a future date when
        they are considered stable.
        """)

    ENHANCES = Item(6, """
        Subject Branch contains a new feature for Object Branch

        This relationship indicates that Subject Branch is a place
        where developers are working on a new feature for the
        software in Object Branch. Usually such a feature is merged
        at some future date when the code is considered stable.
        Subject The Branch.description will usually describe the
        feature being implemented.
        """)

    FORKS = Item(7, """
        The Subject Branch is a For of the Object Branch

        Sometimes the members of an open source project cannot agree on
        the direction a project should take, and the project forks. In
        this case, one group will "fork" the codebase and start work on a
        new version of the product which will likely not be merged. That
        new version is a "fork" of the original code.
        """)


class EmailAddressStatus(DBSchema):
    """Email Address Status

    Launchpad keeps track of email addresses associated with a person. They
    can be used to login to the system, or to associate an Arch changeset
    with a person, or to associate a bug system email message with a person,
    for example.
    """

    NEW = Item(1, """
        New Email Address

        This email address has had no validation associated with it. It
        has just been created in the system, either by a person claiming
        it as their own, or because we have stored an email message or
        arch changeset including that email address and have created
        a phantom person and email address to record it.
        """)

    VALIDATED = Item(2, """
        Validated Email Address

        We have proven that the person associated with this email address
        can read email sent to this email address, by sending a token
        to that address and getting the appropriate response from that
        person.
        """)

    OLD = Item(3, """
        Old Email Address

        The email address was validated for this person, but is now no
        longer accessible or in use by them. We should not use this email
        address to login that person, nor should we associate new incoming
        content from that email address with that person.
        """)

class MembershipRole(DBSchema):
    """Membership Role

    Launchpad knows about teams and individuals. People can be a member
    of many teams, and in each team that they are a member they will
    have a specific role. These are the kind of roles they could have.
    """

    ADMIN = Item(1, """
        Administrator

        The person is an administrator of this team. Typically that means
        that they can do anything that the owner of the team can do, it is
        a way for the owner to delegate authority in the team.
        """)

    MEMBER = Item(2, """
        Member

        The person is a normal member of the team, and can view and edit
        objects associated with that team accordingly.
        """)

class MembershipStatus(DBSchema):
    """Membership Status

    Some teams to not have automatic membership to anybody who wishes to
    join. In this case, a person can be proposed for membership, and the
    request can be approved or declined. The status of a membership can
    be one of these values. The Person.teamowner is always an admin
    member of the team, they do not need to have a membership record.
    """

    PROPOSED = Item(1, """
        Proposed Member

        The person has been proposed or has proposed themselves as a
        member of this team. This status conveys no access rights or
        privileges to the person.
        """)

    CURRENT = Item(2, """
        Current Member

        This person is currently a member of the team. This status means
        that the person will have full access as a member or admin, depending
        on their role.
        """)


class HashAlgorithms(DBSchema):
    """Hash Algorithms

    We use "hash" or "digest" cryptographic algorithms in a number of
    places in Launchpad. Usually these are a way of verifying the
    integrity of a file, but they can also be used to check if a file
    has been seen before. We support only "sha1" initially, if this
    is no longer trusted at some time we will add other algorithms.
    """

    SHA1 = Item(1, """
        The SHA-1 Digest Algorithm

        This algorithm is specified by the US-NIST and is used as part
        of TLS and other common cryptographic protocols. It is a 168-bit
        digest algorithm.
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


class DistributionReleaseState(DBSchema):
    """Distribution Release State

    A DistroRelease (warty, hoary, or grumpy for example) changes state
    throughout its development. This schema describes the level of
    development of the distrorelease. The typical sequence for a
    distrorelease is to progress from experimental to development to
    frozen to current to supported to obsolete, in a linear fashion.
    """

    EXPERIMENTAL = Item(1, """
        Experimental

        This distrorelease contains code that is far from active
        release planning or management. Typically, distroreleases
        that are beyond the current "development" release will be
        marked as "experimental". We create those so that people
        have a place to upload code which is expected to be part
        of that distant future release, but which we do not want
        to interfere with the current development release.
        """)

    DEVELOPMENT = Item(2, """
        Active Development

        The distrorelease that is under active current development
        will be tagged as "development". Typically there is only
        one active development release at a time. When that freezes
        and releases, the next release along switches from "experimental"
        to "development".
        """)

    FROZEN = Item(3, """
        Pre-release Freeze

        When a distrorelease is near to release the administrators
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

        This distrorelease is still supported, but it is no longer
        the current stable release. In Ubuntu we normally support
        a distrorelease for 2 years from release.
        """)

    OBSOLETE = Item(6, """
        Obsolete

        This distrorelease is no longer supported, it is considered
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
        upstream tarballs, configures them and builds them into the appropriate
        locations.
        """)

    SRPM = Item(2, """
        Source RPM

        This is a Source RPM, a normal RPM containing the needed source code
        to build binary packages. It would include the Spec file as well as
        all control and source code files.
        """)

    DSC = Item(3, """
        DSC File

        This is a DSC file containing the Ubuntu source package description,
        which in turn lists the orig.tar.gz and diff.tar.gz files used to make
        up the package.
        """)

    ORIG = Item(4, """
        Orig Tarball

        This file is an Ubuntu "orig" file, typically an upstream tarball or
        other lightly-modified upstreamish thing.
        """)

    DIFF = Item(5, """
        Diff File

        This is an Ubuntu "diff" file, containing changes that need to be made
        to upstream code for the packaging on Ubuntu. Typically this diff
        creates additional directories with patches and documentation used
        to build the binary packages for Ubuntu.
        """)

    TARBALL = Item(6, """
        Tarball

        This is a tarball, usually of a mixture of Ubuntu and upstream code,
        used in the build process for this source package.
        """)


class TranslationPriority(DBSchema):
    """Translation Priority

    Translations in Rosetta can be assigned a priority. This is used in a
    number of places. The priority stored on the translation itself is set
    by the upstream project maintainers, and used to identify the
    translations they care most about. For example, if Apache were nearing
    a big release milestone they would set the priority on those
    POTemplates to 'high'. The priority is also used by TranslationEfforts
    to indicate how important that POTemplate is to the effort. And
    lastly, an individual translator can set the priority on his personal
    subscription to a project, to determine where it shows up on his list.
    """

    HIGH = Item(1, """
        High

        This translation should be shown on any summary list of
        translations in the relevant context. For example, 'high' priority
        projects show up on the home page of a TranslationEffort or Project
        in Rosetta.
        """)

    MEDIUM = Item(2, """
        Medium

        A medium priority POTemplate should be shown on longer lists and
        dropdowns lists of POTemplates in the relevant context.
        """)

    LOW = Item(3, """
        Low

        A low priority POTemplate should only show up if a comprehensive
        search or complete listing is requested by the user.
        """)

class DistroReleaseQueueStatus(DBSchema):
    """Distro Release Queue Status

    An upload has various stages it must pass through before becoming
    part of a DistroRelease. These are managed via the DistroReleaseQueue
    table and related tables and eventually (assuming a successful upload
    into the DistroRelease) the effects are published via the PackagePublishing
    and SourcePackagePublishing tables.
    """

    UNCHECKED = Item(1, """
        Unchecked

        This upload has been checked enough to get it into the database but
        has yet to be checked for new binary packages, mismatched overrides
        or similar.
        """)

    NEW = Item(2, """
        New

        This upload is either a brand-new source package or contains a binary
        package with brand new debs or similar. The package must sit here until
        someone with the right role in the DistroRelease checks and either
        accepts or rejects the upload. If the upload is accepted then
        entries will be made in the overrides tables and further uploads
        will bypass this state
        """)

    UNAPPROVED = Item(3, """
        Unapproved

        If a DistroRelease is frozen or locked out of ordinary updates then
        this state is used to mean that while the package is correct from a
        technical point of view; it has yet to be approved for inclusion in
        this DistroRelease. One use of this state may be for security releases
        where you want the security team of a DistroRelease to approve uploads.
        """)

    BYHAND = Item(4, """
        ByHand

        If an upload contains files which are not stored directly into the
        pool tree (I.E. not .orig.tar.gz .tar.gz .diff.gz .dsc .deb or .udeb)
        then the package must be processed by hand. This may involve unpacking
        a tarball somewhere special or similar.
        """)

    ACCEPTED = Item(5, """
        Accepted

        An upload in this state has passed all the checks required of it and
        is ready to have its publishing records created.
        """)

    DONE = Item(7, """
        Done

        An upload in this state has had its publishing records created
        if it needs them and is fully processed into the
        DistroRelease. This state exists so that a logging and/or
        auditing tool can pick up accepted uploads and create entries
        in a journal or similar before removing the queue item.
        """)

    REJECTED = Item(6, """
        Rejected

        An upload which reaches this state has, for some reason or another
        not passed the requirements (technical or human) for entry into the
        DistroRelease it was targetting. As for the 'done' state, this
        state is present to allow logging tools to record the rejection
        and then clean up any subsequently unnecessary records.
        """)


class PackagePublishingStatus(DBSchema):
    """Package Publishing Status

     A package has various levels of being published within a DistroRelease.
     This is important because of how new source uploads dominate binary
     uploads bit-by-bit. Packages (source or binary) enter the publishing
     tables as 'Pending', progress through to 'Published' eventually become
     'Superceded' and then become 'PendingRemoval'. Once removed from the
     DistroRelease the publishing record is also removed.
     """

    PENDING = Item(1, """
        Pending

        This [source] package has been accepted into the DistroRelease and
        is now pending the addition of the files to the published disk area.
        """)

    PUBLISHED = Item(2, """
        Published

        This package is currently published as part of the archive for that
        distrorelease. In general there will only ever be one version of
        any source/binary package published at any one time. Once a newer
        version becomes published the older version is marked as superceded.
        """)

    SUPERCEDED = Item(3, """
        Superceded

        When a newer version of a [source] package is published the existing
        one is marked as "superceded".
        """)

    PENDINGREMOVAL = Item(6, """
        PendingRemoval

        Once a package is ready to be removed from the archive is is put
        into this state and the removal will be acted upon when a period
        of time has passed. When the package is moved to this state the
        scheduleddeletiondate column is filled out. When that date has passed
        the archive maintainance tools will remove the package from the on-disk
        archive and remove the publishing record.
        """)


class PackagePublishingPriority(DBSchema):
    """Package Publishing Priority

    Binary packages have a priority which is related to how important
    it is to have that package installed in a system. Common priorities
    range from required to optional and various others are available.
    """

    REQUIRED = Item( 50, """
        Required

        This priority indicates that the package is required. This priority
        is likely to be hard-coded into various package tools. Without all
        the packages at this priority it may become impossible to use dpkg.
        """)

    IMPORTANT = Item( 40, """
        Important

        If foo is in a package; and "What is going on?! Where on earth
        is foo?!?!" would be the reaction of an experienced UNIX
        hacker were the package not installed, then the package is
        important.
        """)

    STANDARD = Item( 30, """
        Standard

        Packages at this priority are standard ones you can rely on to be
        in a distribution. They will be installed by default and provide
        a basic character-interface userland.
        """)

    OPTIONAL = Item( 20, """
        Optional

        This is the software you might reasonably want to install if you
        did not know what it was or what your requiredments were. Systems
        such as X or TeX will live here.
        """)

    EXTRA = Item( 10, """
        Extra

        This contains all the packages which conflict with those at the other
        priority levels; or packages which are only useful to people who have
        very specialised needs.
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

        The subject source package was designed to replace the object
        source package.
        """)

    REIMPLEMENTS = Item(2, """
        Reimplements

        The subject source package is a completely new packaging of
        the same underlying products as the object package.
        """)

    SIMILARTO = Item(3, """
        Similar To

        The subject source package is similar, in that it packages
        software that has similar functionality to the object package.
        For example, postfix and exim4 would be "similarto" one
        another.
        """)

    DERIVESFROM = Item(4, """
        Derives From

        The subject source package derives from and tracks the object
        source package. This means that new uploads of the object package
        should trigger a notification to the maintainer of the subject
        source package.
        """)

    CORRESPONDSTO = Item(5, """
        Corresponds To

        The subject source package includes the same products as th
        object source package, but for a different distribution. For
        example, the "apache2" Ubuntu package "correspondsto" the
        "httpd2" package in Red Hat.
        """)


class BinaryPackageFormat(DBSchema):
    """Binary Package Format

    Launchpad tracks a variety of binary package formats. This schema
    documents the list of binary package formats that are supported
    in Launchpad.
    """

    DEB = Item(1, """
        Ubuntu Package

        This is the binary package format used by Ubuntu and all
        similar distributions. It includes dependency information
        to allow the system to ensure it always has all the software
        installed to make any new package work correctly.
        """)

    UDEB = Item(2, """
        Ubuntu Installer Package

        This is the binary package format use by the installer
        in Ubuntu and similar distributions.
        """)

    EBUILD = Item(3, """
        Gentoo Ebuild Package

        This is the Gentoo binary package format. While Gentoo
        is primarily known for being a build-it-from-source-yourself
        kind of distribution, it is possible to exchange binary
        packages between Gentoo systems.
        """)

    RPM = Item(4, """
        RPM Package

        This is the format used by Mandrake and other similar
        distributions. It does not include dependency tracking
        information.
        """)


class BinaryPackagePriority(DBSchema):
    """Binary Package Priority

    When a binary package is installed in an archive it can be assigned
    a specific priority. This schema documents the priorities that Launchpad
    knows about.
    """

    REQUIRED = Item(1, """
        Required Package

        This package is required for the distribution to operate normally.
        Usually these are critical core packages that are essential for the
        correct operation of the operating system.
        """)

    IMPORTANT = Item(2, """
        Important

        This package is important, and should be installed under normal
        circumstances.
        """)

    STANDARD = Item(3, """
        Standard

        The typical install of this distribution should include this
        package.
        """)

    OPTIONAL = Item(4, """
        Optional

        This is an optional package in this distribution.
        """)

    EXTRA = Item(5, """
        Extra

        This is an extra package in this distribution. An "extra" package
        might conflict with one of the standard or optional packages so
        it should be treated with some caution.
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


class BugAssignmentStatus(DBSchema):
    """Bug Assignment Status

    Bugs are assigned to products and to source packages in Malone. The
    assignment carries a status - new, open or closed. This schema
    documents those possible status values.
    """

    NEW = Item(10, """
        New

        This is a new bug and has not yet been accepted by the maintainer
        of this product or source package.
        """)

    ACCEPTED = Item(20, """
        Accepted

        This bug has been reviewed, perhaps verified, and accepted as
        something needing fixing.
        """)

    FIXED = Item(30, """
        Fixed

        This bug has been fixed.
        """)

    REJECTED = Item(40, """
        Rejected

        This bug has been rejected, e.g. in cases of operator-error.
        """)

class RemoteBugStatus(DBSchema):
    """Bug Assignment Status

    The status of a bug in a remote bug tracker. We map known statuses
    to one of these values, and use UNKNOWN if we are unable to map
    the remote status.
    """

    NEW = Item(1, """
        New

        This is a new bug and has not yet been accepted by the maintainer
        of this product or source package.
        """)

    OPEN = Item(2, """
        Open

        This bug has been reviewed and accepted by the maintainer, and
        is still open.
        """)

    CLOSED = Item(3, """
        Closed

        This bug has been closed by the maintainer.
        """)

    UNKNOWN = Item(99, """
        Unknown

        The remote bug status cannot be determined.
        """)

class BugPriority(DBSchema):
    """Bug Priority

    Each bug in Malone can be assigned a priority by the maintainer of
    the bug. The priority is an indication of the maintainer's desire
    to fix the bug. This schema documents the priorities Malone allows.
    """

    HIGH = Item(40, """
        High

        This is a high priority bug for the maintainer.
        """)

    MEDIUM = Item(30, """
        Medium

        This is a medium priority bug for the maintainer.
        """)

    LOW = Item(20, """
        Low

        This is a low priority bug for the maintainer.
        """)

    WONTFIX = Item(10, """
        Wontfix

        The maintainer does not intend to fix this bug.
        """)


class BugSeverity(DBSchema):
    """Bug Severity

    A bug assignment has a severity, which is an indication of the
    extent to which the bug impairs the stability and security of
    the distribution.
    """

    CRITICAL = Item(50, """
        Critical

        This bug is essential to fix as soon as possible. It affects
        system stability, data integrity and / or remote access
        security.
        """)

    MAJOR = Item(40, """
        Major

        This bug needs urgent attention from the maintainer or
        upstream. It affects local system security or data integrity.
        """)

    NORMAL = Item(30, """
        Normal

        This bug warrants an upload just to fix it, but can be put
        off until other major or critical bugs have been fixed.
        """)

    MINOR = Item(20, """
        Minor

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

    Buttress brings code from a variety of upstream revision control
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

    ARCH = Item(3, """
        The Arch Revision Control System

        An open source revision control system that combines truly
        distributed branching with advanced merge algorithms. This
        removes the scalability problems of centralised revision
        control.
        """)

    PACKAGE = Item(4, """
        Package

        XXX Provide a description.
        """)


    BITKEEPER = Item(5, """
        Bitkeeper

        A commercial revision control system that, like Arch, uses
        distributed branches to allow for faster distributed
        development.
        """)


class ArchArchiveType(DBSchema):
    """Arch Archive Type

    An arch archive can be read only, or it might be an archive
    into which we can push new changes, or it might be a mirror
    into which we can only push changes from the upstream. This schema
    documents those states.
    """

    READWRITE = Item(1, """
        ReadWrite Archive

        This archive can be written to with new changesets, it
        is an archive which we "own" and therefor are free to
        write changesets into. Note that an archive which has
        been created for upstream CVS mirroring, for example, would
        be "readwrite" because we need to be able to create new
        changesets in it as we mirror the changes in the CVS
        repository.
        """)

    READONLY = Item(2, """
        Read Only Archive

        An archive in the "readonly" state can only be published
        and read from, it cannot be written to.
        """)

    MIRRORTARGET = Item(3, """
        Mirror Target

        We can write into this archive, but we can only write
        changesets which have actually come from the upstream
        arch archive of which this is a mirror.
        """)


class BugSubscription(DBSchema):
    """A Bug Subscription type.

    This is a list of the type of relationships a person can have with a bug.
    """

    WATCH = Item(1, """
        Watch

        The person wishes to watch this bug through a web interface. Emails
        are not required.
        """)

    CC = Item(2, """
        CC

        The person wishes to watch this bug through a web interface and in
        addition wishes to be notified by email whenever their is activity
        relating to this bug.
        """)

    IGNORE = Item(3, """
        Ignore

        The person has taken an active decision to ignore this bug. They do
        not wish to receive any communications about it.
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


class DistributionRole(DBSchema):
    """Distribution Role

    This schema documents the roles that a person can play in
    a distribution, other than being a package maintainer.
    """

    DM = Item (1, """
        Distro Master

        Oversees all distribution activities.
        """
    )
    SO = Item (2, """
        Security Overlord

        Ensures no sharp edges are left in the distribution.
        """
    )
    PD = Item (3, """
        Prophet of Doom

        Makes hand-wavy predictions.
        """
    )

class DistroReleaseRole(DBSchema):
    """Distribution Role

    This schema documents the roles that a person can play in
    a distribution, other than being a package maintainer.
    """

    RM = Item (1, """
        Release Manager

        Distribution Release Manager""")
    
    SO = Item (2, """
        Security Officer

        Distribution Release Manager""")

    BW = Item (3, """
        Bug Wrangler

        Corrals and keeps the release bugs under control""")

    UB = Item (4, """
        User Bender
        
        Convinces users that it's a feature""")

class DOAPRole(DBSchema):
    """DOAP Role

    This schema documents the roles that a person can play in
    a DOAP project. The person might have these roles with
    regard to the project as a whole or to a specific product
    of that project."""

    MAINTAINER = Item(1, """
        Maintainer

        A project or product maintainer is a member of the core
        team of people who are responsible for that open source
        work. Maintainers have commit rights to the relevant code
        repository, and are the ones who sign off on any release.""")

    ADMIN = Item(2, """
        Administrator

        The project or product administrators for a Launchpad
        project and product have the same privileges as the
        project or product owner, except that they cannot appoint
        more administrators. This allows the project owner to share
        the load of administration with other individuals.""")


class RosettaImportStatus(DBSchema):
    """Rosetta Import Status

    After a raw file is added into Rosetta it could have a set of
    states like ignore, pending, imported or failed.
    This schema documents those options.
    """

    IGNORE = Item(1, """
        Ignore

        There are not any rawfile attached and we don't need to do
        anything with that field.
        """)

    PENDING = Item(2, """
        Pending

        There are a rawfile pending of review to be finally imported into
        the system.
        """)

    IMPORTED = Item(3, """
        Imported

        The attached rawfile has been already imported so it does not needs
        any extra process.
        """)

    FAILED = Item(4, """
        Failed

        The attached rawfile import failed.
        """)


class KarmaField(DBSchema):
    # If you add a new Item here, please remember to add it to 
    # canonical.launchpad.database.person.KARMA_POINTS too. 
    # XXX: This KarmaField is a good candidate for leaving dbschema and
    # get into the database.
    """Karma Field

    This schema documents the different kinds of Karma that can be
    assigned to a person. A person have a list of assigned Karmas and
    each of these Karmas have a KarmaField.
    """

    WIKI_EDIT = Item(1, """
        Wiki Page Edited

        User edited a Wiki page.
    """)

    WIKI_CREATE = Item(2, """
        New Wiki Page

        User created a new page in the Wiki.
    """)

    BUG_COMMENT = Item(3, """
        New Comment on Bug

        User posted a comment on the bug's discussion forum.
    """)

    BUG_REPORT = Item(4, """
        Bug Report

        User reported a new bug.
    """)

    BUG_FIX = Item(5, """
        Bug Fix

        User provided a patch to fix a bug.
    """)

    PACKAGE_UPLOAD = Item(6, """
        Package Uploaded

        User uploaded a new package to the system.
    """)

