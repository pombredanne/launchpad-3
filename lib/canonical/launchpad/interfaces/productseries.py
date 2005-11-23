# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Product series interfaces."""

__metaclass__ = type

__all__ = [
    'IProductSeries',
    'IProductSeriesSource',
    'IProductSeriesSourceAdmin',
    'IProductSeriesSet',
    'IProductSeriesSubset',
    'IProductSeriesSourceSet',
    ]


from zope.schema import  Choice, Datetime, Int, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.interfaces import ISpecificationTarget

from canonical.launchpad.validators.name import name_validator

_ = MessageIDFactory('launchpad')

class IProductSeries(ISpecificationTarget):
    """A series of releases. For example '2.0' or '1.3' or 'dev'."""
    # XXX Mark Shuttleworth 14/10/04 would like to get rid of id in
    # interfaces, as soon as SQLobject allows using the object directly
    # instead of using object.id.
    id = Int(title=_('ID'))
    # field names
    product = Choice(title=_('Product'), required=True,
                     vocabulary='Product')
    name = TextLine(title=_('Name'), required=True, 
                    description=_("The name of the series is a short, "
                        "unique name that identifies it, being used in "
                        "URLs. It must be all lowercase, with no special "
                        "characters. For example, '2.0' or 'trunk'."),
                    constraint=name_validator)
    datecreated = Datetime(title=_('Date Registered'), required=True,
                           readonly=True)
    title = Attribute('Title')
    displayname = TextLine(title=_('Display Name'),
                           description=_("The 'display name' of the "
                               "Series is a short, capitalized name. It "
                               "should make sense as part of a paragraph "
                               "of text. For example, '2.0 (Stable)' or "
                               "'MAIN (development)' or '1.3 (Obsolete)'."),
                           required=True)
    summary = Text(title=_("Summary"), 
                   description=_('A single paragraph introduction or overview '
                                 'of this series. For example: "The 2.0 '
                                 'series of Apache represents the current '
                                 'stable series, and is recommended for all '
                                 'new deployments".'),
                   required=True)
    datecreated = TextLine(title=_('Date Created'), description=_("""The
        date this productseries was created in Launchpad."""))

    releases = Attribute("An iterator over the releases in this "
        "Series, sorted with latest release first.")
    potemplates = Attribute(
        _("Return an iterator over this productrelease's PO templates."))
    currentpotemplates = Attribute(
        _("Return an iterator over this productrelease's PO templates that "
          "have the 'iscurrent' flag set'."))
    packagings = Attribute("An iterator over the Packaging entries "
        "for this product series.")
    specifications = Attribute("The specifications targeted to this "
        "product series.")
    sourcepackages = Attribute(_("List of distribution packages for this "
        "product series"))

    def getRelease(version):
        """Get the release in this series that has the specified version.
        Return None is there is no such release.
        """

    def getPackage(distrorelease):
        """Return the SourcePackage for this productseries in the supplied
        distrorelease. This will use a Packaging record if one exists, but
        it will also work through the ancestry of the distrorelease to try
        to find a Packaging entry that may be relevant."""

    def setPackaging(distrorelease, sourcepackagename, owner):
        """Create or update a Packaging record for this product series,
        connecting it to the given distrorelease and source package name.
        """

    def getPackagingInDistribution(distribution):
        """Return all the Packaging entries for this product series for the
        given distribution. Note that this only returns EXPLICT packaging
        entries, it does not look at distro release ancestry in the same way
        that IProductSeries.getPackage() does.
        """

    def getPOTemplate(name):
        """Return the POTemplate with this name for the series."""


