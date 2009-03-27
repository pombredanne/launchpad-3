# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Product series interfaces."""

__metaclass__ = type

__all__ = [
    'IProductSeries',
    'IProductSeriesEditRestricted',
    'IProductSeriesPublic',
    'IProductSeriesSet',
    'NoSuchProductSeries',
    ]

from zope.schema import Choice, Datetime, Int, Text, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad.fields import (
    ContentNameField, PublicPersonChoice, Title)
from canonical.launchpad.interfaces.branch import IBranch
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
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)
from canonical.launchpad.interfaces.validation import validate_url
from canonical.launchpad.validators import LaunchpadValidationError

from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.webapp.interfaces import NameLookupFailed
from canonical.launchpad import _

from canonical.lazr.fields import CollectionField, Reference, ReferenceChoice
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, export_factory_operation, exported,
    rename_parameters_as)


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


def validate_release_glob(value):
    if validate_url(value, ["http", "https", "ftp"]):
        return True
    else:
        raise LaunchpadValidationError('Invalid release URL pattern.')


class IProductSeriesEditRestricted(Interface):
    """IProductSeries properties which require launchpad.Edit."""

    @rename_parameters_as(dateexpected='date_targeted')
    @export_factory_operation(IMilestone,
                              ['name', 'dateexpected', 'summary', 'code_name'])
    def newMilestone(name, dateexpected=None, summary=None, code_name=None):
        """Create a new milestone for this ProjectSeries."""


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

    branch = exported(
        ReferenceChoice(
            title=_('Branch'),
            vocabulary='BranchRestrictedOnProduct',
            schema=IBranch,
            required=False,
            description=_("The Bazaar branch for this series.  Leave blank "
                          "if this series is not maintained in Bazaar.")))

    user_branch = Attribute(
        _("Backwards compatibility shim for IProductSeries.branch"))

    series_branch = Attribute(
        _("Backwards compatibility shim for IProductSeries.branch"))

    translations_autoimport_mode = Choice(
        title=_('Import mode'),
        vocabulary=TranslationsBranchImportMode,
        required=True,
        description=_("Specify which files will be imported from the "
                      "source code branch."))

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

    # where are the tarballs released from this branch placed?
    releasefileglob = TextLine(title=_("Release URL pattern"),
        required=False, constraint=validate_release_glob,
        description=_('A URL pattern that matches releases that are part '
                      'of this series.  Launchpad automatically scans this '
                      'site to import new releases.  Example: '
                      'http://ftp.gnu.org/gnu/emacs/emacs-21.*.tar.gz'))
    releaseverstyle = Attribute("The version numbering style for this "
        "series of releases.")

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

    def getSeriesForBranches(branches):
        """Return the ProductSeries associated with a branch in branches."""


class NoSuchProductSeries(NameLookupFailed):
    """Raised when we try to find a product that doesn't exist."""

    _message_prefix = "No such product series"

    def __init__(self, name, product, message=None):
        NameLookupFailed.__init__(self, name, message)
        self.product = product
