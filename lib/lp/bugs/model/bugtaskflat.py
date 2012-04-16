from storm.locals import (
    Bool,
    DateTime,
    Int,
    )

from lp.registry.enums import InformationType
from lp.services.database.enumcol import EnumCol
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    BugTaskStatusSearch,
    )


class BugTaskFlat(object):

    __storm_table__ = 'BugTaskFlat'

    bugtask_id = Int(name='bugtask', primary=True)
    bug_id = Int(name='bug')
    datecreated = DateTime()
    duplicateof_id = Int(name='duplicateof')
    bug_owner_id = Int(name='bug_owner')
    information_type = EnumCol(enum=InformationType)
    date_last_updated = DateTime()
    heat = Int()
    product_id = Int(name='product')
    productseries_id = Int(name='productseries')
    distribution_id = Int(name='distribution')
    distroseries_id = Int(name='distroseries')
    sourcepackagename_id = Int(name='sourcepackagename')
    status = EnumCol(schema=(BugTaskStatus, BugTaskStatusSearch))
    importance = EnumCol(schema=BugTaskImportance)
    assignee_id = Int(name='assignee')
    milestone_id = Int(name='milestone')
    owner_id = Int(name='owner')
    active = Bool()
