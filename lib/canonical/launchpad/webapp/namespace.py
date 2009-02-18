from zope.app.pagetemplate.viewpagetemplatefile import (
    ViewPageTemplateFile, BoundPageTemplate)
from zope.traversing.interfaces import TraversalError
from zope.traversing.namespace import view

from canonical.launchpad.webapp.launchpadform import LaunchpadFormView

class form(view):
    template = ViewPageTemplateFile('../templates/launchpad-form-body.pt')

    def traverse(self, name, ignored):
        """Form traversal adapter

        This adapter allows any LaunchpadFormView to simply render the
        form body.
        """
        # Note: removeSecurityProxy seems necessary here as otherwise
        # isinstance below doesn't determine the type of the context.
        from zope.security.proxy import removeSecurityProxy
        context = removeSecurityProxy(self.context)

        if isinstance(context, LaunchpadFormView):
            # Note: without explicitely creating the BoundPageTemplate here
            # the view fails to render.
            context.index = BoundPageTemplate(form.template, context)
        else:
            raise TraversalError("The URL does not correspond to a form.")

        return self.context

