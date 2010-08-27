# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A comment/message for a difference between two distribution series."""

__metaclass__ = type

__all__ = [
    'DistroSeriesDifferenceMessage',
    ]


from storm.locals import (
    Int,
    Reference,
    Storm,
    )
from zope.interface import implements

from lp.registry.interfaces.distroseriesdifferencemessage import (
    IDistroSeriesDifferenceMessage,
    )

class DistroSeriesDifferenceMessage(Storm):
    """See `IDistroSeriesDifferenceMessage`."""
    implements(IDistroSeriesDifferenceMessage)
    __storm_table__ = 'DistroSeriesDifferenceMessage'

    id = Int(primary=True)

    distro_series_difference_id = Int(name='distro_series_difference',
                                      allow_none=False)
    distro_series_difference = Reference(
        distro_series_difference_id, 'DistroSeriesDifference.id')

    message_id = Int(name="message", allow_none=False)
    message = Reference(message_id, 'Message.id')

