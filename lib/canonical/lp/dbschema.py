# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Database schemas

Use them like this:

  from canonical.lp.dbschema import BugTaskSeverity

  print "SELECT * FROM Bug WHERE Bug.severity='%d'" % BugTaskSeverity.CRITICAL

"""
__metaclass__ = type

# MAINTAINER:
#
# When you add a new DBSchema subclass, add its name to the __all__ tuple
# below.
#
# If you do not do this, from canonical.lp.dbschema import * will not
# work properly, and the thing/lp:SchemaClass will not work properly.

# The DBSchema subclasses should be in alphabetical order, listed after
# EnumCol and Item.  Please keep it that way.
__all__ = (
'EnumCol',
'Item',
'DBSchema',
# DBSchema types follow.
'ArchArchiveType',
'BinaryPackageFileType',
'BinaryPackageFormat',
'BountyDifficulty',
'BountyStatus',
'BranchRelationships',
'BugTaskStatus',
'BugAttachmentType',
'BugTrackerType',
'BugExternalReferenceType',
'BugInfestationStatus',
'BugTaskPriority',
'BugRelationship',
'BugTaskSeverity',
'BuildStatus',
'CodereleaseRelationships',
'CveStatus',
'DistributionReleaseStatus',
'EmailAddressStatus',
'GPGKeyAlgorithm',
'HashAlgorithm',
'ImportTestStatus',
'ImportStatus',
'KarmaActionCategory',
'KarmaActionName',
'LoginTokenType',
'ManifestEntryType',
'ManifestEntryHint',
'MirrorFreshness',
'PackagePublishingPriority',
'PackagePublishingStatus',
'PackagePublishingPocket',
'PackagingType',
'PollAlgorithm',
'PollSecrecy',
'ProjectRelationship',
'ProjectStatus',
'RevisionControlSystems',
'RosettaFileFormat',
'RosettaImportStatus',
'RosettaTranslationOrigin',
'ShipItArchitecture',
'ShipItDistroRelease',
'ShipItFlavour',
'SourcePackageFileType',
'SourcePackageFormat',
'SourcePackageRelationships',
'SourcePackageUrgency',
'SpecificationPriority',
'SpecificationStatus',
'SSHKeyType',
'TicketPriority',
'TicketStatus',
'TeamMembershipStatus',
'TeamSubscriptionPolicy',
'TranslationPriority',
'TranslationPermission',
'TranslationValidationStatus',
'DistroReleaseQueueStatus',
'UpstreamFileType',
'UpstreamReleaseVersionStyle',
)

from canonical.database.constants import DEFAULT

from zope.interface.advice import addClassAdvisor
import sys
import warnings

from sqlobject.col import SOCol, Col
from sqlobject.include import validators
import sqlobject.constraints as consts


class SODBSchemaEnumCol(SOCol):

    def __init__(self, **kw):
        self.schema = kw.pop('schema')
        if not issubclass(self.schema, DBSchema):
            raise TypeError('schema must be a DBSchema: %r' % self.schema)
        SOCol.__init__(self, **kw)
        self.validator = validators.All.join(
            DBSchemaValidator(schema=self.schema), self.validator)

    def autoConstraints(self):
        return [consts.isInt]

    def _sqlType(self):
        return 'INT'


class DBSchemaEnumCol(Col):
    baseClass = SODBSchemaEnumCol


class DBSchemaValidator(validators.Validator):

    def __init__(self, **kw):
        self.schema = kw.pop('schema')
        validators.Validator.__init__(self, **kw)

    def fromPython(self, value, state):
        """Convert from DBSchema Item to int.

        >>> validator = DBSchemaValidator(schema=BugTaskStatus)
        >>> validator.fromPython(BugTaskStatus.PENDINGUPLOAD, None)
        25
        >>> validator.fromPython(ImportTestStatus.NEW, None)
        Traceback (most recent call last):
        ...
        TypeError: DBSchema Item from wrong class
        >>>

        """
        if value is None:
            return None
        if isinstance(value, int):
            raise TypeError(
                'Need to set a dbschema Enum column to a dbschema Item,'
                ' not an int')
        # Allow this to work in the presence of security proxies.
        ##if not isinstance(value, Item):
        if value is DEFAULT:
            return value
        if value.__class__ != Item:
            raise TypeError('Not a DBSchema Item: %r' % value)
        if value.schema is not self.schema:
            raise TypeError('DBSchema Item from wrong class')
        return value.value

    def toPython(self, value, state):
        """Convert from int to DBSchema Item.

        >>> validator = DBSchemaValidator(schema=BugTaskStatus)
        >>> validator.toPython(25, None) is BugTaskStatus.PENDINGUPLOAD
        True

        """
        if value is None:
            return None
        if value is DEFAULT:
            return value
        return self.schema.items[value]

EnumCol = DBSchemaEnumCol

def docstring_to_title_descr(string):
    """When given a classically formatted docstring, returns a tuple
    (title,x description).

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
        if key in self.mapping:
            return self.mapping[key]
        else:
            for k, v in self.mapping.iteritems():
                if v.name == key:
                    return v
            raise KeyError, key

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
        self.schema = cls
        names = [k for k, v in cls.__dict__.iteritems() if v is self]
        assert len(names) == 1
        self.name = names[0]
        if not hasattr(cls, '_items'):
            cls._items = {}
        cls._items[self.value] = self
        return cls

    def __int__(self):
        raise TypeError("Cannot cast Item to int.  Use item.value instead.")

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<Item %s (%d) from %s>" % (self.name, self.value, self.schema)

    def __sqlrepr__(self, dbname):
        return repr(self.value)

    def __eq__(self, other, stacklevel=2):
        if isinstance(other, int):
            warnings.warn('comparison of DBSchema Item to an int: %r' % self,
                stacklevel=stacklevel)
            return False
        # Cannot use isinstance, because 'other' might be security proxied.
        ##elif isinstance(other, Item):
        elif other.__class__ == Item:
            return self.value == other.value and self.schema == other.schema
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other, stacklevel=3)

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


