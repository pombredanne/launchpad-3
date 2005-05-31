#!/usr/bin/python
# Copyright 2004 Canonical Ltd, all rights reserved (for now?).
# Author: Rob Weir <rob.weir@canonical.com>

import sys

from CommandLineRunner import Doer

if len (sys.argv) > 3:
    level = int(sys.argv[3])
else:
    level = 2

importer = Doer(level)
importer.makeJob(sys.argv[1], sys.argv[2])
importer.importPackage()
