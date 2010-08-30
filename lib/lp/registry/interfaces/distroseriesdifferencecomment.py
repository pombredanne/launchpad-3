# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Distribution series difference messages."""

__metaclass__ = type
__all__ = [
    'IDistroSeriesDifferenceComment',
    'IDistroSeriesDifferenceCommentSource',
    ]


from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import (
    Int,
    Text,
    )

from canonical.launchpad import _
from canonical.launchpad.interfaces.message import IMessage
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )


class IDistroSeriesDifferenceComment(Interface):
    """A comment for a distroseries difference record."""

    id = Int(title=_('ID'), required=True, readonly=True)

    distro_series_difference = Reference(
        IDistroSeriesDifference, title=_("Distro series difference"),
        required=True, readonly=True, description=_(
            "The distro series difference to which this message "
            "belongs."))
    message = Reference(
        IMessage, title=_("Message"), required=True, readonly=True,
        description=_("A comment about this difference."))

    comment = Text(
        title=_("Comment text"), readonly=True, description=_(
            "The comment text for the related distro series difference."))


class IDistroSeriesDifferenceCommentSource(Interface):
    """A utility of this interface can be used to create comments."""

    def new(distro_series_difference, owner, comment):
        """Create a new comment on a distro series difference.

        :param distro_series_difference: The distribution series difference
            that is being commented on.
        :param owner: The person making the comment.
        :param comment: The comment.
        :return: A new `DistroSeriesDifferenceComment` object.
        """

    def getCommentsForDifference(distro_series_difference):
        """Return a result set of comments for a difference.

        :param distro_series_difference: The distribution series difference
            for which comments are fetched.
        :return: A result set of comments, ordered by id by default.
        """
