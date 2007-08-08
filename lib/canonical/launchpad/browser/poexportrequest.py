# Copyright 2007 Canonical Ltd.  All rights reserved.

"""View class for requesting translation exports."""

__metaclass__ = type
__all__ = ['BaseExportView']

import os.path
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import IPOExportRequestSet
from canonical.launchpad.webapp import (canonical_url, LaunchpadView)
from canonical.lp.dbschema import TranslationFileFormat


class BaseExportView(LaunchpadView):
    """Base class for PO export views."""

    def initialize(self):
        self.request_set = getUtility(IPOExportRequestSet)
        self.processForm()

    def processForm(self):
        """Override in subclass."""
        raise NotImplementedError

    def nextURL(self):
        self.request.response.addInfoNotification(_(
            "Your request has been received. Expect to receive an email "
            "shortly."))
        self.request.response.redirect(canonical_url(self.context))

    def validateFileFormat(self, format_name):
        notice = _('Please select a valid format for download.')
        valid_name = None
        if format_name is not None:
            try:
                valid_name = TranslationFileFormat.items[format_name]
            except KeyError:
                pass
        if format_name is None:
            self.request.response.addErrorNotification(notice)
        return valid_name

    def formats(self):
        """Return a list of formats available for translation exports."""

        class BrowserFormat:
            def __init__(self, title, value, is_default=False):
                self.title = title
                self.value = value
                self.is_default = is_default

        formats = [
            TranslationFileFormat.PO,
            TranslationFileFormat.MO,
        ]

        default_format = self.getDefaultFormat()
        for format in formats:
            is_default = (format == default_format)
            yield BrowserFormat(format.title, format.name, is_default)


