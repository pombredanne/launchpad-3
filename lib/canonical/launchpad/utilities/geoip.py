
import GeoIP as libGeoIP

from zope.interface import implements
from zope.component import getUtility

from zope.i18n.interfaces import IUserPreferredLanguages

from canonical.launchpad.interfaces import IGeoIP, ICountrySet, \
    ILanguageSet, IRequestLocalLanguages, IRequestPreferredLanguages

__all__ = ['GeoIP', 'RequestLocalLanguages', 'RequestPreferredLanguages']


class GeoIP:

    implements(IGeoIP)

    def __init__(self):
        self._gi = libGeoIP.new(libGeoIP.GEOIP_MEMORY_CACHE)

    def country_by_addr(self, ip_address):
        countrycode = self._gi.country_code_by_addr(ip_address)
        if countrycode is None:
            if ip_address == '127.0.0.1':
                countrycode = 'ZA'
            else:
                return None
        countryset = getUtility(ICountrySet)

        try:
            country = countryset[countrycode]
        except KeyError:
            return None
        else:
            return country


class RequestLocalLanguages(object):

    implements(IRequestLocalLanguages)

    def __init__(self, request):
        self.request = request

    def getLocalLanguages(self):
        """See the IRequestLocationLanguages interface"""
        ip_addr = self.request.get('HTTP_X_FORWARDED_FOR', None)
        if ip_addr is None:
            ip_addr = self.request.get('REMOTE_ADDR', None)
        if ip_addr is None:
            # this happens during page testing, when the REMOTE_ADDR is not
            # set by Zope
            ip_addr = '127.0.0.1'
        gi = getUtility(IGeoIP)
        country = gi.country_by_addr(ip_addr)
        if country in [None, 'A0', 'A1', 'A2']:
            return []

        languages = [language for language in country.languages if language.visible]
        return sorted(languages, key=lambda x: x.englishname)


class RequestPreferredLanguages(object):

    implements(IRequestPreferredLanguages)

    def __init__(self, request):
        self.request = request

    def getPreferredLanguages(self):
        """See the IRequestPreferredLanguages interface"""

        codes = IUserPreferredLanguages(self.request).getPreferredLanguages()
        languageset = getUtility(ILanguageSet)
        languages = []

        for code in codes:
            # We need to ensure that the code received contains only ASCII
            # characters otherwise SQLObject will crash if it receives a query
            # with non printable ASCII characters.
            if isinstance(code, str):
                try:
                    code = code.decode('ASCII')
                except UnicodeDecodeError:
                    # skip language codes that can't be represented in ASCII
                    continue
            else:
                try:
                    code = code.encode('ASCII')
                except UnicodeEncodeError:
                    # skip language codes that can't be represented in ASCII
                    continue
            code = languageset.canonicalise_language_code(code)
            try:
                languages.append(languageset[code])
            except KeyError:
                pass

        languages = [language for language in languages if language.visible]
        return sorted(languages, key=lambda x: x.englishname)
