# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Product series interfaces."""

__metaclass__ = type

__all__ = [
    'ImportStatus',
    'IProductSeries',
    'IProductSeriesEditRestricted',
    'IProductSeriesPublic',
    'IProductSeriesSet',
    'RevisionControlSystems',
    'validate_cvs_module',
    'validate_cvs_root',
    ]

import re

from zope.schema import  Choice, Datetime, Int, Text, TextLine
from zope.interface import Interface, Attribute

from CVS.protocol import CVSRoot, CvsRootError

from canonical.config import config
from canonical.launchpad.fields import (
    ContentNameField, PublicPersonChoice, Title, URIField)
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.distroseries import DistroSeriesStatus
from canonical.launchpad.interfaces.launchpad import (
    IHasAppointedDriver, IHasOwner, IHasDrivers)
from canonical.launchpad.interfaces.milestone import (
    IHasMilestones, IMilestone)
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.interfaces.productrelease import IProductRelease
from canonical.launchpad.interfaces.specificationtarget import (
    ISpecificationGoal)
from canonical.launchpad.interfaces.validation import validate_url

from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad import _

from canonical.lazr.enum import DBEnumeratedType, DBItem
from canonical.lazr.fields import CollectionField, Reference
from canonical.lazr.rest.declarations import (
    call_with, export_as_webservice_entry, export_factory_operation, exported,
    rename_parameters_as, REQUEST_USER)


class ImportStatus(DBEnumeratedType):
    """This schema describes the states that a SourceSource record can take
    on."""

    DONTSYNC = DBItem(1, """
        Do Not Import

        Launchpad will not attempt to make a Bazaar import.
        """)

    TESTING = DBItem(2, """
        Testing

        Launchpad has not yet attempted this import. The vcs-imports operator
        will review the source details and either mark the series \"Do not
        sync\", or perform a test import. If the test import is successful, a
        public import will be created. After the public import completes, it
        will be updated automatically.
        """)

    TESTFAILED = DBItem(3, """
        Test Failed

        The test import has failed. We will do further tests, and plan to
        complete this import eventually, but it may take a long time. For more
        details, you can ask on the %s mailing list
        or on IRC in the #launchpad channel on irc.freenode.net.
        """ % config.launchpad.users_address)

    AUTOTESTED = DBItem(4, """
        Test Successful

        The test import was successful. The vcs-imports operator will lock the
        source details for this series and perform a public Bazaar import.
        """)

    PROCESSING = DBItem(5, """
        Processing

        The public Bazaar import is being created. When it is complete, a
        Bazaar branch will be published and updated automatically. The source
        details for this series are locked and can only be modified by
        vcs-imports members and Launchpad administrators.
        """)

    SYNCING = DBItem(6, """
        Online

        The Bazaar import is published and automatically updated to reflect the
        upstream revision control system. The source details for this series
        are locked and can only be modified by vcs-imports members and
        Launchpad administrators.
        """)

    STOPPED = DBItem(7, """
        Stopped

        The Bazaar import has been suspended and is no longer updated. The
        source details for this series are locked and can only be modified by
        vcs-imports members and Launchpad administrators.
        """)


class RevisionControlSystems(DBEnumeratedType):
    """Revision Control Systems

    Bazaar brings code from a variety of upstream revision control
    systems into bzr. This schema documents the known and supported
    revision control systems.
    """

    CVS = DBItem(1, """
        Concurrent Versions System

        The Concurrent Version System is very widely used among
        older open source projects, it was the first widespread
        open source version control system in use.
        """)

    SVN = DBItem(2, """
        Subversion

        Subversion aims to address some of the shortcomings in
        CVS, but retains the central server bottleneck inherent
        in the CVS design.
        """)


class ProductSeriesNameField(ContentNameField):

    errormessage = _("%s is already in use by another series.")

    @property
    def _content_iface(self):
        return IProductSeries

    def _getByName(self, name):
        if self._content_iface.providedBy(self.context):
            return self.context.product.getSeries(name)
        else:
            return self.context.getSeries(name)


