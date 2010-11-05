# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translation permissions policy."""

__metaclass__ = type
__all__ = [
    'ITranslationPolicy',
    ]

from zope.interface import Interface
from zope.schema import Choice

from canonical.launchpad import _
from lp.translations.interfaces.translationgroup import TranslationPermission


class ITranslationPolicy(Interface):
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
