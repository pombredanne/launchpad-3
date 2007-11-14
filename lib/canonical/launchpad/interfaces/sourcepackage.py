# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Source package interfaces."""

__metaclass__ = type

__all__ = [
    'ISourcePackage',
    'SourcePackageFileType',
    'SourcePackageFormat',
    'SourcePackageRelationships',
    'SourcePackageUrgency',
    ]

from zope.interface import Attribute
from zope.schema import Object

from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.component import IComponent
from canonical.lazr import DBEnumeratedType, DBItem


class ISourcePackage(IBugTarget):
    """A SourcePackage. See the MagicSourcePackage specification. This
    interface preserves as much as possible of the old SourcePackage
    interface from the SourcePackage table, with the new table-less
    implementation."""

    id = Attribute("ID")

    name = Attribute("The text name of this source package, from "
                     "SourcePackageName.")

    displayname = Attribute("A displayname, constructed, for this package")

    title = Attribute("Title")

    format = Attribute("Source Package Format. This is the format of the "
                "current source package release for this name in this "
                "distribution or distroseries. Calling this when there is "
                "no current sourcepackagerelease will raise an exception.")

    distinctreleases = Attribute("Return a distinct list "
        "of sourcepackagepublishinghistory for this source package.")

    distribution = Attribute("Distribution")

    distroseries = Attribute("The DistroSeries for this SourcePackage")

    sourcepackagename = Attribute("SourcePackageName")

    bugtasks = Attribute("Bug Tasks that reference this Source Package name "
                    "in the context of this distribution.")

    product = Attribute("The best guess we have as to the Launchpad Project "
                    "associated with this SourcePackage.")

    productseries = Attribute("The best guess we have as to the Launchpad "
                    "ProductSeries for this Source Package. Try find "
                    "packaging information for this specific distroseries "
                    "then try parent series and previous ubuntu series.")

    releases = Attribute("The full set of source package releases that "
        "have been published in this distroseries under this source "
        "package name. The list should be sorted by version number.")

    currentrelease = Attribute("""The latest published SourcePackageRelease
        of a source package with this name in the distribution or
        distroseries, or None if no source package with that name is
        published in this distroseries.""")

    direct_packaging = Attribute("Return the Packaging record that is "
        "explicitly for this distroseries and source package name, "
        "or None if such a record does not exist. You should probably "
        "use ISourcePackage.packaging, which will also look through the "
        "distribution ancestry to find a relevant packaging record.")

    packaging = Attribute("The best Packaging record we have for this "
        "source package. If we have one for this specific distroseries "
        "and sourcepackagename, it will be returned, otherwise we look "
        "for a match in parent and ubuntu distro seriess.")

    published_by_pocket = Attribute("The set of source package releases "
        "currently published in this distro series, organised by "
        "pocket. The result is a dictionary, with the pocket dbschema "
        "as a key, and a list of source package releases as the value.")

    def __getitem__(version):
        """Return the source package release with the given version in this
        distro series, or None."""

    def __eq__(other):
        """Sourcepackage comparison method.

        Sourcepackages compare equal only if their distroseries and
        sourcepackagename compare equal.
        """

    def __ne__(other):
        """Sourcepackage comparison method.

        Sourcepackages compare not equal if either of their distroseries or
        sourcepackagename compare not equal.
        """

    def setPackaging(productseries, owner):
        """Update the existing packaging record, or create a new packaging
        record, that links the source package to the given productseries,
        and record that it was done by the owner.
        """

    shouldimport = Attribute("""Whether we should import this or not.
        By 'import' we mean sourcerer analysis resulting in a manifest and a
        set of Bazaar branches which describe the source package release.
        The attribute is True or False.""")

    latest_published_component = Object(
        title=u'The component in which the package was last published.',
        schema=IComponent, readonly=True, required=False)