class ArchArchiveType(DBSchema):
    """Arch Archive Type

    An arch archive can be read only, or it might be an archive
    into which we can push new changes, or it might be a mirror
    into which we can only push changes from the upstream. This schema
    documents those states.
    """

    READWRITE = Item(0, """
        ReadWrite Archive

        This archive can be written to with new changesets, it
        is an archive which we "own" and therefor are free to
        write changesets into. Note that an archive which has
        been created for upstream CVS mirroring, for example, would
        be "readwrite" because we need to be able to create new
        changesets in it as we mirror the changes in the CVS
        repository.
        """)

    READONLY = Item(1, """
        Read Only Archive

        An archive in the "readonly" state can only be published
        and read from, it cannot be written to.
        """)

    MIRRORTARGET = Item(2, """
        Mirror Target

        We can write into this archive, but we can only write
        changesets which have actually come from the upstream
        arch archive of which this is a mirror.
        """)


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


class ManifestEntryType(DBSchema):
    """A Sourcerer Manifest.

    This is a list of branches that are brought together to make up a source
    package. Each branch can be included in the package in a number of
    different ways, and the Manifest Entry Type tells sourcerer how to bring
    that branch into the package.
    """

    DIR = Item(1, """
        A Directory

        This is a special case of Manifest Entry Type, and tells
        sourcerer simply to create an empty directory with the given name.
        """)

    COPY = Item(2, """
        Copied Source code

        This branch will simply be copied into the source package at
        a specified location. Typically this is used where a source
        package includes chunks of code such as libraries or reference
        implementation code, and builds it locally for static linking
        rather than depending on a system-installed shared library.
        """)

    FILE = Item(3, """
        Binary file

        This is another special case of Manifest Entry Type that tells
        sourcerer to create a branch containing just the file given.
        """)

    TAR = Item(4, """
        A Tar File

        This branch will be tarred up and installed in the source
        package as a tar file. Typically, the package build system
        will know how to untar that code and use it during the build.
        """)

    ZIP = Item(5, """
        A Zip File

        This branch will be zipped up and installed in the source
        package as a zip file. Typically, the package build system
        will know how to unzip that code and use it during the build.
        """)

    PATCH = Item(6, """
        Patch File

        This branch will be brought into the source file as a patch
        against another branch. Usually, the patch is stored in the
        "patches" directory, then applied at build time by the source
        package build scripts.
        """)


