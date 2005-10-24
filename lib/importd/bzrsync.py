#! /usr/bin/env python

import random
import sys

msg, status = random.choice([('success', 0), ('failure', 1)])

print msg
sys.exit(status)
