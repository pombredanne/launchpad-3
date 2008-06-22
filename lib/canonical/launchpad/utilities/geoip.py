# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__all__ = [
    'GeoIP',
    'GeoIPRequest',
    'RequestLocalLanguages',
    'RequestPreferredLanguages',
    ]

import os

import GeoIP as libGeoIP

from zope.interface import implements
from zope.component import getUtility

from zope.i18n.interfaces import IUserPreferredLanguages

from canonical.launchpad.components.request_country import (
    ipaddress_from_request)
from canonical.launchpad.interfaces.country import ICountrySet
from canonical.launchpad.interfaces.geoip import (
    IGeoIP, IGeoIPRecord, IRequestLocalLanguages, IRequestPreferredLanguages)
from canonical.launchpad.interfaces.language import ILanguageSet

GEOIP_CITY_DB = '/usr/share/GeoIP/GeoIPCity.dat'
GEOIP_CITY_LITE_DB = '/usr/share/GeoIP/GeoLiteCity.dat'


class GeoIP:
    """See `IGeoIP`."""
    implements(IGeoIP)

    def __init__(self):
        if os.path.exists(GEOIP_CITY_DB):
            db = GEOIP_CITY_DB
        elif os.path.exists(GEOIP_CITY_LITE_DB):
            db = GEOIP_CITY_LITE_DB
        else:
            raise NoGeoIPDatabaseFound(
                "No GeoIP DB found. Please use utilities/get-geoip-db to "
                "install it.")
        self._gi = libGeoIP.open(db, libGeoIP.GEOIP_MEMORY_CACHE)

    def getRecordByAddress(self, ip_address):
        """See `IGeoIP`."""
        ip_address = ensure_address_is_not_private(ip_address)
        return self._gi.record_by_addr(ip_address)

    def getCountryByAddr(self, ip_address):
        """See `IGeoIP`."""
        ip_address = ensure_address_is_not_private(ip_address)
        geoip_record = self.getRecordByAddress(ip_address)
        if geoip_record is None:
            return None
        countrycode = geoip_record['country_code']

        countryset = getUtility(ICountrySet)
        try:
            country = countryset[countrycode]
        except KeyError:
            return None
        else:
            return country


class GeoIPRequest:
    """An adapter for a BrowserRequest into an IGeoIPRecord."""
    implements(IGeoIPRecord)

    def __init__(self, request):
        self.request = request
        ip_address = ipaddress_from_request(self.request)
        if ip_address is None:
            # This happens during page testing, when the REMOTE_ADDR is not
            # set by Zope.
            ip_address = '127.0.0.1'
        ip_address = ensure_address_is_not_private(ip_address)
        self.ip_address = ip_address
        self.geoip_record = getUtility(IGeoIP).getRecordByAddress(
            self.ip_address)

    @property
    def latitude(self):
        """See `IGeoIPRecord`."""
        if self.geoip_record is None:
            return None
        return self.geoip_record['latitude']

    @property
    def longitude(self):
        """See `IGeoIPRecord`."""
        if self.geoip_record is None:
            return None
        return self.geoip_record['longitude']

    @property
    def time_zone(self):
        """See `IGeoIPRecord`."""
        if self.geoip_record is None:
            return None
        return self.geoip_record['time_zone']


class RequestLocalLanguages(object):

    implements(IRequestLocalLanguages)

    def __init__(self, request):
        self.request = request

    def getLocalLanguages(self):
        """See the IRequestLocationLanguages interface"""
        ip_addr = ipaddress_from_request(self.request)
        if ip_addr is None:
            # this happens during page testing, when the REMOTE_ADDR is not
            # set by Zope
            ip_addr = '127.0.0.1'
        gi = getUtility(IGeoIP)
        country = gi.country_by_addr(ip_addr)
        if country in [None, 'A0', 'A1', 'A2']:
            return []

        languages = [
            language for language in country.languages if language.visible]
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


def ensure_address_is_not_private(ip_address):
    """Return the given IP address if it doesn't start with '127.'.

    If it does start with '127.' then we return a South African IP address.
    """
    if ip_address.startswith('127.'):
        return '196.36.161.227'
    return ip_address


class NoGeoIPDatabaseFound(Exception):
    """No GeoIP database was found."""
