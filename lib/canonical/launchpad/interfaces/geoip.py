
from zope.interface import Interface

__all__ = ['IGeoIP', 'IRequestLocalLanguages', 'IRequestPreferredLanguages']

class IGeoIP(Interface):

    def country_by_addr(ip_address):
        """Find a country based on an IP address in text dotted-address
        notation, for example '196.131.31.25'"""


class IRequestLocalLanguages(Interface):

    def getLocalLanguages():
        """Return a list of the Language objects which represent languages
        spoken in the country from which that IP address is likely to be
        coming."""

class IRequestPreferredLanguages(Interface):

    def getPreferredLanguages():
        """Return a list of the Language objects which represent languages
        listed in the HTTP_ACCEPT_LANGUAGES header."""

