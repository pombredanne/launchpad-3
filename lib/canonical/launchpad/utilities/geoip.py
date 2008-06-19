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

from canonical.config import config
from canonical.launchpad.components.request_country import (
    ipaddress_from_request)
from canonical.launchpad.interfaces.country import ICountrySet
from canonical.launchpad.interfaces.geoip import (
    IGeoIP, IGeoIPRecord, IRequestLocalLanguages, IRequestPreferredLanguages)
from canonical.launchpad.interfaces.language import ILanguageSet


class GeoIP:

    implements(IGeoIP)

    def __init__(self):
        geoip_db = config.launchpad.geoip_db
        if not os.path.exists(geoip_db):
            # XXX: What should we do here!?
            pass
        self._gi = libGeoIP.open(geoip_db, libGeoIP.GEOIP_MEMORY_CACHE)

    def getRecordByAddress(self, ip_address):
        """See `IGeoIP`."""
        return self._gi.record_by_addr(ip_address)

    def country_by_addr(self, ip_address):
        if ip_address.startswith('127.'):
            # Use a South African IP address for localhost.
            ip_address = '196.36.161.227'
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

    implements(IGeoIPRecord)

    def __init__(self, request):
        self.request = request
        ip_address = ipaddress_from_request(self.request)
        if ip_address is None:
            # This happens during page testing, when the REMOTE_ADDR is not
            # set by Zope.
            ip_address = '127.0.0.1'
        # XXX: May not need this.
#         if ip_address.startswith('127.'):
#             # Use a South African IP address for localhost.
#             ip_address = '196.36.161.227'
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
