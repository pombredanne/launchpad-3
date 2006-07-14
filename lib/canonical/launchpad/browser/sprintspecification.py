# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintSpecification."""

__metaclass__ = type

from zope.app.form.browser.add import AddView
from zope.component import getUtility

from canonical.launchpad.browser.editview import SQLObjectEditView

from canonical.launchpad.helpers import check_permission

from canonical.launchpad.interfaces import ILaunchBag

from canonical.lp.dbschema import SprintSpecificationStatus

from canonical.launchpad.webapp import canonical_url


__all__ = [
    'SprintSpecificationAddView',
    'SprintSpecificationEditView',
    'SprintSpecificationRemoveView',
    ]

class SprintSpecificationAddView(AddView):

    def create(self, sprint):
        user = getUtility(ILaunchBag).user
        sprint_link = self.context.linkSprint(sprint, user)
        if check_permission('launchpad.Edit', sprint_link):
            sprint_link.status = SprintSpecificationStatus.ACCEPTED
        return sprint_link

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


