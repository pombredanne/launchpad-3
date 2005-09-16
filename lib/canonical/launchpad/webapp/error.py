# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import traceback

from zope.exceptions.exceptionformatter import format_exception

from canonical.config import config
import canonical.launchpad.layers


class SystemErrorView:
    """Helper class for views on exceptions for the Debug layer.

    Also, sets a 500 response code.
    """

    # Override this in subclasses.  A value of None means "don't set this"
    response_code = 500


    show_tracebacks = False
    pagetesting = False
    debugging = False

    def __init__(self, context, request):
        self.context = context
        self.request = request
        if self.response_code is not None:
            self.request.response.setStatus(self.response_code)
        self.computeDebugOutput()
        if config.show_tracebacks:
            self.show_tracebacks = True
        if canonical.launchpad.layers.PageTestLayer.providedBy(self.request):
            self.pagetesting = True
        if canonical.launchpad.layers.DebugLayer.providedBy(self.request):
            self.debugging = True

    def computeDebugOutput(self):
        """Inspect the exception, and set up instance attributes.

        self.error_type
        self.error_object
        self.traceback_lines
        self.htmltext
        self.plaintext
        """
        self.error_type, self.error_object, tb = sys.exc_info()
        try:
            self.traceback_lines = traceback.format_tb(tb)
            self.htmltext = '\n'.join(
                format_exception(self.error_type, self.error_object,
                                 tb, as_html=True)
                )
            self.plaintext = ''.join(
                format_exception(self.error_type, self.error_object,
                                 tb, as_html=False)
                )
        finally:
            del tb

    def inside_div(self, html):
        """Returns the given html text inside a div of an appropriate class."""

        return ('<div class="highlighted" '
                'style="font-family: monospace; font-size: smaller;">'
                '%s'
                '</div') % html

    def maybeShowTraceback(self):
        """Return a traceback, but only if it is appropriate to do so."""
        if self.pagetesting:
            return self.inside_div('<pre>\n%s</pre>' % self.plaintext)
        elif self.show_tracebacks or self.debugging:
            return self.inside_div(self.htmltext)
        else:
            return ''

    def render_as_text(self):
        """Render the exception as text.

        This is used to render exceptions in pagetests.
        """
        self.request.response.setHeader('Content-Type', 'text/plain')
        return self.plaintext

    def __call__(self):
        if self.pagetesting:
            return self.render_as_text()
        else:
            return self.index()


class NotFoundView(SystemErrorView):

    response_code = 404

    def __call__(self):
        return self.index()
