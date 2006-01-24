# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Milestone interfaces."""

__metaclass__ = type

__all__ = [
    'IMilestone',
    'IMilestoneSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, TextLine, Int, Date, Bool
from zope.component import getUtility

from canonical.launchpad.interfaces import IHasProduct
from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad import _
from canonical.launchpad.fields import ContentNameField
from canonical.launchpad.validators.name import name_validator


class MilestoneNameField(ContentNameField):

    @property
    def _content_iface(self):
        return IMilestone
    
    def _getByName(self, name):
        context = self.context
        milestoneset = getUtility(IMilestoneSet)
        if IMilestone.providedBy(context):
            if self.context.product is not None:
                context = context.product
                milestone = milestoneset.getByNameAndProduct(name, context)
            else:
                context = context.distribution
                milestone = milestoneset.getByNameAndDistribution(name,
                        context)
        elif IProduct.providedBy(context):
            milestone = milestoneset.getByNameAndProduct(name, context)
        else:
            milestone = milestoneset.getByNameAndDistribution(name, context)
        if milestone is not None:
              self.errormessage = _(
                  "The name %%s is already used by a milestone in %s."
                  % context.displayname)
        return milestone


class IMilestone(IHasProduct):
    """A milestone, or a targeting point for bugs and other release-related
    items that need coordination.
    """
    id = Int(title=_("Id"))
    name = MilestoneNameField(
        title=_("Name"),
        description=_(
            "Only letters, numbers, and simple punctuation are allowed."),
        required=True,
        constraint=name_validator)
    product = Choice(
        title=_("Product"),
        description=_("The product to which this milestone is associated"),
        vocabulary="Product")
    distribution = Choice(title=_("Distribution"),
        description=_("The distribution to which this milestone belongs."),
        vocabulary="Distribution")
    dateexpected = Date(title=_("Date Targeted"), required=False,
        description=_("Example: 2005-11-24"))
    visible = Bool(title=_("Active"), description=_("Whether or not this "
        "milestone should be shown in web forms for bug targeting."))
    target = Attribute("The product or distribution of this milestone.")
    displayname = Attribute("A displayname for this milestone, constructed "
        "from the milestone name.")
    title = Attribute("A milestone context title for pages.")
    bugtasks = Attribute("A list of the bug tasks targeted to this "
        "milestone.")
    specifications = Attribute("A list of the specifications targeted to "
        "this milestone.")


class IMilestoneSet(Interface):
    def __iter__():
        """Return an iterator over all the milestones for a thing."""

    def get(milestoneid):
        """Get a milestone by its id.

        If the milestone with that ID is not found, a
        zope.exceptions.NotFoundError will be raised.
        """

    def getByNameAndProduct(self, name, product, default=None):
        """Get a milestone by its name and product.

        If no milestone is found, default will be returned. 
        """

    def getByNameAndDistribution(self, name, distribution, default=None):
        """Get a milestone by its name and distribution.

        If no milestone is found, default will be returned.
        """

    def new(product, name, title):
        """Create a new milestone for a product.

        name and title are (currently) required."""
