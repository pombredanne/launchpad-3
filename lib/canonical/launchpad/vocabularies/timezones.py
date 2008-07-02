# Copyright 2005 Canonical Ltd.  All rights reserved.

__all__ = [
    'TimezoneNameVocabulary',
    ]

__metaclass__ = type

import pytz
import traceback

from zope.interface import alsoProvides
from zope.schema.vocabulary import SimpleVocabulary

from canonical.lazr.interfaces.timezone import ITimezoneNameVocabulary
from canonical.launchpad.webapp.errorlog import report_timezone_oops


# create a sorted list of the common time zone names, with UTC at the start
_values = sorted(pytz.common_timezones)
_values.remove('UTC')
_values.insert(0, 'UTC')
# The tzdata package may not contain all the timezone files that pytz
# thinks exist.
for timezone_name in _values:
    # pylint: disable-msg=W0702
    # Disabling pylint warning for "except:" block which
    # doesn't specify an exception.
    try:
        pytz.timezone(timezone_name)
    except:
        # We already know that this timezone is failing. I am removing only
        # after an exception occurs in case US/Pacific-New gets re-added to
        # the tzdata package.
        if timezone_name != 'US/Pacific-New':
            report_timezone_oops("Invalid timezone (%s)" % timezone_name)
        _values.remove(timezone_name)

_timezone_vocab = SimpleVocabulary.fromValues(_values)
alsoProvides(_timezone_vocab, ITimezoneNameVocabulary)
del _values

def TimezoneNameVocabulary(context=None):
    return _timezone_vocab
