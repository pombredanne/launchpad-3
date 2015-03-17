# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'GitRef',
    ]

from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.interface import implements

from lp.code.enums import GitObjectType
from lp.code.interfaces.gitref import IGitRef
from lp.services.database.enumcol import EnumCol
from lp.services.database.stormbase import StormBase


class GitRef(StormBase):
    """See `IGitRef`."""

    __storm_table__ = 'GitRef'
    __storm_primary__ = ('repository_id', 'path')

    implements(IGitRef)

    repository_id = Int(name='repository', allow_none=False)
    repository = Reference(repository_id, 'GitRepository.id')

    path = Unicode(name='path', allow_none=False)

    commit_sha1 = Unicode(name='commit_sha1', allow_none=False)

    object_type = EnumCol(enum=GitObjectType, notNull=True)
