# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation classes for IDiff, etc."""

__metaclass__ = type
__all__ = ['BranchMergeQueue']

from storm.locals import (
    Int,
    Reference,
    Storm,
    Unicode,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.database.datetimecol import UtcDateTimeCol
from lp.code.interfaces.branchmergequeue import (
    IBranchMergeQueue,
    IBranchMergeQueueSource,
    )


class BranchMergeQueue(Storm):
    """See `IBranchMergeQueue`."""

    __storm_table__ = 'BranchMergeQueue'
    implements(IBranchMergeQueue)
    classProvides(IBranchMergeQueueSource)

    id = Int(primary=True)

    registrant_id = Int(name='registrant', allow_none=True)
    registrant = Reference(registrant_id, 'Person.id')

    owner_id = Int(name='owner', allow_none=True)
    owner = Reference(owner_id, 'Person.id')

    name = Unicode(allow_none=False)
    description = Unicode(allow_none=False)
    configuration = Unicode(allow_none=False)

    date_created = UtcDateTimeCol(notNull=True)

    @staticmethod
    def new(name, owner, registrant, description=None,
            configuration=None):
        queue = BranchMergeQueue()
        queue.name = name
        queue.owner = owner
        queue.registrant = registrant
        queue.description = description
        queue.configuration = configuration

        return queue