class IProductSeriesSource(Interface):
    # revision control items
    branch = Attribute("The Bazaar branch for this series. Note that there "
        "may be many branches associated with a given series, such as the "
        "branches of individual tarball releases. This branch is the real "
        "upstream code, mapped into Bazaar from CVS or SVN if upstream "
        "does not already use Bazaar.")
    importstatus = Attribute("The bazaar-import status of upstream "
        "revision control for this series. It can be NULL if we do not "
        "have any revision control data for this series, otherwise it "
        "will reflect our current status for importing and syncing the "
        "upstream code and publishing it as a Bazaar branch.")
    datelastsynced = Attribute("The date on which we last "
        "successfully synced the upstream RCS into the Bazaar branch "
        "in .branch.")
    syncinterval = Attribute("The time between sync attempts for this "
        "series. In some cases we might want to sync once a week, in "
        "others, several times per day.")
    rcstype = Int(title=_("Type of Revision"),
        description=_("The type of revision control used for "
        "the upstream branch of this series. Can be CVS, SVN, BK or "
        "Arch."))
    cvsroot = Text(title=_("The CVS server root at which the upstream "
        "code for this branch can be found."))
    cvsmodule = Text(title=_("The CVS module for this branch."))
    cvstarfileurl = Text(title=_("A URL where a tarball of the CVS "
        "repository can be found. This can sometimes be faster than "
        "trying to query the server for commit-by-commit data."))
    cvsbranch = Text(title=_("The branch of this module that represents "
        "the upstream branch for this series."))
    svnrepository = Text(title=_("The URL for the SVN branch where "
        "the upstream code for this series can be found."))
    # where are the tarballs released from this branch placed?
    releaseroot = Text(title=_("The URL of the root directory for releases "
        "made as part of this series."))
    releasefileglob = Text(title=_("A pattern-matching 'glob' expression "
        "that should match all the releases made as part of this series. "
        "For example, if release tarball filenames take the form "
        "'apache-2.0.35.tar.gz' then the glob would be "
        "'apache-2.0.*.tar.gz'."))
    releaseverstyle = Attribute("The version numbering style for this "
        "product series of releases.")
    # these fields tell us where to publish upstream as bazaar branch
    targetarcharchive = Text(title=_("The Arch archive into which we will "
        "publish this code as a Bazaar branch."))
    targetarchcategory = Text(title=_("The Arch category name to use for "
        "this upstream when we publish it as a Bazaar branch."))
    targetarchbranch = Text(title=_("The Arch branch name for this upstream "
        "code, used when we publish the code as a Bazaar branch."))
    targetarchversion = Text(title=_("The Arch version name to use when "
        "we publish this code as a Bazaar branch."))
    dateautotested = Attribute("The date this upstream passed automatic "
        "testing.")
    datestarted = Attribute("The timestamp when we started the latest "
        "sync attempt on this upstream RCS.")
    datefinished = Attribute("The timestamp when the latest sync attempt "
        "on this upstream RCS finished.")
    dateprocessapproved = Attribute("The date when we approved processing "
        "of this upstream source.")
    datesyncapproved = Attribute("The date when we approved syncing of "
        "this upstream source into a public Bazaar branch.")

    def syncCertified():
        """is the series source sync enabled?"""

    def autoSyncEnabled():
        """is the series source enabled for automatic syncronisation?"""

    def autoTestFailed():
        """has the series source failed automatic testing by roomba?"""
    
    def namesReviewed():
        """Return True if the product and project details have been reviewed
        and are still active."""


class IProductSeriesSourceAdmin(Interface):
    """Administrative interface to approve syncing on a Product Series
    upstream codebase, publishing it as Bazaar branch."""

    def certifyForSync():
        """enable this to sync"""

    def enableAutoSync():
        """enable this series RCS for automatic baz syncronisation"""


class IProductSeriesSubset(Interface):
    """A set of ProductSeries objects for a specific product."""

    def __iter__():
        """Return an interator over the ProductSeries', constrained by
        self.product."""

    def __getitem__(name):
        """Return a specific ProductSeries, by name, constrained by the
        self.product."""


class IProductSeriesSourceSet(Interface):
    """The set of ProductSeries with a view to source imports"""
    def search(ready=None, text=None, forimport=None, importstatus=None,
               start=None, length=None):
        """return a list of series matching the arguments, which are passed
        through to _querystr to generate the query."""

    def importcount(status=None):
        """Return the number of series that are in the process of being
        imported and published as baz branches. If status is None then all
        the statuses are included, otherwise the count reflects the number
        of branches with that importstatus."""

