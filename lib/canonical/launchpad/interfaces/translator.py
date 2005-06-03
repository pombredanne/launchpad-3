# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute, classImplements

from zope.schema import Choice, Datetime, Int, Text, TextLine, Float
from zope.schema.interfaces import IText, ITextLine
from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.fields import Summary, Title
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import IHasOwner


class ITranslator(Interface):
    """A Translator in a TranslationGroup."""

    id = Int(
            title=_('Translator ID'), required=True, readonly=True,
            )
    datecreated = Datetime(
            title=_('Date Created'), required=True, readonly=True,
            )
    translationgroup = Choice(title=_('Translation Group'), required=True,
        vocabulary='TranslationGroup', description=_("The translation group "
        "in which the translator is being appointed."))
    #translationgroup = Attribute("The translation group.")
    language = Choice(title=_('Language'), required=True,
        vocabulary='Language', description=_("The language of the "
        "translator."))
    #language = Attribute("The language being translated.")
    translator = Choice(title=_('Translator'), required=True,
        vocabulary='Person', description=_("The translator who will be "
        "responsible for the language in this group."))
    #translator = Attribute("The translator.")


# Interfaces for containers
class ITranslatorSet(IAddFormCustomization):
    """A container for translators."""

    title = Attribute('Title')