def validate_cvs_root(cvsroot):
    try:
        root = CVSRoot(cvsroot)
    except CvsRootError, e:
        raise LaunchpadValidationError(e)
    if root.method == 'local':
        raise LaunchpadValidationError('Local CVS roots are not allowed.')
    if root.hostname.count('.') == 0:
        raise LaunchpadValidationError(
            'Please use a fully qualified host name.')
    return True


def validate_cvs_module(cvsmodule):
    valid_module = re.compile('^[a-zA-Z][a-zA-Z0-9_/.+-]*$')
    if not valid_module.match(cvsmodule):
        raise LaunchpadValidationError(
            'The CVS module contains illegal characters.')
    if cvsmodule == 'CVS':
        raise LaunchpadValidationError(
            'A CVS module can not be called "CVS".')
    return True


def validate_cvs_branch(branch):
    if branch and re.match('^[a-zA-Z][a-zA-Z0-9_-]*$', branch):
        return True
    else:
        raise LaunchpadValidationError('Your CVS branch name is invalid.')


def validate_release_glob(value):
    if validate_url(value, ["http", "https", "ftp"]):
        return True
    else:
        raise LaunchpadValidationError('Invalid release URL pattern.')


class IProductSeriesEditRestricted(Interface):
    """IProductSeries properties which require launchpad.Edit."""

    @rename_parameters_as(dateexpected='date_targeted')
    @export_factory_operation(IMilestone,
                              ['name', 'dateexpected', 'description'])
    def newMilestone(name, dateexpected=None, description=None):
        """Create a new milestone for this ProjectSeries."""

    @call_with(owner=REQUEST_USER)
    @rename_parameters_as(codename='code_name')
    @export_factory_operation(
        IProductRelease,
        ['version', 'codename', 'summary', 'description', 'changelog'])
    def addRelease(version, owner, codename=None, summary=None,
                   description=None, changelog=None):
        """Create a new ProductRelease.

        :param version: Name of the version.
        :param owner: `IPerson` object who manages the release.
        :param codename: Alternative name of the version.
        :param shortdesc: Summary information.
        :param description: Detailed information.
        :param changelog: Highlighted changes in each version.
        :returns: `IProductRelease` object.
        """


