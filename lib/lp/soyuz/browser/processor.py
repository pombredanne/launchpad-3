# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Navigation views for processors."""


__metaclass__ = type

__all__ = [
    'ProcessorFamilySetNavigation',
    'ProcessorSetNavigation',
    ]


from canonical.launchpad.webapp import Navigation
from lp.app.errors import NotFoundError
from lp.soyuz.interfaces.processor import (
    IProcessorFamilySet,
    IProcessorSet,
    )


class ProcessorFamilySetNavigation(Navigation):
    """IProcessorFamilySet navigation."""
    usedfor = IProcessorFamilySet

    def traverse(self, name):
        family = self.context.getByName(name)
        # Raise NotFoundError on invalid processor family name.
        if family is None:
            raise NotFoundError(name)
        return family


class ProcessorSetNavigation(Navigation):
    """IProcessorFamilySet navigation."""
    usedfor = IProcessorSet

    def traverse(self, name):
        return self.context.getByName(name)
