# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to CodeImport."""

__metaclass__ = type

__all__ = [
    'CodeImport',
    'CodeImportMachine',
    'CodeImportMachineSet',
    'CodeImportSet',
    ]

from sqlobject import (
    BoolCol, ForeignKey, IntCol, StringCol)

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ICodeImport, ICodeImportMachine, ICodeImportMachineSet, ICodeImportSet,
    ILaunchpadCelebrities)
from canonical.lp.dbschema import (
    CodeImportReviewStatus, RevisionControlSystems)


class CodeImport(SQLBase):
    """See ICodeImport."""

    implements(ICodeImport)
    _table = 'CodeImport'

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    branch = ForeignKey(dbName='branch', foreignKey='Branch',
                        notNull=True)
    registrant = ForeignKey(dbName='registrant', foreignKey='Person',
                            notNull=True)

    @property
    def product(self):
        return self.branch.product

    review_status = EnumCol(schema=CodeImportReviewStatus, notNull=True,
        default=CodeImportReviewStatus.NEW)

    rcs_type = EnumCol(schema=RevisionControlSystems,
        notNull=False, default=None)
    cvs_root = StringCol(default=None)
    cvs_module = StringCol(default=None)
    svn_branch_url = StringCol(default=None)


class CodeImportSet:
    """See `ICodeImportSet`."""

    implements(ICodeImportSet)

    def new(self, registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """See `ICodeImportSet`."""
        assert branch.owner == getUtility(ILaunchpadCelebrities).vcs_imports
        if rcs_type == RevisionControlSystems.CVS:
            assert cvs_root is not None and cvs_module is not None
            assert svn_branch_url is None
        elif rcs_type == RevisionControlSystems.SVN:
            assert cvs_root is None and cvs_module is None
            assert svn_branch_url is not None
        else:
            raise AssertionError(
                "Don't know how to sanity check source details for unknown "
                "rcs_type %s"%rcs_type)
        return CodeImport(registrant=registrant, branch=branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)

    def getAll(self):
        """See `ICodeImportSet`."""
        return CodeImport.select()

    def get(self, id):
        """See `ICodeImportSet`."""
        return CodeImport.get(id)

    def getByBranch(self, branch):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(branch=branch)


class CodeImportMachine(SQLBase):
    """See `ICodeImportMachine`."""

    implements(ICodeImportMachine)

    hostname = StringCol(default=None)
    online = BoolCol(default=False)


class CodeImportMachineSet(object):
    """See `ICodeImportMachineSet`."""

    implements(ICodeImportMachineSet)

    def getAll(self):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine.select()

    def getByHostname(self, hostname):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine.selectOneBy(hostname=hostname)

    def new(self, hostname, online):
        """See `ICodeImportMachineSet`."""
        return CodeImportMachine(hostname=hostname, online=online)
