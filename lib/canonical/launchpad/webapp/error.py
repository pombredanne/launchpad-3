# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import traceback

from zope.exceptions.exceptionformatter import format_exception

from canonical.config import config

class SystemError:
    """Default exception error view

    Returns a 500 response instead of 200
    """
    show_tracebacks = False
    def __init__(self, context, request):

        self.context = context
        self.request = request

        if config.show_tracebacks:
            self.show_tracebacks = True

            self.error_type, self.error_object, tb = sys.exc_info()
            try:
                self.traceback_lines = traceback.format_tb(tb)
                self.htmltext = '\n'.join(
                    format_exception(self.error_type, self.error_object,
                                    tb, as_html=True)
                    )
            finally:
                del tb


    def __call__(self, *args, **kw):
        self.request.response.setStatus(500)
        return self.index(*args, **kw)

