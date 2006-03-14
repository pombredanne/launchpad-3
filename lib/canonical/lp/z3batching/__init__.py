##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
# Some parts Copyright 2005 Canonical Ltd.
#
##############################################################################

"""
Zope-derived Batching Support
"""

from zope.interface import implements
from interfaces import IBatch

from sqlos.interfaces import ISelectResults

# XXX: replace this with a configuration option
#   -- kiko, 2006-03-13
BATCH_SIZE = 50

class Batch(object):
    implements(IBatch)

    def __init__(self, results, start=0, size=None, _listlength=None):
        if results is None:
            results = []
        self.list = results

        # We only check the length of the list once, because if the
        # list is a SelectResults from SQLObject, list.count() hits
        # the database each time.  Ideally SQLObject would be smart
        # enough to cache it for us, but for now we take the easy
        # route.
        #   -- Andrew Bennetts, 2005-06-22
        if _listlength is None:
            if ISelectResults.providedBy(results):
                listlength = results.count()
            else:
                listlength = len(results)
        else:
            listlength = _listlength
        self.listlength = listlength

        if size is None:
            size = BATCH_SIZE
        self.size = size

        if start >= listlength:
            self.trueSize = 0
        elif start+size >= listlength:
            self.trueSize = listlength-start
        else:
            self.trueSize = size

        if listlength == 0:
            start = -1

        self.start = start
        if self.trueSize == 0:
            self.end = start
        else:
            self.end = start+self.trueSize-1

    def __len__(self):
        if self.trueSize < 0:
            return 0
        else:
            return self.trueSize

    def __getitem__(self, key):
        if key >= self.trueSize:
            raise IndexError, 'batch index out of range'
        return self.list[self.start+key]

    def __iter__(self): 
        return iter(self.list[self.start:self.end+1])

    def __contains__(self, item):
        return item in self.__iter__()

    def nextBatch(self):
        start = self.start + self.size
        if start >= self.listlength:
            return None
        return Batch(self.list, start, self.size, _listlength=self.listlength)

    def prevBatch(self):
        if self.start > self.listlength:
            start = self.listlength - (self.listlength % self.size)
        else:
            start = self.start - self.size
        if start < 0:
            return None
        return Batch(self.list, start, self.size, _listlength=self.listlength)

    def first(self):
        return self.list[self.start]

    def last(self):
        return self.list[self.end]

    def total(self):
        return self.listlength

    def startNumber(self):
        return self.start+1

    def endNumber(self):
        return self.end+1

