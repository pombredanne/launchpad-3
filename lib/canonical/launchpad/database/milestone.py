__metaclass__ = type

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import ForeignKey, StringCol, AND, SQLObjectNotFound

from canonical.launchpad.interfaces.milestone import IMilestone, \
    IMilestoneSet
from canonical.database.sqlbase import SQLBase

class Milestone(SQLBase):
    implements(IMilestone)

    product = ForeignKey(dbName = "product", foreignKey = 'Product')
    name = StringCol(notNull = True, alternateID=True)
    title = StringCol(notNull = True)

class MilestoneSet:
    implements(IMilestoneSet)

    def __iter__(self):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""

    def get(self, milestoneid):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        try:
            return Milestone.get(milestoneid)
        except SQLObjectNotFound, err:
            raise NotFoundError(
                "Milestone with ID %d does not exist" % milestoneid)

    def new(self, product, name, title):
        """See canonical.launchpad.interfaces.milestone.IMilestoneSet."""
        return Milestone(productID = product.id, name = name, title = title)
        

# XXX: Brad Bollenbach, 2005-02-02: A milestone set specific to products
# should probably go away by the time take a second pass through this
# code whilst implementing mpt's UI foo.
#
# Unless you have an amazingly good reason not to, READ milestone.txt FOR
# THE CORRECT WAY TO USE MILESTONES.
class ProductMilestoneSet:
    implements(IMilestoneSet)

    def __init__(self, product):
        self.product = product

    def __iter__(self):
        for milestone in self.product.milestones:
            yield milestone

    def __getitem__(self, name):
        milestones = Milestone.select(AND(
            Milestone.q.productID == self.product.id,
            Milestone.q.name == name))

        if milestones.count():
            return milestones[0]

        raise KeyError(name)

def ProductMilestoneFactory(*args, **kwargs):
    return Milestone(
        productID = kwargs['product'], name = kwargs['name'],
        title = kwargs['title'])
