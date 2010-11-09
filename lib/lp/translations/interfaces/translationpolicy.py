# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation access and sharing policy."""

__metaclass__ = type
__all__ = [
    'ITranslationPolicy',
    ]

from zope.interface import Interface
from zope.schema import Choice

from canonical.launchpad import _
from lp.translations.enums import TranslationPermission


class ITranslationPolicy(Interface):
    """Permissions and sharing policy for translatable pillars.

    A translation policy defines who can edit translations, and who can
    add suggestions.  (The ability to edit also implies the ability to
    enter suggestions).  Everyone else is allowed only to view the
    translations.
    """

    translationgroup = Choice(
        title = _("Translation group"),
        description = _("The translation group that helps review "
            " translations for this project or distribution. The group's "
            " role depends on the permissions policy selected below."),
        required=False,
        vocabulary='TranslationGroup')

    translationpermission = Choice(
        title=_("Translation permissions policy"),
        description=_("The policy this project or distribution uses to "
            " balance openness and control for their translations."),
        required=True,
        vocabulary=TranslationPermission)

    def getTranslationGroups():
        """List all applicable translation groups.

        This may be an empty list, or a list containing just this
        policy's translation group, or for a product that is part of a
        project group, possibly a list of two translation groups.

        If there is an inherited policy, its translation group comes
        first.  Duplicates are removed.
        """

    def getTranslators(language, store=None):
        """Find the applicable `TranslationGroup`(s) and translators.

        Zero, one, or two translation groups may apply.  Each may have a
        `Translator` for the language, with either a person or a team
        assigned.

        In the case of a product in a project group, there may be up to
        two entries.  In that case, the entry from the project group
        comes first.

        :param language: The language that you want the translators for.
        :type language: ILanguage
        :param store: Optionally a specific store to retrieve from.
        :type store: Store
        :return: A result set of zero or more tuples:
            (`TranslationGroup`, `Translator`, `Person`).  The
            translation group is always present and unique.  The person
            is present if and only if the translator is present.  The
            translator is unique if present, but the person need not be.
        """

    def getEffectiveTranslationPermission(self):
        """Get the effective `TranslationPermission`.

        Returns the strictest applicable permission out of
        `self.translationpermission` and any inherited
        `TranslationPermission`.
        """
