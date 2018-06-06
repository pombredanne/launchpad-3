#!/usr/bin/python -S
#
# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

import _pythonpath

from launchpad_loggerhead.wsgi import LoggerheadApplication


if __name__ == "__main__":
    LoggerheadApplication().run()
