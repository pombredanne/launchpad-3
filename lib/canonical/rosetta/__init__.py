# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: b2309f78-891e-434e-bcdc-9fa635ec013d
#
# This is the canonical.rosetta python package.

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from canonical.launchpad.interfaces import IRosettaApplication, IProductSet, \
        ICountrySet, IGeoIP, IRequestPreferredLanguages
from canonical.publication import rootObject


class RosettaApplication:
    implements(IRosettaApplication)

    __parent__ = rootObject

    def __init__(self):
        self.title = 'Rosetta: Translations in the Launchpad'

    def translatables(self, translationProject=None):
        """This will give a list of the translatables in the given
        Translation Project. For the moment it just returns every
        translatable product."""
        products = getUtility(IProductSet)
        return products.translatables(translationProject)

    name = 'Rosetta'

class RosettaApplicationView(object):

    countryPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-country-langs.pt')

    browserLangPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-browser-langs.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def requestCountry(self):
        ip = self.request.get('HTTP_X_FORWARDED_FOR', None)
        if ip is None:
            ip = self.request.get('REMOTE_ADDR', None)
        if ip is None:
            return None
        gi = getUtility(IGeoIP)
        return gi.country_by_addr(ip)

    def browserLanguages(self):
        return IRequestPreferredLanguages(self.request).getPreferredLanguages()

