
from zope.interface import Interface

class IGeoIP(Interface):

    def country_by_addr(ip_address):
        """Find a country based on an IP address in text dotted-address
        notation, for example '196.131.31.25'"""

