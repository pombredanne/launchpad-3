# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'SpecificationMessage',
    'SpecificationMessageSet'
    ]

from email.utils import make_msgid

from sqlobject import (
    BoolCol,
    ForeignKey,
    )
from zope.interface import implementer

from lp.blueprints.interfaces.specificationmessage import (
    ISpecificationMessage,
    ISpecificationMessageSet,
    )
from lp.services.database.sqlbase import SQLBase
from lp.services.messages.model.message import (
    Message,
    MessageChunk,
    )


@implementer(ISpecificationMessage)
class SpecificationMessage(SQLBase):
    """A table linking specifictions and messages."""

    _table = 'SpecificationMessage'

    specification = ForeignKey(
        dbName='specification', foreignKey='Specification', notNull=True)
    message = ForeignKey(dbName='message', foreignKey='Message', notNull=True)
    visible = BoolCol(notNull=True, default=True)


@implementer(ISpecificationMessageSet)
class SpecificationMessageSet:
    """See ISpecificationMessageSet."""

    def createMessage(self, subject, spec, owner, content=None):
        """See ISpecificationMessageSet."""
        msg = Message(
            owner=owner, rfc822msgid=make_msgid('blueprint'), subject=subject)
        MessageChunk(message=msg, content=content, sequence=1)
        return SpecificationMessage(specification=spec, message=msg)

    def get(self, specmessageid):
        """See ISpecificationMessageSet."""
        return SpecificationMessage.get(specmessageid)
