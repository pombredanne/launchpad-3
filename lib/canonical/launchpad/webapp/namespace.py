# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from z3c.ptcompat import ViewPageTemplateFile
from zope.app.pagetemplate.viewpagetemplatefile import BoundPageTemplate
from zope.security.proxy import removeSecurityProxy
from zope.traversing.interfaces import TraversalError
from zope.traversing.namespace import view

from lp.app.browser.launchpadform import LaunchpadFormView


class FormNamespaceView(view):
    """A namespace view to handle traversals with ++form++."""

    # Use a class variable for the template so that it does not need
    # to be created during the traverse.
    template = ViewPageTemplateFile('../templates/launchpad-form-body.pt')

    def traverse(self, name, ignored):
        """Form traversal adapter.

        This adapter allows any LaunchpadFormView to simply render the
        form body.
        """
        # Note: removeSecurityProxy seems necessary here as otherwise
        # isinstance below doesn't determine the type of the context.
        context = removeSecurityProxy(self.context)

        if isinstance(context, LaunchpadFormView):
            # Note: without explicitely creating the BoundPageTemplate here
            # the view fails to render.
            context.index = BoundPageTemplate(FormNamespaceView.template,
                                              context)
        else:
            raise TraversalError("The URL does not correspond to a form.")

        return self.context
