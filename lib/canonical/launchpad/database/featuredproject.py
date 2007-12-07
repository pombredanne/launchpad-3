# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for Featured Projects."""

__metaclass__ = type
__all__ = [
    'FeaturedProject',
    ]

from sqlobject import StringCol
from zope.interface import implements

from canonical.launchpad.interfaces import IFeaturedProject

from canonical.database.sqlbase import SQLBase


class FeaturedProject(SQLBase):
    """A featured project name. This is only the name of a project, product
    or distribution.
    """
    implements(IFeaturedProject)

    _defaultOrder = ['name']

    name = StringCol(notNull=True)

