# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'FormNamespaceView',
    'JsonModelNamespaceView',
    ]


from z3c.ptcompat import ViewPageTemplateFile
from zope.app.pagetemplate.viewpagetemplatefile import BoundPageTemplate
from zope.security.proxy import removeSecurityProxy
from zope.traversing.interfaces import TraversalError
from zope.traversing.namespace import view
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher
from lazr.restful.interfaces import IJSONRequestCache

from lp.app.browser.launchpadform import LaunchpadFormView
from simplejson import dumps

class FormNamespaceView(view):
    """A namespace view to handle traversals with ++form++."""

    # Use a class variable for the template so that it does not need
    # to be created during the traverse.
    template = ViewPageTemplateFile('templates/launchpad-form-body.pt')

    def traverse(self, name, ignored):
        """Form traversal adapter.

        This adapter allows any LaunchpadFormView to simply render the
        form body.
        """
        # Note: removeSecurityProxy seems necessary here as otherwise
        # isinstance below doesn't determine the type of the context.
        context = removeSecurityProxy(self.context)

        if isinstance(context, LaunchpadFormView):
            # Note: without explicitly creating the BoundPageTemplate here
            # the view fails to render.
            context.index = BoundPageTemplate(FormNamespaceView.template,
                                              context)
        else:
            raise TraversalError("The URL does not correspond to a form.")

        return self.context


class JsonModelNamespaceView(view):
    """A namespace view to handle traversals with ++model++."""

    implements(IBrowserPublisher)

    def traverse(self, name, ignored):
        """Model traversal adapter.

        This adapter allows any LaunchpadView to render its JSON cache.
        """
        # XXX If the context is not a view then find and return the default
        # view.
        return self

    def browserDefault(self, request):
        # Tell traversal to stop, dammit.
        return self, None

    @property
    def display_breadcrumbs(self):
        return False

    def __call__(self):
        # This will render the parent view so that the object cache is
        # initialized.  This is a bit paranoid.
        # XXX register a <browser:pages> directive in the ZCML for
        # LaunchpadView to make the security settings work.
        naked_context = removeSecurityProxy(self.context)
        naked_context.initialize()
        #self.context.initialize()
        ## cache = IJSONRequestCache(self.request)
        ## #cache = {'name': 'brad'}
        ## return dumps(cache.objects)
        cache = naked_context.getCacheJSON()
        self.request.response.setHeader('content-type', 'application/json')
        return cache
