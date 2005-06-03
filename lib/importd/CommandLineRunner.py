#!/usr/bin/python
# Copyright 2004 Canonical Ltd, all rights reserved (for now?).
# Author: Rob Weir <rob.weir@canonical.com>
#         David Allouche <david@allouche.net>

import os
import sys
import pickle
import logging

import Job
from canonical.database.sqlbase import quote
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database import Product
from importd.Job import Job
from canonical.lp import initZopeless
import canonical

import pybaz
import pybaz.backends.forkexec
pybaz.backend.spawning_strategy = pybaz.backends.forkexec.PyArchSpawningStrategy
import gnarly.process
import gnarly.process.unix_process
gnarly.process.Popen = gnarly.process.unix_process.Popen


class Doer(object):

    def __init__(self, log_level=2):
        #how portable is this conversion?
        self.logger=logging.Logger("importd", 50 - log_level*10)
        handler=logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        self.logger.addHandler(handler)
        initZopeless()

    def makeJob(self, productName, seriesName):
        """Create the Job object from the source source name (packagename)."""
        product = Product.byName(productName)
        series = product.getSeries(seriesName)
        self._job = Job()
        self._job.from_series(series)
        self._job.slave_home = os.environ['IMPORTD_SLAVE_HOME']
        self._job.archive_mirror_dir = os.environ['IMPORTD_MIRRORS']
        print "Job = %s" % self._job

    def importPackage(self):
        """start a synchronous import"""
        self._job.TYPE = 'import'
        self._job.nukeTargets(logger=self.logger)
        self._job.runJob(logger=self.logger, dir='.')

    def syncPackage(self):
        """start a synchronous sync"""
        self._job.TYPE = 'sync'
        self._job.runJob(logger=self.logger, dir='.')
        self._job.mirrorTarget(logger=self.logger, dir='.')

    def loadJob(self, jobfile_name):
        """Load the Job object from a pickle file."""
        jobfile = open(jobfile_name, 'r')
        self._job = pickle.load(jobfile)
        jobfile.close()

    def runMethod(self, method, dirname):
        getattr(self._job, method)(logger=self.logger, dir=dirname)


def main():
    jobfile_name, method, dirname = sys.argv[1:]
    doer = Doer()
    doer.loadJob(jobfile_name)
    doer.runMethod(method, dirname)

if __name__ == '__main__':
    main()
