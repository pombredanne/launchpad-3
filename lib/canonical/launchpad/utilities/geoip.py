
import GeoIP as libGeoIP

from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import IGeoIP, ICountrySet

__all__ = ['GeoIP']

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
        return countryset[countrycode]
