# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from zope.interface import implements
from sqlobject import (
    BoolCol, ForeignKey, IntCol, MultipleJoin, SQLMultipleJoin,
    SQLObjectNotFound, SQLRelatedJoin, StringCol)
from sqlobject.sqlbuilder import AND, OR, SQLConstant

