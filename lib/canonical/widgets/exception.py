from zope.interface import implements
from zope.app.form.interfaces import IWidgetInputError
from zope.app.form.interfaces import WidgetInputError as _WidgetInputError
from zope.app.form.browser.interfaces import IWidgetInputErrorView
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# TODO: Sort Z3 out and use the default implementation when it gets back
# to launchpad.

class WidgetInputError(_WidgetInputError):
    """A customized WidgetInputError to work around a bug in Z3
    (The snippet method fails if errors is a list of ValidationError objects)

    """
    implements(IWidgetInputError)

    def __init__(self, field_name, widget_title, errors):
        """Initialize Error

        `errors` is a ``ValidationError`` or a list of ValidationError objects

        """
        if not isinstance(errors, list):
            errors = [errors]
        _WidgetInputError.__init__(self, field_name, widget_title, errors)

    def doc(self):
        """Returns a string that represents the error message."""
        return ', '.join([v.doc() for v in self.errors])


class WidgetInputErrorView(object):
    """Rendering of IWidgetInputError"""
    implements(IWidgetInputErrorView)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    snippet = ViewPageTemplateFile('templates/error.pt')

