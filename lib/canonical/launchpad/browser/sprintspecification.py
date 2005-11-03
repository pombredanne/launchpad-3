# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintSpecification."""

__metaclass__ = type

from zope.app.form.browser.add import AddView

from canonical.launchpad.interfaces import ISprintSpecification

from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'SprintSpecificationAddView',
    'SprintSpecificationEditView',
    'SprintSpecificationRemoveView',
    ]

class SprintSpecificationAddView(AddView):

    def create(self, sprint):
        return self.context.linkSprint(sprint)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class SprintSpecificationRemoveView(AddView):
    """This is counter-intuitive. We are using the zope addform machinery to
    render the form, so the bug gets passed to the "create" method of this
    class, but we are actually REMOVING the sprint.

    XXX sabdfl 14/09/05 please redo with new General Form
    """

    def create(self, sprint):
        return self.context.unlinkSprint(sprint)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return canonical_url(self.context)


class SprintSpecificationEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context.sprint))


