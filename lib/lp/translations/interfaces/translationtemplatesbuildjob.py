# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'ITranslationTemplatesBuildJobSource',
    ]

from zope.interface import Interface


class ITranslationTemplatesBuildJobSource(Interface):
    """Container for `TranslationTemplatesBuildJob`s."""

    def create(build):
        """Create new `TranslationTemplatesBuildJob`.

        Also creates the matching `IBuildQueue` and `IJob`.

        :param build: The `TranslationTemplatesBuild` to queue.
        :return: A new `TranslationTemplatesBuildJob`.
        """

    def getByBranch(branch):
        """Find `TranslationTemplatesBuildJob` for given `Branch`."""
