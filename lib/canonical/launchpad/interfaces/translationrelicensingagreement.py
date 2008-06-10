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
    """An agreement to relicensing a person's translations."""

    id = Int(
        title=_("The ID for this relicensing answer"),
        readonly=True, required=True)

    person = Object(
        title=_("The person who responded to the relicensing question"),
        readonly=False, required=True, schema=IPerson)

    # Title of this field appears in the web form, thus it's
    # oriented more towards being a useful UI than being a docstring.
    allow_relicensing = Bool(
        title=_("Relicense my translations under BSD license"),
        readonly=False, default=True, required=True)

    date_decided = Datetime(
        title=_("The date person made her decision"),
        readonly=True, required=True)
