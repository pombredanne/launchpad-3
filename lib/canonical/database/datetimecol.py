# Copyright 2005 Canonical Ltd.  All rights reserved.
'''UtcDateTimeCol for SQLObject'''

__all__ = ['UtcDateTimeCol']

import pytz
import storm.sqlobject


class UtcDateTimeCol(storm.sqlobject.UtcDateTimeCol):
    _kwargs = {'tzinfo': pytz.timezone('UTC')}
