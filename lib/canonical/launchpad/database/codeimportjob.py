# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = ['CodeImportJob', 'CodeImportJobSet']

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ICodeImportJob, ICodeImportJobSet

from zope.interface import implements

class CodeImportJob(SQLBase):
    """See `ICodeImportJob`."""

    implements(ICodeImportJob)

class CodeImportJobSet(object):
    """See `ICodeImportJobSet`."""

    implements(ICodeImportJobSet)
