# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SpecificationDependency."""

__metaclass__ = type

from zope.app.form.browser.add import AddView

from canonical.launchpad.interfaces import ISpecificationDependency

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'SpecificationDependencyAddView',
    'SpecificationDependencyRemoveView',
    ]

class SpecificationDependencyAddView(AddView):

    def create(self, dependency):
        return self.context.createDependency(dependency)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class SpecificationDependencyRemoveView(AddView):
    """This is counter-intuitive. We are using the zope addform machinery to
    render the form, so the spec gets passed to the "create" method of this
    class, but we are actually REMOVING the dependency.
    """

    def create(self, dependency):
        return self.context.removeDependency(dependency)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


