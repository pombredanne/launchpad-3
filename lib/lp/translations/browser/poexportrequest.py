# Copyright 2007-2009 Canonical Ltd.  All rights reserved.

"""View class for requesting translation exports."""

__metaclass__ = type
__all__ = ['BaseExportView']


from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from lp.translations.interfaces.poexportrequest import (
    IPOExportRequestSet)
from lp.translations.interfaces.potemplate import (
    IHasTranslationTemplates)
from lp.translations.interfaces.translationexporter import (
    ITranslationExporter)
from lp.translations.interfaces.translationfileformat import (
    TranslationFileFormat)
from canonical.launchpad.webapp import (canonical_url, LaunchpadView)


class BaseExportView(LaunchpadView):
    """Base class for PO export views."""

    @cachedproperty
    def uses_translations(self):
        return self.context.has_current_translation_templates

    def getDefaultFormat(self):
        """Overridable: return default file format to use for the export."""
        if not IHasTranslationTemplates.providedBy(self.context):
            raise NotImplementedError(
                'Subclass not implementing `IHasTranslationsTemplates` '
                'interface.  Either override getDefaultFormat implementation '
                'or implement `IHasTranslationsTemplates`.')

        templates = self.context.getCurrentTranslationTemplates()
        if not bool(templates.any()):
            return None
        formats = self.context.getTranslationTemplateFormats()
        format = formats[0]
        if len(formats) > 1:
            self.request.response.addInfoNotification(
                "This package has templates with different native "
                "file formats.  If you proceed, all translations will be "
                "exported in the single format you specify.")
        return format

    def processForm(self):
        """Return templates and translations requested to be exported.

        Overridable in a child class.  Must do one of:
        a. Add an error notification to the page and return `None`
        b. Return a tuple of two iterables or None, of requested templates
           and of requested pofiles IDs.
        c. Redirect and return `None`.
        """
        if not IHasTranslationTemplates.providedBy(self.context):
            raise NotImplementedError(
                'Subclass not implementing `IHasTranslationsTemplates` '
                'interface.  Either override getDefaultFormat implementation '
                'or implement `IHasTranslationsTemplates`.')

        translation_templates_ids = (
            self.context.getCurrentTranslationTemplates(just_ids=True))
        pofiles_ids = self.context.getCurrentTranslationFiles(just_ids=True)
        if not bool(pofiles_ids.any()):
            pofiles_ids = None
        return (translation_templates_ids, pofiles_ids)

    def modifyFormat(self, format):
        """Optional overridable: return format used to export `format` files.

        :param format: What file format to look up an exportable format for.
        :returns: The modified format.
        """
        return format

    def initialize(self):
        self.request_set = getUtility(IPOExportRequestSet)

        # Ask our derived class to figure out the default file format for this
        # export.  We do that here because the method may issue warnings,
        # which must be attached to our response early on.
        self.default_format = self.getDefaultFormat()

        if self.request.method != "POST":
            return

        bad_format_message = _("Please select a valid format for download.")
        format_name = self.modifyFormat(self.request.form.get("format"))
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
            self.request_set.addRequest(self.user, templates, pofiles, format)
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

        translation_exporter = getUtility(ITranslationExporter)
        exporters = translation_exporter.getExportersForSupportedFileFormat(
            self.default_format)
        for exporter in exporters:
            format = exporter.format
            if format == self.default_format:
                is_default = True
            else:
                is_default = False
            yield BrowserFormat(format.title, format.name, is_default)
