# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser views for translation pages for sourcepackages."""

__metaclass__ = type

__all__ = [
    'SourcePackageTranslationsExportView',
    'SourcePackageTranslationsView',
    ]

from canonical.launchpad.webapp import (
    ApplicationMenu, enabled_with_permission, GetitemNavigation, Link,
    NavigationMenu, redirection, StandardLaunchpadFacets, stepto)
from lp.translations.browser.poexportrequest import BaseExportView
from lp.translations.browser.translations import TranslationsMixin
from lp.registry.interfaces.sourcepackage import ISourcePackage


class SourcePackageTranslationsView(TranslationsMixin):
    @property
    def potemplates(self):
        return list(self.context.getCurrentTranslationTemplates())


class SourcePackageTranslationsMenu(NavigationMenu):
    usedfor = ISourcePackage
    facet = 'translations'
    links = ('overview', 'download', 'imports')

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text)

    @enabled_with_permission('launchpad.ExpensiveRequest')
    def download(self):
        text = 'Download'
        enabled = bool(self.context.getCurrentTranslationTemplates().any())
        return Link('+export', text, icon='download', enabled=enabled)

    def overview(self):
        return Link('', 'Overview', icon='info')


class SourcePackageTranslationsExportView(BaseExportView):
    """Request tarball export of all translations for a source package."""
    pass
