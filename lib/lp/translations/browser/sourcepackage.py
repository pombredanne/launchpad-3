# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser views for translation pages for sourcepackages."""

__metaclass__ = type

__all__ = [
    'SourcePackageTranslationsExportView',
    'SourcePackageTranslationsView',
    ]

from canonical.launchpad.webapp import (
    canonical_url,
    enabled_with_permission,
    Link,
    NavigationMenu,
    )
from canonical.launchpad.webapp.authorization import check_permission
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.translations.browser.poexportrequest import BaseExportView
from lp.translations.browser.translations import TranslationsMixin
from lp.translations.browser.translationsharing import (
    TranslationSharingDetailsMixin,
    )
from lp.translations.utilities.translationsharinginfo import (
    has_upstream_template,
    get_upstream_sharing_info,
    )


class SourcePackageTranslationsView(TranslationsMixin,
                                    TranslationSharingDetailsMixin):

    @property
    def potemplates(self):
        return list(self.context.getCurrentTranslationTemplates())

    @property
    def label(self):
        return "Translations for %s" % self.context.displayname

    def is_sharing(self):
        return has_upstream_template(self.context)

    @property
    def sharing_productseries(self):
        infos = get_upstream_sharing_info(self.context)
        if len(infos) == 0:
            return None

        productseries, template = infos[0]
        return productseries

    def getTranslationTarget(self):
        """See `TranslationSharingDetailsMixin`."""
        return self.context

    def can_edit_sharing_details(self):
        return check_permission('launchpad.Edit', self.context.distroseries)


class SourcePackageTranslationsMenu(NavigationMenu):
    usedfor = ISourcePackage
    facet = 'translations'
    links = ('overview', 'download', 'imports')

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text, site='translations')

    @enabled_with_permission('launchpad.ExpensiveRequest')
    def download(self):
        text = 'Download'
        enabled = bool(self.context.getCurrentTranslationTemplates().any())
        return Link('+export', text, icon='download', enabled=enabled,
                    site='translations')

    def overview(self):
        return Link('', 'Overview', icon='info', site='translations')


class SourcePackageTranslationsExportView(BaseExportView):
    """Request tarball export of all translations for a source package."""

    page_title = "Download"

    @property
    def download_description(self):
        """Current context description used inline in paragraphs."""
        return "%s package in %s %s" % (
            self.context.sourcepackagename.name,
            self.context.distroseries.distribution.displayname,
            self.context.distroseries.displayname)

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    @property
    def label(self):
        return "Download translations for %s" % self.download_description
