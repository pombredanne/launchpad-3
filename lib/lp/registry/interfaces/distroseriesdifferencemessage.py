# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Distribution series difference messages."""

__metaclass__ = type
__all__ = [
    'IDistroSeriesDifferenceMessage',
    ]


from lazr.restful.fields import Reference
from zope.interface import Interface
from zope.schema import Int

from canonical.launchpad import _
from canonical.launchpad.interfaces.message import IMessage
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )


class IDistroSeriesDifferenceMessage(Interface):

    id = Int(title=_('ID'), required=True, readonly=True)

    distro_series_difference = Reference(
        IDistroSeriesDifference, title=_("Distro series difference"),
        required=True, readonly=True, description=_(
            "The distro series difference to which this message "
            "belongs."))
    message = Reference(
        IMessage, title=_("Message"), required=True, readonly=True,
        description=_("A comment about this difference."))
