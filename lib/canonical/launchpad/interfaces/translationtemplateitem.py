# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface
from zope.schema import Int, Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.potemplate import IPOTemplate
from canonical.launchpad.interfaces.potmsgset import IPOTMsgSet

__metaclass__ = type
__all__ = [
    'ITranslationTemplateItem',
    ]


class ITranslationTemplateItem(Interface):
    """A translatable message in a translation template file."""

    id = Int(
        title=_("The ID for this translation message"),
        readonly=True, required=True)

    potemplate = Object(
        title=_("The template this translation is in"),
        readonly=False, required=False, schema=IPOTemplate)

    sequence = Int("The ordering of this set within its file.")

    potmsgset = Object(
        title=_("The template message that this translation is for"),
        readonly=True, required=True, schema=IPOTMsgSet)
