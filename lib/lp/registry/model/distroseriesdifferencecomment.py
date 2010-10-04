# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A comment/message for a difference between two distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesDifferenceComment',
    ]

from email.Utils import make_msgid

from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.interface import (
    classProvides,
    implements,
    )

from canonical.launchpad.database.message import Message, MessageChunk
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.registry.interfaces.distroseriesdifferencecomment import (
    IDistroSeriesDifferenceComment,
    IDistroSeriesDifferenceCommentSource,
    )


class DistroSeriesDifferenceComment(Storm):
    """See `IDistroSeriesDifferenceComment`."""
    implements(IDistroSeriesDifferenceComment)
    classProvides(IDistroSeriesDifferenceCommentSource)
    __storm_table__ = 'DistroSeriesDifferenceMessage'

    id = Int(primary=True)

    distro_series_difference_id = Int(name='distro_series_difference',
                                      allow_none=False)
    distro_series_difference = Reference(
        distro_series_difference_id, 'DistroSeriesDifference.id')

    message_id = Int(name="message", allow_none=False)
    message = Reference(message_id, 'Message.id')

    @property
    def comment_author(self):
        """See `IDistroSeriesDifferenceComment`."""
        return self.message.owner

    @property
    def body_text(self):
        """See `IDistroSeriesDifferenceComment`."""
        return self.message.text_contents

    @property
    def comment_date(self):
        """See `IDistroSeriesDifferenceComment`."""
        return self.message.datecreated

    @staticmethod
    def new(distro_series_difference, owner, comment):
        """See `IDistroSeriesDifferenceCommentSource`."""
        msgid = make_msgid('distroseriesdifference')
        message = Message(
            parent=None, owner=owner, rfc822msgid=msgid,
            subject=distro_series_difference.title)
        MessageChunk(message=message, content=comment, sequence=1)

        store = IMasterStore(DistroSeriesDifferenceComment)
        dsd_comment = DistroSeriesDifferenceComment()
        dsd_comment.distro_series_difference = distro_series_difference
        dsd_comment.message = message

        comment = store.add(dsd_comment)
        store.flush()
        return comment

    @staticmethod
    def getForDifference(distro_series_difference, id):
        """See `IDistroSeriesDifferenceCommentSource`."""
        store = IStore(DistroSeriesDifferenceComment)
        DSDComment = DistroSeriesDifferenceComment
        return store.find(
            DSDComment,
            DSDComment.distro_series_difference == distro_series_difference,
            DSDComment.id == id).one()