class SourcePackageFileType(DBEnumeratedType):
    """Source Package File Type

    Launchpad tracks files associated with a source package release. These
    files are stored on one of the inner servers, and a record is kept in
    Launchpad's database of the file's name and location. This schema
    documents the files we know about.
    """

    EBUILD = DBItem(1, """
        Ebuild File

        This is a Gentoo Ebuild, the core file that Gentoo uses as a source
        package release. Typically this is a shell script that pulls in the
        upstream tarballs, configures them and builds them into the
        appropriate locations.  """)

    SRPM = DBItem(2, """
        Source RPM

        This is a Source RPM, a normal RPM containing the needed source code
        to build binary packages. It would include the Spec file as well as
        all control and source code files.  """)

    DSC = DBItem(3, """
        DSC File

        This is a DSC file containing the Ubuntu source package description,
        which in turn lists the orig.tar.gz and diff.tar.gz files used to
        make up the package.  """)

    ORIG = DBItem(4, """
        Orig Tarball

        This file is an Ubuntu "orig" file, typically an upstream tarball or
        other lightly-modified upstreamish thing.  """)

    DIFF = DBItem(5, """
        Diff File

        This is an Ubuntu "diff" file, containing changes that need to be
        made to upstream code for the packaging on Ubuntu. Typically this
        diff creates additional directories with patches and documentation
        used to build the binary packages for Ubuntu.  """)

    TARBALL = DBItem(6, """
        Tarball

        This is a tarball, usually of a mixture of Ubuntu and upstream code,
        used in the build process for this source package.  """)


class SourcePackageFormat(DBEnumeratedType):
    """Source Package Format

    Launchpad supports distributions that use source packages in a variety
    of source package formats. This schema documents the types of source
    package format that we understand.
    """

    DPKG = DBItem(1, """
        The DEB Format

        This is the source package format used by Ubuntu, Debian, Linspire
        and similar distributions.
        """)

    RPM = DBItem(2, """
        The RPM Format

        This is the format used by Red Hat, Mandrake, SUSE and other similar
        distributions.
        """)

    EBUILD = DBItem(3, """
        The Ebuild Format

        This is the source package format used by Gentoo.
        """)


class SourcePackageRelationships(DBEnumeratedType):
    """Source Package Relationships

    Launchpad tracks many source packages. Some of these are related to one
    another. For example, a source package in Ubuntu called "apache2" might
    be related to a source package in Mandrake called "httpd". This schema
    defines the relationships that Launchpad understands.
    """

    REPLACES = DBItem(1, """
        Replaces

        The subject source package was designed to replace the object source
        package.  """)

    REIMPLEMENTS = DBItem(2, """
        Reimplements

        The subject source package is a completely new packaging of the same
        underlying products as the object package.  """)

    SIMILARTO = DBItem(3, """
        Similar To

        The subject source package is similar, in that it packages software
        that has similar functionality to the object package.  For example,
        postfix and exim4 would be "similarto" one another.  """)

    DERIVESFROM = DBItem(4, """
        Derives From

        The subject source package derives from and tracks the object source
        package. This means that new uploads of the object package should
        trigger a notification to the maintainer of the subject source
        package.  """)

    CORRESPONDSTO = DBItem(5, """
        Corresponds To

        The subject source package includes the same products as the object
        source package, but for a different distribution. For example, the
        "apache2" Ubuntu package "correspondsto" the "httpd2" package in Red
        Hat.  """)


class SourcePackageUrgency(DBEnumeratedType):
    """Source Package Urgency

    When a source package is released it is given an "urgency" which tells
    distributions how important it is for them to consider bringing that
    package into their archives. This schema defines the possible values
    for source package urgency.
    """

    LOW = DBItem(1, """
        Low Urgency

        This source package release does not contain any significant or
        important updates, it might be a cleanup or documentation update
        fixing typos and speling errors, or simply a minor upstream
        update.
        """)

    MEDIUM = DBItem(2, """
        Medium Urgency

        This package contains updates that are worth considering, such
        as new upstream or packaging features, or significantly better
        documentation.
        """)

    HIGH = DBItem(3, """
        Very Urgent

        This update contains updates that fix security problems or major
        system stability problems with previous releases of the package.
        Administrators should urgently evaluate the package for inclusion
        in their archives.
        """)

    EMERGENCY = DBItem(4, """
        Critically Urgent

        This release contains critical security or stability fixes that
        affect the integrity of systems using previous releases of the
        source package, and should be installed in the archive as soon
        as possible after appropriate review.
        """)