class ManifestEntryHint(DBSchema):
    """Hint as to purpose of a ManifestEntry.

    Manifests, used by both HCT and Sourcerer, are made up of a collection
    of Manifest Entries.  Each entry refers to a particular component of
    the source package built by the manifest, usually each having a different
    branch or changeset.  A Manifest Entry Hint can be assigned to suggest
    what the purpose of the entry is.
    """

    ORIGINAL_SOURCE = Item(1, """
        Original Source

        This is the original source code of the source package, and in the
        absence of any Patch Base, the parent of any new patch branches
        created.
        """)

    PATCH_BASE = Item(2, """
        Patch Base

        This is an entry intended to serve as the base for any new patches
        created and added to the source package.  It is often a patch itself,
        or a virtual branch.  If not present, the Original Source is used
        instead.
        """)

    PACKAGING = Item(3, """
        Packaging

        This is the packaging meta-data for the source package, usually
        the entry that becomes the debian/ directory in the case of Debian
        source packages or the spec file in the case of RPMs.
        """)


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

##XXX: (gpg+dbschema) cprov 20041004
## the data structure should be rearranged to support 4 field
## needed: keynumber(1,16,17,20), keyalias(R,g,D,G), title and description
class GPGKeyAlgorithm(DBSchema):
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
    a branch. And Bazaar (the Arch subsystem of Launchpad) tracks the
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
        a phantom person and email address to record it. WE SHOULD
        NEVER EMAIL A "NEW" EMAIL.
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

    PREFERRED = Item(4, """
        Preferred Email Address

        The email address was validated and is the person's choice for
        receiving notifications from Launchpad.
        """)

class TeamMembershipStatus(DBSchema):
    """TeamMembership Status

    According to the policies specified by each team, the membership status of
    a given member can be one of multiple different statuses. More information
    can be found in the TeamMembership spec.
    """

    PROPOSED = Item(1, """
        Proposed

        You are a proposed member of this team. To become an active member your
        subscription has to bo approved by one of the team's administrators.
        """)

    APPROVED = Item(2, """
        Approved

        You are an active member of this team.
        """)

    ADMIN = Item(3, """
        Administrator

        You are an administrator of this team.
        """)

    DEACTIVATED = Item(4, """
        Deactivated

        Your subscription to this team has been deactivated.
        """)

    EXPIRED = Item(5, """
        Expired

        Your subscription to this team is expired.
        """)

    DECLINED = Item(6, """
        Declined

        Your proposed subscription to this team has been declined.
        """)


class TeamSubscriptionPolicy(DBSchema):
    """Team Subscription Policies

    The policies that apply to a team and specify how new subscriptions must
    be handled. More information can be found in the TeamMembershipPolicies
    spec.
    """

    MODERATED = Item(1, """
        Moderated Team

        All subscriptions for this team are subjected to approval by one of
        the team's administrators.
        """)

    OPEN = Item(2, """
        Open Team

        Any user can join and no approval is required.
        """)

    RESTRICTED = Item(3, """
        Restricted Team

        New members can only be added by one of the team's administrators.
        """)


class HashAlgorithm(DBSchema):
    """Hash Algorithms

    We use "hash" or "digest" cryptographic algorithms in a number of
    places in Launchpad. Usually these are a way of verifying the
    integrity of a file, but they can also be used to check if a file
    has been seen before.
    """

    MD5 = Item(0, """
        The MD5 Digest Algorithm

        A widely-used cryptographic hash function with a 128-bit hash value. As
        an Internet standard (RFC 1321), MD5 has been employed in a wide
        variety of security applications.
        """)

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


