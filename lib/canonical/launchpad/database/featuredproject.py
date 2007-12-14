# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for Featured Projects."""

__metaclass__ = type
__all__ = [
    'FeaturedProject',
    ]

from sqlobject import IntCol

from zope.interface import implements

from canonical.launchpad.interfaces import IFeaturedProject
from canonical.database.sqlbase import SQLBase


class FeaturedProject(SQLBase):
    """A featured project reference.

    This is a reference to the name of a project, product or distribution
    that is currently being "featured" by being listed on the Launchpad home
    page.
    """
    implements(IFeaturedProject)

    _defaultOrder = ['id']

    pillar_name = IntCol(notNull=True)

