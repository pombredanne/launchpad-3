# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Milestone interfaces."""

__metaclass__ = type

__all__ = [
    'ICanGetMilestonesDirectly',
    'IHasMilestones',
    'IMilestone',
    'IMilestoneSet',
    'IProjectMilestone',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Date, Int, TextLine

from lp.registry.interfaces.productrelease import IProductRelease
from canonical.launchpad.interfaces.bugtarget import IHasBugs
from canonical.launchpad.interfaces.bugtask import IBugTask
from canonical.launchpad import _
from canonical.launchpad.fields import (
    ContentNameField, Description
    )
from canonical.launchpad.validators.name import name_validator

from canonical.lazr.fields import CollectionField, Reference
from canonical.lazr.rest.declarations import (
    call_with, export_as_webservice_entry, export_factory_operation, exported,
    export_operation_as, export_write_operation, rename_parameters_as,
    REQUEST_USER)


class MilestoneNameField(ContentNameField):
    """A field that can get the milestone from different contexts."""

    @property
    def _content_iface(self):
        """The interface this field manages."""
        return IMilestone

    def _getByName(self, name):
        """Return the named milestone from the context."""
        # IProductSeries and IDistroSeries are imported here to
        # avoid an import loop.
        from lp.registry.interfaces.productseries import (
            IProductSeries)
        from lp.registry.interfaces.distroseries import IDistroSeries
        if IMilestone.providedBy(self.context):
            milestone = self.context.target.getMilestone(name)
        elif IProductSeries.providedBy(self.context):
            milestone = self.context.product.getMilestone(name)
        elif IDistroSeries.providedBy(self.context):
            milestone = self.context.distribution.getMilestone(name)
        else:
            raise AssertionError, (
                'Editing a milestone in an unexpected context: %r'
                % self.context)
        if milestone is not None:
            self.errormessage = _(
                "The name %%s is already used by a milestone in %s."
                % milestone.target.displayname)
        return milestone


class IMilestone(IHasBugs):
    """A milestone, or a targeting point for bugs and other
    release-management items that need coordination.
    """
    export_as_webservice_entry()

    id = Int(title=_("Id"))
    name = exported(
        MilestoneNameField(
            title=_("Name"),
            description=_(
                "Only letters, numbers, and simple punctuation are allowed."),
            constraint=name_validator))
    product = Choice(
        title=_("Project"),
        description=_("The project to which this milestone is associated"),
        vocabulary="Product")
    distribution = Choice(title=_("Distribution"),
        description=_("The distribution to which this milestone belongs."),
        vocabulary="Distribution")
    productseries = Choice(
        title=_("Product Series"),
        description=_("The product series for which this is a milestone."),
        vocabulary="FilteredProductSeries",
        required=False) # for now
    distroseries = Choice(
        title=_("Distro Series"),
        description=_(
            "The distribution series for which this is a milestone."),
        vocabulary="FilteredDistroSeries",
        required=False) # for now
    dateexpected = exported(
        Date(title=_("Date Targeted"), required=False,
             description=_("Example: 2005-11-24")),
        exported_as='date_targeted')
    active = exported(
        Bool(
            title=_("Active"),
            description=_("Whether or not this milestone should be shown "
                          "in web forms for bug targeting.")),
        exported_as='is_active')
    summary = exported(
        Description(
            title=_("Summary"),
            required=False,
            description=_(
                "A summary of the features and status of this milestone.")))
    target = exported(
        Reference(
            schema=Interface, # IHasMilestones
            title=_("The product or distribution of this milestone."),
            required=False))
    series_target = exported(
        Reference(
            schema=Interface, # IHasMilestones
            title=_("The productseries or distroseries of this milestone."),
            required=False))
    displayname = Attribute("A displayname for this milestone, constructed "
        "from the milestone name.")
    title = exported(
        TextLine(title=_("A milestone context title for pages."),
                 readonly=True))
    specifications = Attribute("A list of the specifications targeted to "
        "this milestone.")

    code_name = Attribute("An alternative to the name attribute.")

    product_release = Reference(
        schema=IProductRelease,
        title=_("The release for this milestone."),
        required=False,
        readonly=True)

    @call_with(owner=REQUEST_USER)
    @rename_parameters_as(datereleased='date_released')
    @export_factory_operation(
        IProductRelease,
        ['datereleased', 'changelog', 'release_notes'])
    def createProductRelease(owner, datereleased,
                             changelog=None, release_notes=None):
        """Create a new ProductRelease.

        :param owner: `IPerson` object who manages the release.
        :param datereleased: Date of the product release.
        :param changelog: Detailed changes in each version.
        :param release_notes: Overview of changes in each version.
        :returns: `IProductRelease` object.
        """

    @export_write_operation()
    @export_operation_as('delete')
    def destroySelf():
        """Delete this milestone.

        This method must not be used if this milestone has a product
        release.
        """

# Avoid circular imports
IBugTask['milestone'].schema = IMilestone


class IMilestoneSet(Interface):
    """An set provides access `IMilestone`s."""

    def __iter__():
        """Return an iterator over all the milestones for a thing."""

    def get(milestoneid):
        """Get a milestone by its id.

        If the milestone with that ID is not found, a
        NotFoundError will be raised.
        """

    def getByNameAndProduct(name, product, default=None):
        """Get a milestone by its name and product.

        If no milestone is found, default will be returned.
        """

    def getByNameAndDistribution(name, distribution, default=None):
        """Get a milestone by its name and distribution.

        If no milestone is found, default will be returned.
        """


class IProjectMilestone(IMilestone):
    """A marker interface for milestones related to a project"""


class IHasMilestones(Interface):
    """An interface for classes providing milestones."""
    export_as_webservice_entry()

    milestones = exported(
        CollectionField(
            title=_("The visible and active milestones associated with this "
                    "object, ordered by date expected."),
            value_type=Reference(schema=IMilestone)),
        exported_as='active_milestones')

    all_milestones = exported(
        CollectionField(
            title=_("All milestones associated with this object, ordered by "
                    "date expected."),
            value_type=Reference(schema=IMilestone)))


class ICanGetMilestonesDirectly(Interface):
    """ An interface for classes providing getMilestone(name)."""

    def getMilestone(name):
        """Return a milestone with the given name for this object, or None."""


# Fix cyclic references.
IMilestone['target'].schema = IHasMilestones
IMilestone['series_target'].schema = IHasMilestones
IProductRelease['milestone'].schema = IMilestone
