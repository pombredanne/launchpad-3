#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.

import canonical.lp
from canonical.launchpad.database import Project

def showprojects():
    for project in Project.select():
        print project.name

if __name__ == '__main__':
    ztm = canonical.lp.initZopeless()

    showprojects()

