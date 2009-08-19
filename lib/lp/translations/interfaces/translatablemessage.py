# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.interface import Attribute, Interface
from zope.schema import Int

from canonical.launchpad import _

__metaclass__ = type

__all__ = [
    'ITranslatableMessage',
    ]

class ITranslatableMessage(Interface):
    """An IPOTMsgSet in the context of a certain IPOFile."""

    pofile = Attribute("The IPOFile")
    potmsgset = Attribute("The POTMsgset")

    sequence = Int(
        title=_("The sequence number within the POTemplate."),
        required=True)

    def isObsolete():
        """Flag indicating that this TranslatableMessage is obsolete"""

    def isCurrentDiverged():
        """Flag indicating that the current translation is diverged"""

    def isCurrentEmpty():
        """Flag indicating that the current translation is empty"""

    def isCurrentImported():
        """Flag indicating that the current translation is imported"""

    def getCurrentTranslation():
        """Get the TranslationMessage that holds the current translation."""

    def getImportedTranslation():
        """Get the TranslationMessage that is marked as imported.

        This can be None if there is no such message or it can be identical
        to the current translation if the current translation is imported.
        """

    def getSharedTranslation():
        """Get the TranslationMessage that is marked as shared.

        This can be None if there is no such message or it can be identical
        to the current translation if the current translation is shared.
        """

    def getSuggestions(only_new):
        """Return an iterator over suggested translations.

        :param only_new: Return only those translations that are newer than
          the review date of the current translation.
        """

    def getExternalTranslations():
        """Return an iterator over external translations.

        External translations are translations for the same English string
        in other products and source packages.
        """

