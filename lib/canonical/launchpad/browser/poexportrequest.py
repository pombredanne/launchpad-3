# Copyright 2007 Canonical Ltd.  All rights reserved.

"""View class for requesting translation exports."""

__metaclass__ = type
__all__ = ['BaseExportView']

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IPOExportRequestSet, ITranslationExporter)
from canonical.launchpad.webapp import (canonical_url, LaunchpadView)
from canonical.lp.dbschema import TranslationFileFormat


class BaseExportView(LaunchpadView):
    """Base class for PO export views."""

    def getDefaultFormat(self):
        """Overridable: default file format to offer."""
        raise NotImplementedError

    def processForm(self):
        """Overridable: what templates and translations are being requested?

        Override in child class.  Must do one of:
        a. Add an error notification to the page and return `None`
        b. Return a tuple of two lists: the list of requested templates and
            the list of requested pofiles.
        c. Redirect and return `None`.
        """
        raise NotImplementedError

    def initialize(self):
        self.request_set = getUtility(IPOExportRequestSet)
        if self.request.method != "POST":
            return

        bad_format_message = _("Please select a valid format for download.")
        format_name = self.request.form.get("format")
        if format_name is None:
            self.request.response.addErrorNotification(bad_format_message)
            return
        try:
            format = TranslationFileFormat.items[format_name]
        except KeyError:
            self.request.response.addErrorNotification(bad_format_message)
            return

        requested_files = self.processForm()
        if requested_files is None:
            return

        templates, pofiles = requested_files
        if not templates and not pofiles:
            self.request.response.addErrorNotification(
                "Please select at least one translation or template.")
        else:
            self.request_set.addRequest( self.user, templates, pofiles, format)
            self.nextURL()

    def nextURL(self):
        self.request.response.addInfoNotification(_(
            "Your request has been received. Expect to receive an email "
            "shortly."))
        self.request.response.redirect(canonical_url(self.context))

    def formats(self):
        """Return a list of formats available for translation exports."""

        class BrowserFormat:
            def __init__(self, title, value, is_default=False):
                self.title = title
                self.value = value
                self.is_default = is_default

        default_format = self.getDefaultFormat()
        exporters = (getUtility(
            ITranslationExporter).getExportersForSupportedFileFormat(
                default_format))
        for exporter in exporters:
            format = exporter.format
            is_default = (format == default_format)
            yield BrowserFormat(format.title, format.name, is_default)
