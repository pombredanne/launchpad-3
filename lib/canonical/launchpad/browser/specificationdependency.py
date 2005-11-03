# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationDependency."""

__metaclass__ = type

from canonical.launchpad.webapp import GeneralFormView

from canonical.launchpad.interfaces import ISpecificationDependency

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'SpecificationDependencyAddView',
    'SpecificationDependencyRemoveView',
    ]

class SpecificationDependencyAddView(GeneralFormView):

    def process(self, dependency):
        self._nextURL = canonical_url(self.context)
        return self.context.createDependency(dependency)


class SpecificationDependencyRemoveView(GeneralFormView):

    def process(self, dependency):
        self._nextURL = canonical_url(self.context)
        return self.context.removeDependency(dependency)

