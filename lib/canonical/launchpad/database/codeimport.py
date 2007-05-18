# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to CodeImport."""

__metaclass__ = type
__all__ = ['CodeImport']

from canonical.database.constants import DEFAULT
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import RevisionControlSystems
from canonical.launchpad.interfaces import ICodeImport, ICodeImportSet


class CodeImport(SQLBase):
    """See ICodeImport."""

    implements(ICodeImport)
    _table = 'CodeImport'

    name = StringCol(notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    product = ForeignKey(foreignKey='Product', notNull=True)
    series = ForeignKey(foreignKey='ProductSeries', notNull=True)
    branch = ForeignKey(foreignKey='Branch', default=None)

    rcs_type = EnumCol(schema=RevisionControlSystems,
        notNull=False, default=None)
    cvs_root = StringCol(default=None)
    cvs_module = StringCol(default=None)
    svn_branch_url = StringCol(default=None)


class CodeImportSet:
    """See ICodeImportSet."""

    def new(self, name, product, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """See ICodeImportSet."""
        return CodeImport(name=name, product=product,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)
