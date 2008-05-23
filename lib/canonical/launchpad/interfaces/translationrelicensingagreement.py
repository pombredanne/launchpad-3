# Copyright 2008 Canonical Ltd.  All rights reserved.

from zope.interface import Interface
from zope.schema import Bool, Datetime, Int, Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.person import IPerson

__metaclass__ = type
__all__ = [
    'ITranslationRelicensingAgreement',
    ]

class ITranslationRelicensingAgreement(Interface):
    """An agreement from users about relicensing their translations."""

    id = Int(
        title=_("The ID for this relicensing answer"),
        readonly=True, required=True)

    person = Object(
        title=_("Person who has responded to relicensing question"),
        readonly=False, required=True, schema=IPerson)

    allow_relicensing = Bool(
        title=_("Whether you want your translations relicensed "
                "under BSD license"),
        readonly=False, default=True, required=True)

    date_decided = Datetime(
        title=_("The date person has made a decision"),
        readonly=True, required=True)
