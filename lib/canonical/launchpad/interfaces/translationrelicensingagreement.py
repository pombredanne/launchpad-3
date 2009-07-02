# Copyright 2008 Canonical Ltd.  All rights reserved.

from zope.interface import Interface
from zope.schema import Bool, Choice, Datetime, Int, Object, Text
from lazr.enum import EnumeratedType, Item

from canonical.launchpad import _
from lp.registry.interfaces.person import IPerson

__metaclass__ = type
__all__ = [
    'ITranslationRelicensingAgreement',
    'ITranslationRelicensingAgreementEdit',
    'TranslationRelicensingAgreementOptions'
    ]


class ITranslationRelicensingAgreement(Interface):
    """An agreement to relicensing a person's translations."""

    id = Int(
        title=_("The ID for this relicensing answer"),
        readonly=True, required=True)

    person = Object(
        title=_("The person who responded to the relicensing question"),
        readonly=False, required=True, schema=IPerson)

    allow_relicensing = Bool(
        title=_("Whether the person agreed to the BSD license"),
        readonly=False, default=True, required=True)

    date_decided = Datetime(
        title=_("The date person made her decision"),
        readonly=True, required=True)


class TranslationRelicensingAgreementOptions(EnumeratedType):
    BSD = Item("I agree to licence all my translations in Launchpad "
               "using the BSD licence.")
    REMOVE = Item("I do not want to use the BSD licence and understand this "
                  "means I can't make translations in Launchpad.")


class ITranslationRelicensingAgreementEdit(ITranslationRelicensingAgreement):
    """Extend ITranslationRelicensingAgreement with `back_to` field."""

    back_to = Text(
        title=_("URL to go back to after question is shown"),
        readonly=False, required=False)

    allow_relicensing = Choice(
        title=_("I would rather"),
        vocabulary=TranslationRelicensingAgreementOptions,
        required=True)
