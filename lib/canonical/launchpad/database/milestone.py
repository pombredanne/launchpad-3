__metaclass__ = type

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, AND

from canonical.launchpad.interfaces import IAuthorization
from canonical.launchpad.interfaces.milestone import IMilestone, \
    IMilestoneSet
from canonical.database.sqlbase import SQLBase

class Milestone(SQLBase):
    implements(IMilestone)

    product = ForeignKey(dbName = "product", foreignKey = 'Product')
    name = StringCol(notNull = True)
    title = StringCol(notNull = True)

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