class DistributionReleaseStatus(DBSchema):
    """Distribution Release Status

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


class SpecificationPriority(DBSchema):
    """The Priority with a Specification must be implemented.

    This enum is used to prioritise work.
    """

    WISHLIST = Item(0, """
        Wishlist

        This specification is on the "nice to have" list, but is unlikely to
        be implemented as part of a specific release unless somebody
        develops an irresistable itch to do so, on their own initiative.
        """)

    LOW = Item(10, """
        Low

        The specification is low priority. We would like to have it in the
        code, but it's not on any critical path and is likely to get bumped
        in favour of higher-priority work.
        """)

    MEDIUM = Item(50, """
        Medium

        The specification is of a medium, or normal priority. We will
        definitely get to this feature but perhaps not in the next month or
        two.
        """)

    HIGH = Item(70, """
        High

        The specification is definitely desired for the next major release,
        and should be the focal point of developer attention right now.
        """)

    EMERGENCY = Item(90, """
        Emergency

        The specification is required immediately, and should be implemented
        in such a way that it can be moved to production as soon as it is
        ready, perhaps by publishing a new stable product release rather
        than waiting for a new major release.
        """)


class SpecificationStatus(DBSchema):
    """The current status of a Specification

    This enum tells us whether or not a specification is approved, or still
    being drafted, or implemented, or obsolete in some way. The ordinality
    of the values is important, it's the order (lowest to highest) in which
    we probably want them displayed by default.
    """

    APPROVED = Item(10, """
        Approved

        This specification has been approved. The project team believe that
        is ready to be implemented.
        """)

    PENDING = Item(20, """
        Pending Approval

        This spec has been put in a reviewers queue. The reviewer will
        either move it to "approved" or bump it back to "draft", making
        review comments for consideration at the bottom.
        """)

    DRAFT = Item(30, """
        Draft

        The specification is in Draft status. The drafter has made a start
        on reviewing the document.
        """)

    BRAINDUMP = Item(40, """
        Braindump

        The specification is just a thought, or collection of thoughts, with
        no attention paid to implementation strategy, dependencies or
        presentation/UI issues.
        """)

    IMPLEMENTED = Item(50, """
        Implemented

        The specification has been implemented, and has landed in the
        codebase to which it was targeted.
        """)

    SUPERCEDED = Item(60, """
        Superceded

        This specification is still interesting, but has been superceded by
        a newer spec, or set of specs, that clarify or describe a newer way
        to implement the desired feature(s). Please use the newer specs and
        not this one.
        """)

    OBSOLETE = Item(70, """
        Obsolete

        This specification has been obsoleted. Probably, we decided not to
        implement it for some reason. It should not be displayed, and people
        should not put any effort into implementing it.
        """)


class TicketPriority(DBSchema):
    """The Priority with a Support Request must be handled.

    This enum is used to prioritise work done in the Launchpad support
    request management system.
    """

    WISHLIST = Item(0, """
        Wishlist

        This support ticket is really a request for a new feature. We will
        not take it further as a support ticket, it should be closed, and a
        specification created and managed in the Launchpad Specification
        Tracker.
        """)

    NORMAL = Item(10, """
        Normal

        This support ticket is of normal priority. We should respond to it
        in due course.
        """)

    HIGH = Item(70, """
        High

        This support ticket has been flagged as being of higher than normal
        priority. It should always be prioritised over a "normal" support
        request.
        """)

    EMERGENCY = Item(90, """
        Emergency

        This support ticket is classed as an emergency. No more than 5% of
        requests should fall into this category. Support engineers should
        ensure that there is somebody on this problem full time until it is
        resolved, or escalate it to the core technical and management team.
        """)


class TicketStatus(DBSchema):
    """The current status of a Support Request

    This enum tells us the current status of the support ticket. The
    request has a simple lifecycle, from new to closed.
    """

    NEW = Item(10, """
        New

        This support ticket is new to the system and has not yet been
        reviewed by any support engineer.
        """)

    OPEN = Item(20, """
        Open

        This support ticket has been reviewed by a support engineer, and is
        considered to be a valid issue. There may have been some
        correspondence on the issue, but we do not think it has yet been
        answered properly.
        """)

    ANSWERED = Item(30, """
        Answered

        We believe that the last correspondence from the support engineer
        was sufficient to resolve the problem. At this stage, the customer
        will receive email notifications asking them to confirm the
        resolution of the problem by marking the request "closed".
        Alternatively, they can re-open the request, marking it "open".
        """)

    CLOSED = Item(40, """
        Closed

        This request has been verified as "closed" by the customer.
        """)

    REJECTED = Item(50, """
        Rejected

        This request has been marked as "rejected" by the support engineer,
        likely it represents sample data or a mistaken entry. This request
        will not show on most lists or reports.
        """)


class ImportStatus(DBSchema):
    """This schema describes the states that a SourceSource record can take
    on."""

    DONTSYNC = Item(1, """
        Do Not Sync

        We do not want to attempt to test or sync this upstream repository
        or branch. The ProductSeries can be set to DONTSYNC from any state
        other than SYNCING. Once it is Syncing, it can be STOPPED but should
        not be set to DONTSYNC. This prevents us from forgetting that we
        were at one stage SYNCING the ProductSeries.  """)

    TESTING = Item(2, """
        Testing

        New entries should start in this mode. We will try to import the
        given upstream branch from CVS or SVN automatically. When / if this
        ever succeeds it should set the status to AUTOTESTED.  """)

    TESTFAILED = Item(3, """
        Test Failed

        This sourcesource has failed its test import run. Failures can be
        indicative of a problem with the RCS server, or a problem with the
        actual data in their RCS system, or a network error.""")

    AUTOTESTED = Item(4, """
        Auto Tested

        The automatic testing system ("roomba") has successfully imported
        and in theory verified its import of the upstream revision control
        system. This ProductSeries is a definite candidate for manual review
        and should be switched to PROCESSING.  """)

    PROCESSING = Item(5, """
        Processing

        This ProductSeries is nearly ready for syncing. We will run it
        through the official import process, and then manually review the
        results. If they appear to be correct, then the
        ProductSeries.bazimportstatus can be set to SYNCING.  """)

    SYNCING = Item(6, """
        Syncing

        This ProductSeries is in Sync mode and SHOULD NOT BE EDITED OR
        CHANGED.  At this point, protection of the data related to the
        upstream revision control system should be extreme, with only
        launchpad.Special (in this case the buttsource team) able to affect
        these fields. If it is necessary to stop the syncing then the status
        must be changed to STOPPED, and not to DONTSYNC.  """)

    STOPPED = Item(7, """
        Stopped

        This state is used for ProductSeries that were in SYNCING mode and
        it was necessary to stop the sync activity. For example, when an
        upstream uses the same branch for versions 1, 2 and 3 of their
        product, we should put the ProductSeries into STOPPED after each
        release, create a new ProductSeries for the next version with the
        same branch details for upstream revision control system. That way,
        if they go back and branch off the previous release tag, we can
        amend the previous ProductSeries.  In theory, a STOPPED
        ProductSeries can be set to Sync again, but this requires serious
        Bazaar fu, and the buttsource team.  """)


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
    be translated. In this case, Rosetta allows them to decide how open they
    want that translation process to be. At one extreme, anybody can add or
    edit any translation, without review. At the other, only the designated
    translator for that group in that language can edit its translation
    files. This schema enumerates the options.
    """

    OPEN = Item(1, """
        Open

        This group allows totally open access to its translations. Any
        logged-in user can add or edit translations in any language, without
        any review.""")

    CLOSED = Item(100, """
        Closed

        This group allows only designated translators to edit the
        translations of its files. No other contributions will be considered
        or allowed.""")

