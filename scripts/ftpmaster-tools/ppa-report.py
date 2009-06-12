#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
import _pythonpath

from lp.soyuz.scripts.ppareport import PPAReportScript


if __name__ == '__main__':
    script = PPAReportScript('ppareport', dbuser='ro')
    script.run()
