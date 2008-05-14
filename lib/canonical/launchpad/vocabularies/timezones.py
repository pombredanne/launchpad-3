# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import pytz

from zope.schema.vocabulary import SimpleVocabulary

__all__ = ['TimezoneNameVocabulary']


class TimezoneNameVocabulary(SimpleVocabulary):

    def __init__(self, terms, *interfaces):
        # Create a sorted list of the common time zone names, with UTC at the
        # start.
        values = sorted(pytz.common_timezones)
        values.remove('UTC')
        values.insert(0, 'UTC')
        terms = [self.createTerm(value) for value in values]
        super(TimezoneNameVocabulary, self).__init__(terms)