class DistroReleaseQueueStatus(DBSchema):
    """Distro Release Queue Status

    An upload has various stages it must pass through before becoming part
    of a DistroRelease. These are managed via the DistroReleaseQueue table
    and related tables and eventually (assuming a successful upload into the
    DistroRelease) the effects are published via the PackagePublishing and
    SourcePackagePublishing tables.  """

    UNCHECKED = Item(1, """
        Unchecked

        This upload has been checked enough to get it into the database but
        has yet to be checked for new binary packages, mismatched overrides
        or similar.  """)

    NEW = Item(2, """
        New

        This upload is either a brand-new source package or contains a
        binary package with brand new debs or similar. The package must sit
        here until someone with the right role in the DistroRelease checks
        and either accepts or rejects the upload. If the upload is accepted
        then entries will be made in the overrides tables and further
        uploads will bypass this state """)

    UNAPPROVED = Item(3, """
        Unapproved

        If a DistroRelease is frozen or locked out of ordinary updates then
        this state is used to mean that while the package is correct from a
        technical point of view; it has yet to be approved for inclusion in
        this DistroRelease. One use of this state may be for security
        releases where you want the security team of a DistroRelease to
        approve uploads.  """)

    BYHAND = Item(4, """
        ByHand

        If an upload contains files which are not stored directly into the
        pool tree (I.E. not .orig.tar.gz .tar.gz .diff.gz .dsc .deb or
        .udeb) then the package must be processed by hand. This may involve
        unpacking a tarball somewhere special or similar.  """)

    ACCEPTED = Item(5, """
        Accepted

        An upload in this state has passed all the checks required of it and
        is ready to have its publishing records created.  """)

    DONE = Item(7, """
        Done

        An upload in this state has had its publishing records created if it
        needs them and is fully processed into the DistroRelease. This state
        exists so that a logging and/or auditing tool can pick up accepted
        uploads and create entries in a journal or similar before removing
        the queue item.  """)

    REJECTED = Item(6, """
        Rejected

        An upload which reaches this state has, for some reason or another
        not passed the requirements (technical or human) for entry into the
        DistroRelease it was targetting. As for the 'done' state, this state
        is present to allow logging tools to record the rejection and then
        clean up any subsequently unnecessary records.  """)


