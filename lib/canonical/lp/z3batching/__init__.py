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
##############################################################################
"""Batching Support

$Id$
"""
from zope.interface import implements
from interfaces import IBatch

class Batch(object):
    implements(IBatch)

    def __init__(self, list, start=0, size=20):
        self.list = list
        self.start = start
        if len(list) == 0:
            self.start = -1
        elif start >= len(list):
            raise IndexError, 'start index key out of range'
        self.size = size
        self.trueSize = size
        if start+size >= len(list):
            self.trueSize = len(list)-start
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
        if start >= len(self.list):
            return None
        return Batch(self.list, start, self.size)
    
    def prevBatch(self):
        start = self.start - self.size
        if start < 0:
            return None
        return Batch(self.list, start, self.size)

    def first(self):
        return self.list[self.start]

    def last(self):
        return self.list[self.end]

    def total(self):
        return len(self.list)

    def startNumber(self):
        return self.start+1

    def endNumber(self):
        return self.end+1
