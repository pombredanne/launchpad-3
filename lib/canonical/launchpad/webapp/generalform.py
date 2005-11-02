# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Generalised Form View Classes
"""

__docformat__ = 'restructuredtext'

__all__ = [
    'GeneralFormView',
    'GeneralFormViewFactory',
    ]

from transaction import get_transaction

from zope.interface import Interface
from zope.schema import getFieldNamesInOrder
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.security.checker import defineChecker, NamesChecker

from zope.app import zapi
from zope.app.i18n import ZopeMessageIDFactory as _
from zope.app.form.interfaces import WidgetsError
from zope.app.form.interfaces import IInputWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
from zope.app.publisher.browser import BrowserView

from zope.app.form.utility import setUpWidgets, getWidgetsData


class GeneralFormView(BrowserView):
    """Simple Generalised Form Base Class

    Subclasses should provide a `schema` attribute defining the schema
    to be edited.

    The automatically generated widgets are available by name through
    the attributes `*_widget`.
    (E.g. ``view.title_widget for the title widget``)
    """

    errors = ()
    process_status = None
    label = ''
    _arguments = []
    _keyword_arguments = []
    _nextURL = None

    # Fall-back field names computes from schema
    fieldNames = property(lambda self: getFieldNamesInOrder(self.schema))
    # Fall-back template
    generated_form = ViewPageTemplateFile('../templates/launchpad-generalform.pt')

    # methods that should be overridden
    def process(self, *args, **kw):
        """Override this method in your own browser class, to process the
        form submission results.
        """
        pass

    def nextURL(self):
        """Override this to tell the form where to go after it has
        processed. Alternatively, just set self._nextURL and this method
        will send you there after self.process()
        """
        return self._nextURL


    # internal methods, should not be overridden
    def __init__(self, context, request):
        super(GeneralFormView, self).__init__(context, request)
        self._setUpWidgets()

    def _setUpWidgets(self):
        setUpWidgets(self, self.schema, IInputWidget, names=self.fieldNames)

    def setPrefix(self, prefix):
        for widget in self.widgets():
            widget.setPrefix(prefix)

    def widgets(self):
        return [getattr(self, name+'_widget')
                for name in self.fieldNames]

    def process_form(self):
        """This method extracts all the meaningful data from the form, and
        then calls self.process(), passing the contents of the form. You
        should override self.process() in your own View class.
        """

        if self.process_status is not None:
            # We've been called before. Just return the status we previously
            # computed.
            return self.process_status

        if "FORM_SUBMIT" not in self.request:
            self.process_status = ''
            if self.request.method == 'POST':
                self.process_status = 'Please fill in the form.'
            return self.process_status

        # extract the posted data, and validate with form widgets
        try:
            data = getWidgetsData(self, self.schema, names=self.fieldNames)
        except WidgetsError, errors:
            self.errors = errors
            self.process_status = _(
                "Please fix the problems below and try again.")
            get_transaction().abort()
            return self.process_status

        # pass the resulting validated data to the form's self.process() and
        args = []
        if self._arguments:
            for name in self._arguments:
                args.append(data[name])

        kw = {}
        if self._keyword_arguments:
            for name in self._keyword_arguments:
                if name in data:
                    kw[str(name)] = data[name]

        self.process_status = self.process(*args, **kw)

        # if we have a nextURL() then go there
        if self.nextURL():
            self.request.response.redirect(self.nextURL())

        return self.process_status


def GeneralFormViewFactory(name, schema, label, permission, layer,
                    template, default_template, bases, for_, fields,
                    arguments, keyword_arguments, fulledit_path=None,
                    fulledit_label=None, menu=u''):
    class_ = SimpleViewClass(template, used_for=schema, bases=bases)
    class_.schema = schema
    class_.label = label
    class_.fieldNames = fields
    class_._arguments = arguments
    class_._keyword_arguments = keyword_arguments

    class_.fulledit_path = fulledit_path
    if fulledit_path and (fulledit_label is None):
        fulledit_label = "Full edit"

    class_.fulledit_label = fulledit_label

    class_.generated_form = ViewPageTemplateFile(default_template)

    defineChecker(class_,
                  NamesChecker(("__call__", "__getitem__",
                                "browserDefault", "publishTraverse"),
                               permission))
    if layer is None:
        layer = IBrowserRequest

    s = zapi.getGlobalService(zapi.servicenames.Adapters)
    s.register((for_, layer), Interface, name, class_)

