# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Source package interfaces."""

__metaclass__ = type

__all__ = [
    'ISourcePackage',
    ]

from zope.interface import Attribute

from canonical.launchpad import _
from canonical.launchpad.interfaces.bugtarget import IBugTarget


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
                "distribution or distrorelease. Calling this when there is "
                "no current sourcepackagerelease will raise an exception.")

    changelog = Attribute("Returns the concatenated full changelog for each "
                          "published sourcepackagerelease versions ordered "
                          "by crescent version.")

    manifest = Attribute("The Manifest of the current SourcePackageRelease "
                    "published in this distribution / distrorelease.")

    distribution = Attribute("Distribution")

    distrorelease = Attribute("The DistroRelease for this SourcePackage")

    sourcepackagename = Attribute("SourcePackageName")

    bugtasks = Attribute("Bug Tasks that reference this Source Package name "
                    "in the context of this distribution.")

    product = Attribute("The best guess we have as to the Launchpad Project "
                    "associated with this SourcePackage.")

    productseries = Attribute("The best guess we have as to the Launchpad "
                    "ProductSeries for this Source Package. Try find "
                    "packaging information for this specific distrorelease "
                    "then try parent releases and previous ubuntu releases.")

    releases = Attribute("The full set of source package releases that "
        "have been published in this distrorelease under this source "
        "package name. The list should be sorted by version number.")

    currentrelease = Attribute("""The latest published SourcePackageRelease
        of a source package with this name in the distribution or
        distrorelease, or None if no source package with that name is
        published in this distrorelease.""")

    releasehistory = Attribute("A list of all the source packages ever "
        "published in this Distribution (across all distroreleases) with "
        "this source package name. Note that the list spans "
        "distroreleases, and should be sorted by version number.")

    direct_packaging = Attribute("Return the Packaging record that is "
        "explicitly for this distrorelease and source package name, "
        "or None if such a record does not exist. You should probably "
        "use ISourcePackage.packaging, which will also look through the "
        "distribution ancestry to find a relevant packaging record.")

    packaging = Attribute("The best Packaging record we have for this "
        "source package. If we have one for this specific distrorelease "
        "and sourcepackagename, it will be returned, otherwise we look "
        "for a match in parent and ubuntu distro releases.")

    published_by_pocket = Attribute("The set of source package releases "
        "currently published in this distro release, organised by "
        "pocket. The result is a dictionary, with the pocket dbschema "
        "as a key, and a list of source package releases as the value.")

    potemplates = Attribute(
        _("Return an iterator over this distrorelease/sourcepackagename's "
          "PO templates."))

    currentpotemplates = Attribute(
        _("Return an iterator over this distrorelease/sourcepackagename's "
          "PO templates that have the 'iscurrent' flag set'."))

    def __getitem__(version):
        """Return the source package release with the given version in this
        distro release, or None."""

    def __eq__(other):
        """Sourcepackage comparison method.

        Sourcepackages compare equal only if their distrorelease and
        sourcepackagename compare equal.
        """

    def __ne__(other):
        """Sourcepackage comparison method.

        Sourcepackages compare not equal if either of their distrorelease or
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

