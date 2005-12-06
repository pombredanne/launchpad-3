# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationDependency."""

__metaclass__ = type

__all__ = [
    'SpecificationDependencyAddView',
    'SpecificationDependencyRemoveView',
    ]

from canonical.launchpad.webapp import GeneralFormView, canonical_url

class SpecificationDependencyAddView(GeneralFormView):

    def process(self, dependency):
        self._nextURL = canonical_url(self.context)
        return self.context.createDependency(dependency)


class SpecificationDependencyRemoveView(GeneralFormView):

    def process(self, dependency):
        self._nextURL = canonical_url(self.context)
        return self.context.removeDependency(dependency)

