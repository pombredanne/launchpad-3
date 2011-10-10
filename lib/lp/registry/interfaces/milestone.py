# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Milestone interfaces."""

__metaclass__ = type

__all__ = [
    'ICanGetMilestonesDirectly',
    'IHasMilestones',
    'IMilestone',
    'IMilestoneSet',
    'IMilestoneBugtaskListingBatchNavigator',
    'IMilestoneSpecificationListingBatchNavigator',
    'IProjectGroupMilestone',
    ]

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_destructor_operation,
    export_factory_operation,
    export_operation_as,
    export_read_operation,
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    rename_parameters_as,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Int,
    TextLine,
    )

from canonical.launchpad import _
from canonical.launchpad.components.apihelpers import (
    patch_plain_parameter_type,
    )
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator
from lp.app.validators.name import name_validator
from lp.bugs.interfaces.bugtarget import (
    IHasBugs,
    IHasOfficialBugTags,
    )
from lp.bugs.interfaces.bugtask import IBugTask
from lp.bugs.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget,
    )
from lp.registry.interfaces.productrelease import IProductRelease
from lp.services.fields import (
    ContentNameField,
    FormattableDate,
    NoneableDescription,
    NoneableTextLine,
    )


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
            raise AssertionError(
                'Editing a milestone in an unexpected context: %r'
                % self.context)
        if milestone is not None:
            self.errormessage = _(
                "The name %%s is already used by a milestone in %s."
                % milestone.target.displayname)
        return milestone


class IMilestone(IHasBugs, IStructuralSubscriptionTarget,
                 IHasOfficialBugTags):
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
    code_name = exported(
        NoneableTextLine(
            title=u'Code name', required=False,
            description=_('An alternative name for the milestone.')))
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
        FormattableDate(title=_("Date Targeted"), required=False,
             description=_("Example: 2005-11-24")),
        exported_as='date_targeted')
    active = exported(
        Bool(
            title=_("Active"),
            description=_("Whether or not this milestone should be shown "
                          "in web forms for bug targeting.")),
        exported_as='is_active')
    summary = exported(
        NoneableDescription(
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

    product_release = exported(
        Reference(
            schema=IProductRelease,
            title=_("The release for this milestone."),
            required=False,
            readonly=True),
        exported_as='release')

    @call_with(owner=REQUEST_USER)
    @rename_parameters_as(datereleased='date_released')
    @export_factory_operation(
        IProductRelease,
        ['datereleased', 'changelog', 'release_notes'])
    @operation_for_version('beta')
    def createProductRelease(owner, datereleased,
                             changelog=None, release_notes=None):
        """Create a new ProductRelease.

        :param owner: `IPerson` object who manages the release.
        :param datereleased: Date of the product release.
        :param changelog: Detailed changes in each version.
        :param release_notes: Overview of changes in each version.
        :returns: `IProductRelease` object.
        """

    def closeBugsAndBlueprints(user):
        """Close completed bugs and blueprints.

        Bugs that are fix committed status are updated to fix released.
        Blueprints that are in deployment status are updated to implemented
        status.
        XXX sinzui 2010-01-27 bug=341687: blueprints not yet implemented.
        """

    @export_destructor_operation()
    @export_operation_as('delete')
    @operation_for_version('beta')
    def destroySelf():
        """Delete this milestone.

        This method must not be used if this milestone has a product
        release.
        """

# Avoid circular imports
IBugTask['milestone'].schema = IMilestone
patch_plain_parameter_type(
    IBugTask, 'transitionToMilestone', 'new_milestone', IMilestone)


class IMilestoneSet(Interface):
    """An set provides access `IMilestone`s."""

    def __iter__():
        """Return an iterator over all the milestones for a thing."""

    def get(milestoneid):
        """Get a milestone by its id.

        If the milestone with that ID is not found, a
        NotFoundError will be raised.
        """

    def getByIds(milestoneids):
        """Get the milestones for milestoneids."""

    def getByNameAndProduct(name, product, default=None):
        """Get a milestone by its name and product.

        If no milestone is found, default will be returned.
        """

    def getByNameAndDistribution(name, distribution, default=None):
        """Get a milestone by its name and distribution.

        If no milestone is found, default will be returned.
        """

    def getVisibleMilestones():
        """Return all visible milestones."""


class IProjectGroupMilestone(IMilestone):
    """A marker interface for milestones related to a project"""


class IHasMilestones(Interface):
    """An interface for classes providing milestones."""
    export_as_webservice_entry()

    has_milestones = Bool(title=_("Whether the object has any milestones."))

    milestones = exported(doNotSnapshot(
        CollectionField(
            title=_("The visible and active milestones associated with this "
                    "object, ordered by date expected."),
            value_type=Reference(schema=IMilestone))),
        exported_as='active_milestones')

    all_milestones = exported(doNotSnapshot(
        CollectionField(
            title=_("All milestones associated with this object, ordered by "
                    "date expected."),
            value_type=Reference(schema=IMilestone))))


class ICanGetMilestonesDirectly(Interface):
    """ An interface for classes providing getMilestone(name)."""

    @operation_parameters(
        name=TextLine(title=_("Name"), required=True))
    @operation_returns_entry(IMilestone)
    @export_read_operation()
    @operation_for_version('beta')
    def getMilestone(name):
        """Return a milestone with the given name for this object, or None."""


# Fix cyclic references.
IMilestone['target'].schema = IHasMilestones
IMilestone['series_target'].schema = IHasMilestones
IProductRelease['milestone'].schema = IMilestone

class IMilestoneBugtaskListingBatchNavigator(ITableBatchNavigator):
    """A marker interface for registering the appropriate listings."""

class IMilestoneSpecificationListingBatchNavigator(ITableBatchNavigator):
    """A marker interface for registering the appropriate listings."""
