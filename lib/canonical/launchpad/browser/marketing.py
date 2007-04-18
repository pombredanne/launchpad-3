# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Views for the marketing microsite."""

__metaclass__ = type

__all__ = [
    'MarketingBreadcrumbNameView',
    'MarketingSubnavigationView'
    ]


from canonical.launchpad.helpers import convertToHtmlCode
from canonical.launchpad.layers import (
    LaunchpadLayer, CodeLayer, BugsLayer, BlueprintsLayer, TranslationsLayer,
    AnswersLayer)

class MarketingSubnavigationView:
    """View used to render the navigation links on the marketing microsite."""

    @property
    def application_name(self):
        """Return the application name based on the layer we are in."""
        request = self.request

        # It is important to test LaunchpadLayer last because all other
        # layers extends from it.
        if CodeLayer.providedBy(request):
            return 'Code'
        elif BugsLayer.providedBy(request):
            return 'Bugs'
        elif BlueprintsLayer.providedBy(request):
            return 'Blueprints'
        elif TranslationsLayer.providedBy(request):
            return 'Translations'
        elif AnswersLayer.providedBy(request):
            return 'Answers'
        elif LaunchpadLayer.providedBy(request):
            return 'Launchpad'
        else:
            assert False, 'Unknown layer type: %s' % request

    @property
    def overview_selected_class(self):
        """Return the HTML class to use when the current page is the +about
        page.
        """
        if str(self.request.URL).endswith('+about'):
            return 'class="current"'
        return ""

    @property
    def tour_selected_class(self):
        """Return the HTML class to use when the current page is the +tour
        page.
        """
        if str(self.request.URL).endswith('+tour'):
            return 'class="current"'
        return ""

    @property
    def faq_selected_class(self):
        """Return True when the current page is the +faq page."""
        if str(self.request.URL).endswith('+faq'):
            return 'class="current"'
        return ""

    def __call__(self):
        """Render the navigation menu."""
        # That menu should only appear on the application site, not the
        # generic page.
        if self.application_name == 'Launchpad':
            return u""

        return u"""
        <dl id="sub-navigation">
          <dt>Sub-navigation<dt>
          <dd>
            <ul>
              <li %(overview_selected_class)s><a href="+about">%(application)s overview</a></li>
              <li %(tour_selected_class)s><a href="+tour">%(application)s tour</a></li>
              <li %(faq_selected_class)s><a href="+faq">%(application)s FAQs</a></li>
            </ul>
            <ul id="global">
               <li id="liContact"><a href="%(contact_email)s">Contact us</a></li>
            </ul>
          </dd>
        </dl>
       """ % {'application': self.application_name,
              'overview_selected_class': self.overview_selected_class,
              'faq_selected_class': self.faq_selected_class,
              'tour_selected_class': self.tour_selected_class,
              'contact_email': convertToHtmlCode(
                'mailto:feedback@launchpad.net')}


class MarketingBreadcrumbNameView:
    """View helper for the breadcrumbs text on the marketing pages."""

    def __call__(self):
        """Render the name that should appear in the current breadcrumb."""
        url = str(self.request.URL)
        if url.endswith('+about'):
            return u'About'
        elif url.endswith('+faq'):
            return u'FAQs'
        elif url.endswith('+tour'):
            return u'Take a tour'
        else:
            assert False, "Can't find breadcrumb name from URL: %s" % url

