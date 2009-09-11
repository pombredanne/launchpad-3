#!/usr/bin/python

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Executable for the ec2test script."""

__metaclass__ = type

import os
import sys

sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib'))

from devscripts.ec2test import main
main()
