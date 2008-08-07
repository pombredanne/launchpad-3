# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['Diff', 'StaticDiffReference']

from zope.interface import implements

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IDiff, IStaticDiffReference

class Diff(SQLBase):

    implements(IDiff)

class StaticDiffReference(SQLBase):

    implements(IStaticDiffReference)
