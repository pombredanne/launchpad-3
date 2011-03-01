# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Int,
    )

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
        title=_("Sequence number within the POTemplate."),
        required=True)

    is_obsolete = Bool(
        title=_("This TranslatableMessage is obsolete"),
        required=True)

    is_untranslated = Bool(
        title=_("The current translation is empty"),
        required=True)

    is_current_diverged = Bool(
        title=_("The current translation is diverged"),
        required=True)

    is_current_imported = Bool(
        title=_("The current translation is used upstream"),
        required=True)

    has_plural_forms = Bool(
        title=_("There is an English plural string"),
        required=True)

    number_of_plural_forms = Int(
        title=_("Number of plural forms in the target language"),
        required=True)

    def getCurrentTranslation():
        """Get the TranslationMessage that holds the current translation."""

    def getImportedTranslation():
        """Get the TranslationMessage that is marked as current-upstream.

        This can be None if there is no such message, or it can be
        identical to the current Ubuntu translation.
        """

    def getSharedTranslation():
        """Get the TranslationMessage that is marked as shared.

        This can be None if there is no such message or it can be identical
        to the current translation if the current translation is shared.
        """

    def getAllSuggestions():
        """Return an iterator over all suggested translations."""

    def getUnreviewedSuggestions():
        """Return an iterator over unreviewed suggested translations.

        Return those translation messages that have a creation date newer
        than the review date of the current message (have not been reviewed).
        """

    def getDismissedSuggestions(include_dismissed=True):
        """Return an iterator over dismissed suggested translations.

        Return those translation messages that have a creation date older
        than the review date of the current message (have been dismissed).
        """

    def getExternalTranslations():
        """Return an iterator over external translations.

        External translations are translations for the same English string
        in other products and source packages.
        """

    def getExternalSuggestions():
        """Return an iterator over externally suggested translations.

        External suggested translations are suggestions for the same English
        string in other products and source packages.
        """

    def dismissAllSuggestions(reviewer, lock_timestamp):
        """Dismiss all suggestions.

        :param reviewer: the person that is doing the dismissal.
        :param lock_timestamp: the timestamp when we checked the values we
            want to update.

        Raises TranslationConflict if two edits happen simultaneously.
        """

