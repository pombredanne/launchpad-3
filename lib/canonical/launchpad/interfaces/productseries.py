

# Zope schema imports
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IProductSeries(Interface):
    """A series of releases. For example "2.0" or "1.3" or "dev"."""
    # XXX Mark Shuttleworth 14/10/04 would like to get rid of id in
    # interfaces, as soon as SQLobject allows using the object directly
    # instead of using object.id.
    id = Int(title=_('ID'))
    # field names
    product = Choice( title=_('Product'), required=True,
                      vocabulary='Product')
    name = Text(title=_('Name'), required=True)
    title = Attribute('Title')
    displayname = Text( title=_('Display Name'), required=True)
    summary = Text(title=_("Summary"), required=True)
    # convenient joins
    releases = Attribute("An iterator over the releases in this "
        "Series, sorted with latest release first.")

    # properties
    sourcepackages = Attribute(_("List of distribution packages for this \
        product series"))

    def getRelease(version):
        """Get the release in this series that has the specified version."""

    def getPackage(distrorelease):
        """Return the SourcePackage for this productseries in the supplied
        distrorelease."""


class ISeriesSource(Interface):
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
    
    def namesReviewed():
        """Return True if the product and project details have been reviewed
        and are still active."""


class ISeriesSourceAdmin(Interface):
    """Administrative interface to approve syncing on a Product Series
    upstream codebase, publishing it as Bazaar branch."""

    def certifyForSync():
        """enable this to sync"""

    def enableAutoSync():
        """enable this sourcesource for automatic syncronisation"""
    

class IProductSeriesSet(Interface):
    """A set of ProductSeries objects. Note that it can be restricted by
    initialising it with a product, in which case it iterates over only the
    Product Release Series' for that Product."""

    def __iter__():
        """Return an interator over the ProductSeries', constrained by
        self.product if the ProductSeries was initialised that way."""

    def __getitem__(name):
        """Return a specific ProductSeries, by name, constrained by the
        self.product. For __getitem__, a self.product is absolutely
        required, as ProductSeries names are only unique within the Product
        they cover."""

    def _querystr(ready=None, text=None, forimport=None, importstatus=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query. Arguments:
          ready - boolean indicator of whether or not to limit the search
                  to products and projects that have been reviewed and are
                  active.
          text - text to search for in the product and project titles and
                 descriptions
          forimport - whether or not to limit the search to series which
                      have RCS data on file
          importstatus - limit the list to series which have the given
                         import status.
        """

    def search(ready=None, text=None, forimport=None, importstatus=None,
               start=None, length=None):
        """return a list of series matching the arguments, which are passed
        through to _querystr to generate the query."""

    def importcount(status=None):
        """Return the number of series that are in the process of being
        imported and published as baz branches. If status is None then all
        the statuses are included, otherwise the count reflects the number
        of branches with that importstatus."""

