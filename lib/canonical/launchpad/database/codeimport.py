# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to CodeImport."""

__metaclass__ = type
__all__ = ['CodeImport', 'CodeImportSet']

from zope.interface import implements

from sqlobject import (
    BoolCol, ForeignKey, IntCol, StringCol)

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import RevisionControlSystems
from canonical.launchpad.interfaces import ICodeImport, ICodeImportSet


class CodeImport(SQLBase):
    """See ICodeImport."""

    implements(ICodeImport)
    _table = 'CodeImport'

    name = StringCol(notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    product = ForeignKey(dbName='product', foreignKey='Product',
                         notNull=True)
    series = ForeignKey(dbName='series', foreignKey='ProductSeries',
                        notNull=True)
    branch = ForeignKey(dbName='branch', foreignKey='Branch',
                        default=None)

    rcs_type = EnumCol(schema=RevisionControlSystems,
        notNull=False, default=None)
    cvs_root = StringCol(default=None)
    cvs_module = StringCol(default=None)
    svn_branch_url = StringCol(default=None)


class CodeImportSet:
    """See ICodeImportSet."""

    implements(ICodeImportSet)

    def new(self, name, product, series, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """See ICodeImportSet."""
        return CodeImport(name=name, product=product, series=series,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)

    def getAll(self):
        """See ICodeImportSet."""
        return CodeImport.select()
