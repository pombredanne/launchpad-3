#!/usr/bin/python2.4
#

# Python imports
import sys
import re
from string import strip
from optparse import OptionParser

# LP imports
from canonical.lp import initZopeless

# launchpad imports
from canonical.launchpad.database import SourcePackageName
from canonical.launchpad.database import BinaryPackageName

class BaseNameList:
    """Base for Packages name list"""

    def __init__(self, filename):
        self.filename = filename
        self.list = []
        self._buildlist()
        self.list.sort()
        
    def _buildlist(self):
        try:
            f = open(self.filename)
        except IOError:
            print 'file %s not found. Exiting...' %self.filename
            sys.exit(1)
            
        for line in f:
            line = self._check_format(strip(line))
            if line:
                if not self._valid_name(line):
                    print ' - Invalid package name: %s' %line
                    continue
                self.list.append(line)

    def _check_format(self, name):
        assert isinstance(name, basestring), repr(name)
        try:
            # check that this is unicode data
            name.decode("utf-8").encode("utf-8")
            return name
        except UnicodeError:
            # check that this is latin-1 data
            s = name.decode("latin-1").encode("utf-8")
            s.decode("utf-8")
            return s

    def _valid_name(self, name):
        pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
        if re.match(pat, name):
            return True

class SourcePackageNameList(BaseNameList):
    """Build a sourcepackagename list from a given file"""

class BinaryPackageNameList(BaseNameList):
    """Build a binarypackagename list from a given file"""

class Counter:
    def __init__(self, interval):
        self._count = 0
        self.interval = interval

        if not interval:
            setattr(self, 'step', self._fake_step)
        else:
            setattr(self, 'step', self._step)

    def _step(self):
        self._count += 1
        if self._count > self.interval:
            self.reset()
            return True

    def _fake_step(self):
        return

    def reset(self):
        self._count = 0

class ProcessNames:
    def __init__(self, source_list, binary_list, commit_interval=0):
        self.source_list = source_list
        self.binary_list = binary_list
        self.ztm = initZopeless()
        self.interval = commit_interval
        self.count = Counter(commit_interval)

    def commit(self):
        print '\t\t@ Commiting...'
        self.ztm.commit()
        
        
    def processSource(self):
        if not self.source_list:
            return

        spnl = SourcePackageNameList(self.source_list).list
        
        for name in spnl:
            print '\t@ Evaluationg SourcePackageName %s' %name
            SourcePackageName.ensure(name)
            if self.count.step():
                self.commit()

        if self.interval:
            self.commit()
        self.count.reset()

    def processBinary(self):
        if not self.binary_list:
            return

        bpnl = BinaryPackageNameList(self.binary_list).list

        for name in bpnl:
            print '\t@ Evaluationg BinaryPackageName %s' %name
            BinaryPackageName.ensure(name)
            if self.count.step():
                self.commit()

        if self.interval:
            self.commit()
        self.count.reset()

if __name__ == '__main__':

    parser = OptionParser()

    parser.add_option("-s", "--source-file", dest="source_file",
                      help="SourcePackageName list file",
                      default=None)

    parser.add_option("-b", "--binary-file", dest="binary_file",
                      help="BinaryPackageName list file",
                      default=None)

    parser.add_option("-c", "--commit-interval", dest="commit_interval",
                      help="DB commit interval. Default 0 performs not commit.",
                      default=0)

    (options,args) = parser.parse_args()


    processor = ProcessNames(options.source_file,
                             options.binary_file,
                             int(options.commit_interval))

    processor.processSource()
    processor.processBinary()
