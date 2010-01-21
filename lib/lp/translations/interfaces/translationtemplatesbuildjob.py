# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0213

__metaclass__ = type

__all__ = [
    'ITranslationTemplatesBuildJobSource',
    ]

from zope.interface import Interface


class ITranslationTemplatesBuildJobSource(Interface):
    """Container for `TranslationTemplatesBuildJob`s."""

    def create(branch):
        """Create new `TranslationTemplatesBuildJob`.

        Also creates the matching `IBuildQueue` and `IJob`.

        :param branch: A `Branch` that this job will check out and
            generate templates for.
        :return: A new `TranslationTemplatesBuildJob`.
        """