class IProductSeriesPublic(IHasAppointedDriver, IHasDrivers, IHasOwner,
                           IBugTarget, ISpecificationGoal, IHasMilestones):
    """Public IProductSeries properties."""
    # XXX Mark Shuttleworth 2004-10-14: Would like to get rid of id in
    # interfaces, as soon as SQLobject allows using the object directly
    # instead of using object.id.
    id = Int(title=_('ID'))

    product = exported(
        Choice(title=_('Project'), required=True, vocabulary='Product'),
        exported_as='project')

    status = exported(
        Choice(
            title=_('Status'), required=True, vocabulary=DistroSeriesStatus,
            default=DistroSeriesStatus.DEVELOPMENT))

    parent = Attribute('The structural parent of this series - the product')

    name = exported(
        ProductSeriesNameField(
            title=_('Name'),
            description=_(
                "The name of the series is a short, unique name "
                "that identifies it, being used in URLs. It must be all "
                "lowercase, with no special characters. For example, '2.0' "
                "or 'trunk'."),
            constraint=name_validator))

    datecreated = exported(
        Datetime(title=_('Date Registered'),
                 required=True,
                 readonly=True),
        exported_as='date_created')

    owner = exported(
        PublicPersonChoice(
            title=_('Owner'), required=True, vocabulary='ValidOwner',
            description=_('Project owner, either a valid Person or Team')))

    driver = exported(
        PublicPersonChoice(
            title=_("Driver"),
            description=_(
                "The person or team responsible for decisions about features "
                "and bugs that will be targeted to this series. If you don't "
                "nominate someone here, then the owner of this series will "
                "automatically have those permissions."),
            required=False, vocabulary='ValidPersonOrTeam'))

    title = exported(
        Title(
            title=_('Title'),
            description=_("The product series title.  "
                          "Should be just a few words.")))

    displayname = exported(
        TextLine(
            title=_('Display Name'),
            description=_('Display name, in this case we have removed the '
                          'underlying database field, and this attribute '
                          'just returns the name.')),
        exported_as='display_name')

    summary = exported(
        Text(title=_("Summary"),
             description=_('A single paragraph introduction or overview '
                           'of this series. For example: "The 2.0 series '
                           'of Apache represents the current stable series, '
                           'and is recommended for all new deployments".'),
             required=True))

    releases = exported(
        CollectionField(
            title=_("An iterator over the releases in this "
                    "Series, sorted with latest release first."),
            readonly=True,
            value_type=Reference(schema=IProductRelease)))

    release_files = Attribute("An iterator over the release files in this "
        "Series, sorted with latest release first.")

    packagings = Attribute("An iterator over the Packaging entries "
        "for this product series.")

    specifications = Attribute("The specifications targeted to this "
        "product series.")

    sourcepackages = Attribute(_("List of distribution packages for this "
        "product series"))

    milestones = exported(
        CollectionField(
            title=_("The visible milestones associated with this "
                    "project series, ordered by date expected."),
            readonly=True,
            value_type=Reference(schema=IMilestone)),
        exported_as='active_milestones')

    all_milestones = exported(
        CollectionField(
            title=_("All milestones associated with this project series, "
                    "ordered by date expected."),
            readonly=True,
            value_type=Reference(schema=IMilestone)))

    drivers = exported(
        CollectionField(
            title=_(
                'A list of the people or teams who are drivers for this '
                'series. This list is made up of any drivers or owners '
                'from this project series, the project and if it exists, '
                'the relevant project group.'),
            readonly=True,
            value_type=Reference(schema=IPerson)))

    bug_supervisor = CollectionField(
        title=_('Currently just a reference to the project bug '
                'supervisor.'),
        readonly=True,
        value_type=Reference(schema=IPerson))

    security_contact = PublicPersonChoice(
        title=_('Security Contact'),
        description=_('Currently just a reference to the project '
                      'security contact.'),
        required=False, vocabulary='ValidPersonOrTeam')

    # XXX: jamesh 2006-09-05:
    # While it would be more sensible to call this ProductSeries.branch,
    # I've used this name to make sure code that works with the
    # vcs-imports branch (which used to be called branch) doesn't use
    # this attribute by accident.

    series_branch = exported(
        Choice(
            title=_('Series Branch'),
            vocabulary='BranchRestrictedOnProduct',
            readonly=True,
            description=_("The Bazaar branch for this series.")))

    user_branch = Choice(
        title=_('Branch'),
        vocabulary='BranchRestrictedOnProduct',
        required=False,
        description=_("The Bazaar branch for this series.  Leave blank "
                      "if this series is not maintained in Bazaar."))

    def getRelease(version):
        """Get the release in this series that has the specified version.
        Return None is there is no such release.
        """

    def getPackage(distroseries):
        """Return the SourcePackage for this project series in the supplied
        distroseries. This will use a Packaging record if one exists, but
        it will also work through the ancestry of the distroseries to try
        to find a Packaging entry that may be relevant."""

    def setPackaging(distroseries, sourcepackagename, owner):
        """Create or update a Packaging record for this product series,
        connecting it to the given distroseries and source package name.
        """

    def getPackagingInDistribution(distribution):
        """Return all the Packaging entries for this product series for the
        given distribution. Note that this only returns EXPLICT packaging
        entries, it does not look at distro series ancestry in the same way
        that IProductSeries.getPackage() does.
        """

    def getPOTemplate(name):
        """Return the POTemplate with this name for the series."""

    # revision control items
    import_branch = Choice(
        title=_('Import Branch'),
        vocabulary='Branch',
        description=_("The Bazaar branch for this series imported from "
                      "upstream version control. Note that there may be "
                      "many branches associated with a given series, such "
                      "as the branches of individual tarball releases. "
                      "This branch is the real upstream code, mapped into "
                      "Bazaar from CVS or SVN."))
    importstatus = Attribute("The bazaar-import status of upstream "
        "revision control for this series. It can be NULL if we do not "
        "have any revision control data for this series, otherwise it "
        "will reflect our current status for importing and syncing the "
        "upstream code and publishing it as a Bazaar branch.")
    rcstype = Choice(title=_("Type of RCS"),
        required=False, vocabulary=RevisionControlSystems,
        description=_("The type of revision control used for "
        "the upstream branch of this series. Can be CVS or Subversion."))
    cvsroot = TextLine(title=_("Repository"), required=False,
        constraint=validate_cvs_root,
        description=_('The CVSROOT. '
            'Example: :pserver:anonymous@anoncvs.gnome.org:/cvs/gnome'))
    cvsmodule = TextLine(title=_("Module"), required=False,
        constraint=validate_cvs_module,
        description=_('The path to import within the repository.'
            ' Usually, it is the name of the project.'))
    cvstarfileurl = Text(title=_("A URL where a tarball of the CVS "
        "repository can be found. This can sometimes be faster than "
        "trying to query the server for commit-by-commit data."))
    cvsbranch = TextLine(title=_("Branch"), required=False,
        constraint=validate_cvs_branch,
        description=_("The branch in this module."
            " Only MAIN branches are imported."))
    svnrepository = URIField(title=_("Branch"), required=False,
        description=_(
            "The URL of a Subversion trunk, starting with svn:// or"
            " http(s)://. Only trunk branches are imported."),
        allowed_schemes=["http", "https", "svn", "svn+ssh"],
        allow_userinfo=False, # Only anonymous access is supported.
        allow_port=True,
        allow_query=False,    # Query makes no sense in Subversion.
        allow_fragment=False, # Fragment makes no sense in Subversion.
        trailing_slash=False) # See http://launchpad.net/bugs/56357.

    # where are the tarballs released from this branch placed?
    releasefileglob = TextLine(title=_("Release URL pattern"),
        required=False, constraint=validate_release_glob,
        description=_('A URL pattern that matches releases that are part '
                      'of this series.  Launchpad automatically scans this '
                      'site to import new releases.  Example: '
                      'http://ftp.gnu.org/gnu/emacs/emacs-21.*.tar.gz'))
    releaseverstyle = Attribute("The version numbering style for this "
        "series of releases.")
    # Key dates on the road to import happiness
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
    # Controlling the freshness of an import
    syncinterval = Attribute(_("The time between sync attempts for this "
        "series. In some cases we might want to sync once a week, in "
        "others, several times per day."))
    datelastsynced = Attribute(_("The date on which we last "
        "successfully synced the upstream RCS. The date of the currently "
        "published branch data if it is older than "
        "import_branch.last_mirrored"))
    datepublishedsync = Attribute(_("The date of the published code was last "
        "synced, at the time of the last sync."))

    is_development_focus = Attribute(
        _("Is this series the development focus for the product?"))


class IProductSeries(IProductSeriesEditRestricted, IProductSeriesPublic):
    """A series of releases. For example '2.0' or '1.3' or 'dev'."""
    export_as_webservice_entry('project_series')



class IProductSeriesSet(Interface):
    """Interface representing the set of ProductSeries."""

    def __getitem__(series_id):
        """Return the ProductSeries with the given id.

        Raise NotFoundError if there is no such series.
        """

    def get(series_id, default=None):
        """Return the ProductSeries with the given id.

        Return the default value if there is no such series.
        """

    def getByCVSDetails(cvsroot, cvsmodule, cvsbranch, default=None):
        """Return the ProductSeries with the given CVS details.

        Return the default value if there is no ProductSeries with the
        given details.
        """

    def getBySVNDetails(svnrepository, default=None):
        """Return the ProductSeries with the given SVN details.

        Return the default value if there is no ProductSeries with the
        given details.
        """

    def getSeriesForBranches(branches):
        """Return the ProductSeries associated with a branch in branches."""
