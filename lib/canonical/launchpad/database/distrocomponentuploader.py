# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['DistroComponentUploader']

from canonical.launchpad.interfaces import IDistroComponentUploader

from canonical.database.sqlbase import SQLBase
from sqlobject import ForeignKey
from zope.interface import implements

from canonical.launchpad.validators.person import validate_public_person

class DistroComponentUploader(SQLBase):
    """A grant of upload rights to a person or team, applying to a
    distribution and a specific component therein.
    """

    implements(IDistroComponentUploader)

    distribution = ForeignKey(dbName='distribution',
        foreignKey='Distribution', notNull=True)
    component = ForeignKey(
        dbName='component', foreignKey='Component', notNull=True)
    uploader = ForeignKey(dbName='uploader', foreignKey='Person',
        storm_validator=validate_public_person,
        notNull=True)

    def __contains__(self, person):
        """See IDistroComponentUploader."""
        return person.inTeam(self.uploader)


