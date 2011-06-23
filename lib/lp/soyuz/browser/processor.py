# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Navigation views for processors."""


__metaclass__ = type

__all__ = [
    'ProcessorFamilySetNavigation',
    'ProcessorFamilyNavigation',
    ]


from canonical.launchpad.webapp import Navigation
from lp.app.errors import NotFoundError
from lp.soyuz.interfaces.processor import (
    IProcessorFamily,
    IProcessorFamilySet,
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


class ProcessorFamilyNavigation(Navigation):
    """IProcessorFamily navigation."""

    usedfor= IProcessorFamily

    def traverse(self, id_):
        id_ = int(id_)
        processors = self.processors
        for p in processors:
            if p.id == id_:
                return p
        raise NotFoundError(id_)
