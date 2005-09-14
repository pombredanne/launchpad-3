# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import traceback

from zope.exceptions.exceptionformatter import format_exception

from canonical.config import config


class DebugView:
    """Helper class for views on exceptions for the Debug layer."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.computeDebugOutput()

    def computeDebugOutput(self):
        """Inspect the exception, and set up instance attributes.

        self.error_type
        self.error_object
        self.traceback_lines
        self.htmltext
        """
        self.error_type, self.error_object, tb = sys.exc_info()
        try:
            self.traceback_lines = traceback.format_tb(tb)
            self.htmltext = '\n'.join(
                format_exception(self.error_type, self.error_object,
                                 tb, as_html=True)
                )
        finally:
            del tb


class SystemErrorView(DebugView):
    """Default exception error view.

    Returns a 500 response instead of 200.
    """

    show_tracebacks = False

    def computeDebugOutput(self):
        """Compute debug output only if config.show_tracebacks is set."""
        if config.show_tracebacks:
            self.show_tracebacks = True
            DebugView.computeDebugOutput(self)

    def __call__(self, *args, **kw):
        self.request.response.setStatus(500)
        return self.index(*args, **kw)