class PackagePublishingStatus(DBSchema):
    """Package Publishing Status

     A package has various levels of being published within a DistroRelease.
     This is important because of how new source uploads dominate binary
     uploads bit-by-bit. Packages (source or binary) enter the publishing
     tables as 'Pending', progress through to 'Published' eventually become
     'Superseded' and then become 'PendingRemoval'. Once removed from the
     DistroRelease the publishing record is also removed.
     """

    PENDING = Item(1, """
        Pending

        This [source] package has been accepted into the DistroRelease and
        is now pending the addition of the files to the published disk area.
        In due course, this source package will be published.
        """)

    PUBLISHED = Item(2, """
        Published

        This package is currently published as part of the archive for that
        distrorelease. In general there will only ever be one version of any
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
        packages in distroreleases. """)

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

    A single distrorelease can at its heart be more than one logical
    distrorelease as the tools would see it. For example there may be a
    distrorelease called 'hoary' and a SECURITY pocket subset of that would
    be referred to as 'hoary-security' by the publisher and the distro side
    tools.
    """

    RELEASE = Item(0, """
        Release

        This is the "release" pocket, it contains the versions of the
        packages that were published when the release was made. For releases
        that are still under development, this is the only pocket into which
        packages will be published.
        """)

    SECURITY = Item(10, """
        Security

        This is the pocket into which we publish only security fixes to the
        released distribution. It is highly advisable to ensure that your
        system has the security pocket enabled.
        """)

    UPDATES = Item(20, """
        Updates

        This is the pocket into which we publish packages with new
        functionality after a release has been made. It is usually
        enabled by default after a fresh install.
        """)

    PROPOSED = Item(30, """
        Proposed

        This is the pocket into which we publish packages with new
        functionality after a release has been made, which we would like to
        have widely tested but not yet made part of a default installation.
        People who "live on the edge" will have enabled the "proposed"
        pocket, and so will start testing these packages. Once they are
        proven safe for wider deployment they will go into the updates
        pocket.
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


