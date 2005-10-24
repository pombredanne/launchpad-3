#!/usr/bin/python
from canonical.lp import initZopeless
from importd.bzrsync import BzrSync
import sys, os

tm = initZopeless(dbuser="importd")

tm.begin()
BzrSync(int(sys.argv[1])).syncHistory()
tm.commit()

