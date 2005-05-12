
import pytz

from zope.interface import implements

from canonical.launchpad.interfaces import IPerson, IRequestTzInfo

_utc_tz = pytz.timezone('UTC')

class RequestTzInfo(object):
    implements(IRequestTzInfo)

    def __init__(self, request):
        self.request = request

    def getTzInfo(self):
        person = IPerson(self.request.principal, None)
        if person and person.timezone_name:
            try:
                return pytz.timezone(person.timezone_name)
            except KeyError:
                pass
        # if not logged in, or using an unknown timezone ...
        return _utc_tz
