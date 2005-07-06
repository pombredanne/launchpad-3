# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from canonical.launchpad.interfaces import IGeoIP

def request_country(request):
    """Adapt a request to the country in which the request was made.

    Return None if the remote IP address is unknown or its country is not in
    our database.
    """

    ipaddress = request.get('HTTP_X_FORWARDED_FOR')

    if ipaddress is None:
        ipaddress = request.get('REMOTE_ADDR')

    if ipaddress is None:
        return None

    return getUtility(IGeoIP).country_by_addr(ipaddress)

