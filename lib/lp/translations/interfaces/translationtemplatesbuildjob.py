# Copyright 2010 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'ITranslationTemplatesBuildJob',
    'ITranslationTemplatesBuildJobSource',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )

from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobOld


class ITranslationTemplatesBuildJob(IBuildFarmJobOld):

    branch = Attribute("Branch")


class ITranslationTemplatesBuildJobSource(Interface):
    """Container for `TranslationTemplatesBuildJob`s."""

    def getByBranch(branch):
        """Find `TranslationTemplatesBuildJob` for given `Branch`."""
