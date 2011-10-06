# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database class for Featured Projects."""

__metaclass__ = type
__all__ = [
    'FeaturedProject',
    ]

from sqlobject import IntCol
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.registry.interfaces.featuredproject import IFeaturedProject


class FeaturedProject(SQLBase):
    """A featured project reference.

    This is a reference to the name of a project, product or distribution
    that is currently being "featured" by being listed on the Launchpad home
    page.
    """
    implements(IFeaturedProject)

    _defaultOrder = ['id']

    pillar_name = IntCol(notNull=True)