class BugTaskStatus(DBSchema):
    """Bug Task Status

    Bugs are assigned to products and to source packages in Malone. The
    task carries a status - new, open or closed. This schema
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

    PENDINGUPLOAD = Item(25, """
        PendingUpload

        The source package with the fix has been sent off to the buildds.
        The bug will be resolved once the newly uploaded package is
        completed.
        """)

    FIXED = Item(30, """
        Fixed

        This bug has been fixed.
        """)

    REJECTED = Item(40, """
        Rejected

        This bug has been rejected, e.g. in cases of operator-error.
        """)


class BugTaskPriority(DBSchema):
    """Bug Task Priority

    Each bug task in Malone can be assigned a priority by the
    maintainer of the bug. The priority is an indication of the
    maintainer's desire to fix the task. This schema documents the
    priorities Malone allows.
    """

    HIGH = Item(40, """
        High

        This is a high priority task for the maintainer.
        """)

    MEDIUM = Item(30, """
        Medium

        This is a medium priority task for the maintainer.
        """)

    LOW = Item(20, """
        Low

        This is a low priority task for the maintainer.
        """)

    WONTFIX = Item(10, """
        Wontfix

        The maintainer does not intend to fix this task.
        """)


class BugTaskSeverity(DBSchema):
    """Bug Task Severity

    A bug task has a severity, which is an indication of the
    extent to which the bug impairs the stability and security of
    the distribution or upstream in which it was reported.
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

    ARCH = Item(3, """
        The Arch Revision Control System

        An open source revision control system that combines truly
        distributed branching with advanced merge algorithms. This
        removes the scalability problems of centralised revision
        control.
        """)

    PACKAGE = Item(4, """
        Package

        DEPRECATED DO NOT USE
        """)


    BITKEEPER = Item(5, """
        Bitkeeper

        A commercial revision control system that, like Arch, uses
        distributed branches to allow for faster distributed
        development.
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


class KarmaActionName(DBSchema):
    """The name of an action that gives karma to a user."""

    BUGCREATED = Item(1, """
        New Bug Created

        """)

    BUGCOMMENTADDED = Item(2, """
        New Comment

        """)

    BUGTITLECHANGED = Item(3, """
        Bug Title Changed

        """)

    BUGSUMMARYCHANGED = Item(4, """
        Bug Summary Changed

        """)

    BUGDESCRIPTIONCHANGED = Item(5, """
        Bug Description Changed

        """)

    BUGEXTREFADDED = Item(6, """
        Bug External Reference Added

        """)

    BUGCVEREFADDED = Item(7, """
        Bug CVE Reference Added

        """)

    BUGFIXED = Item(8, """
        Bug Status Changed to FIXED

        """)

    BUGTASKCREATED = Item(9, """
        New Bug Task Created

        """)

    TRANSLATIONTEMPLATEIMPORT = Item(10, """
        Translation Template Import

        """)

    TRANSLATIONIMPORTUPSTREAM = Item(11, """
        Import Upstream Translation

        """)

    TRANSLATIONTEMPLATEDESCRIPTIONCHANGED = Item(12, """
        Translation Template Description Changed

        """)

    TRANSLATIONSUGGESTIONADDED = Item(13, """
        Translation Suggestion Added

        """)

    TRANSLATIONSUGGESTIONAPPROVED = Item(14, """
        Translation Suggestion Approved

        """)

    TRANSLATIONREVIEW = Item(15, """
        Translation Review

        """)

    BUGREJECTED = Item(16, """
        Bug Status Changed to REJECTED

        """)

    BUGACCEPTED = Item(17, """
        Bug Status Changed to ACCEPTED

        """)

    BUGTASKSEVERITYCHANGED = Item(18, """
        Change the Severity of a Bug Task

        """)

    BUGTASKPRIORITYCHANGED = Item(19, """
        Change the Priority of a Bug Task

        """)

    BUGMARKEDASDUPLICATE = Item(20, """
        Mark a Bug as a Duplicate

        """)

    BUGWATCHADDED = Item(21, """
        New Bug Watch Added

        """)


class KarmaActionCategory(DBSchema):
    """The class of an action that gives karma to a user.

    This schema documents the different classes of actions that can result
    in Karma assigned to a person. A person have a list of assigned Karmas,
    each of these Karma entries have a KarmaAction and each of these actions
    have a Class, which is represented by one of the following items.
    """

    MISC = Item(1, """
        Miscellaneous

        Any action that doesn't fit into any other class.
    """)

    BUGS = Item(2, """
        Bugs

        All actions related to bugs.
    """)

    TRANSLATIONS = Item(3, """
        Translations

        All actions related to translations.
    """)

    BOUNTIES = Item(4, """
        Bounties

        All actions related to bounties.
    """)

    HATCHERY = Item(5, """
        Hatchery

        All actions related to the Hatchery.
    """)


class SSHKeyType(DBSchema):
    """SSH key type

    SSH (version 2) can use RSA or DSA keys for authentication.  See OpenSSH's
    ssh-keygen(1) man page for details.
    """

    RSA = Item(1, """
        RSA

        RSA
        """)

    DSA = Item(2, """
        DSA

        DSA
        """)

class LoginTokenType(DBSchema):
    """Login token type

    Tokens are emailed to users in workflows that require email address
    validation, such as forgotten password recovery or account merging.
    We need to identify the type of request so we know what workflow
    is being processed.
    """

    PASSWORDRECOVERY = Item(1, """
        Password Recovery

        User has forgotten or never known their password and need to
        reset it.
        """)

    ACCOUNTMERGE = Item(2, """
        Account Merge

        User has requested that another account be merged into their
        current one.
        """)

    NEWACCOUNT = Item(3, """
        New Account

        A new account is being setup. They need to verify their email address
        before we allow them to set a password and log in.
        """)

    VALIDATEEMAIL = Item(4, """
        Validate Email

        A user has added more email addresses to their account and they
        need to be validated.
        """)

    VALIDATETEAMEMAIL = Item(5, """
        Validate Team Email

        One of the team administrators is trying to add a contact email
        address for the team, but this address need to be validated first.
        """)

    VALIDATEGPG = Item(6, """
        Validate GPG key 

        A user has submited a new GPG key to his account and it need to
        be validated.
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
        Fully built

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
        Manual dependency wait

        Build record represents a package whose build dependencies cannot
        currently be satisfied within the relevant DistroArchRelease. This
        build will have to be manually given back (put into 'NEEDSBUILD') when
        the dependency issue is resolved.
        """)

    CHROOTWAIT = Item(4, """
        Chroot wait

        Build record represents a build which needs a chroot currently known
        to be damaged or bad in some way. The buildd maintainer will have to
        reset all relevant CHROOTWAIT builds to NEEDSBUILD after the chroot
        has been fixed.
        """)

class MirrorFreshness(DBSchema):
    """ Mirror Freshness

    This valeu indicates how up-to-date Mirror is.
    """

    UNKNOWN = Item(99, """
        Freshness Unknown

        The Freshness was never verified and is unknown.
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


class RosettaFileFormat(DBSchema):
    """Rosetta File Format

    This is an enumeration of the different sorts of file that Rosetta can
    export.
    """

    PO = Item(1, """
        PO format

        Gettext's standard text file format.
        """)

    MO = Item(2, """
        MO format

        Gettext's standard binary file format.
        """)

    XLIFF = Item(3, """
        XLIFF

        OASIS's XML Localisation Interchange File Format.
        """)

    CSHARP_DLL = Item(4, """
        .NET DLL

        The dynamic link library format as used by programs that use the .NET
        framework.
        """)

    CSHARP_RESOURCES = Item(5, """
        .NET resource file

        The resource file format used by programs that use the .NET framework.
        """)

    TCL = Item(6, """
        TCL format

        The .msg format as used by TCL/msgcat.
        """)

    QT = Item(7, """
        QT format

        The .qm format as used by programs using the QT toolkit.
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


class ShipItFlavour(DBSchema):
    """The Distro Flavour, used only to link with ShippingRequest."""

    UBUNTU = Item(1, """
        Ubuntu

        The Ubuntu flavour.
        """)


class ShipItArchitecture(DBSchema):
    """The Distro Architecture, used only to link with ShippingRequest."""

    X86 = Item(1, """
        Intel/X86

        x86 processors.
        """)

    AMD64 = Item(2, """
        AMD64

        AMD64 or EM64T based processors.
        """)

    PPC = Item(3, """
        PowerPC

        PowerPC processors.
        """)


class ShipItDistroRelease(DBSchema):
    """The Distro Release, used only to link with ShippingRequest."""

    BREEZY = Item(1, """
        Breezy Badger

        The Breezy Badger release.
        """)

