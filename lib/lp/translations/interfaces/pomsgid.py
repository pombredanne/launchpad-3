# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from zope.interface import Interface
from zope.schema import (
    Int,
    Text,
    )

from canonical.launchpad import _


__metaclass__ = type

__all__ = ('IPOMsgID', )

class IPOMsgID(Interface):
    """A PO message ID."""

    id = Int(
        title=_("The identifier of this POMsgID."),
        readonly=True, required=True)

    msgid = Text(
        title=_(u"A msgid string."))
