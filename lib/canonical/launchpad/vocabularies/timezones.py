# Copyright 2005 Canonical Ltd.  All rights reserved.

__all__ = [
    'TimezoneNameVocabulary',
    ]

__metaclass__ = type

import pytz

from zope.interface import directlyProvides
from zope.schema.vocabulary import SimpleVocabulary

from canonical.lazr.interfaces.timezone import ITimezoneNameVocabulary


# create a sorted list of the common time zone names, with UTC at the start
_values = sorted(pytz.common_timezones)
_values.remove('UTC')
_values.insert(0, 'UTC')

_timezone_vocab = SimpleVocabulary.fromValues(_values)
directlyProvides(_timezone_vocab, ITimezoneNameVocabulary)
del _values

def TimezoneNameVocabulary(context=None):
    return _timezone_vocab
