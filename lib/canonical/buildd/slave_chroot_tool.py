#!/usr/bin/python

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""
Build and manage chroots for launchpad (slave tool)
"""

__metaclass__ = type

import sys, os
from optparse import OptionParser
from ConfigParser import SafeConfigParser
import tempfile

class ChrootError(Exception):
    pass

slavebin = ""

def execute(cmd):
    """convenience method to raise an error if a command fails to run ok."""
    if os.system(cmd) != 0:
        raise OSError("Command %s failed" % cmd)

def affirmed(response):
    return response in ('y', 'yes', '')

class SlaveChrootBuilder:
    """Manage the process of building a chroot."""

    def __init__(self, conffile, slavebin):
        self.conffile = conffile
        self.bin = slavebin

    def loadConfig(self):
        """Parse the configuration file and check for expected values."""
        self.conf = SafeConfigParser()
        self.conf.read(self.conffile)
        self.config = {}

        required_config_items = [
            ('chroot', ['distribution', 'distroseries', 'distroseries',
                        'architecture', 'debootstraparchive', 'variant']),
            ('apt', ['archiveroot', 'components', 'pockets',
                     'signingdisabled']),
            ('buildd', ['user', 'group', 'paths', 'touchfiles', 'extrapkgs']),
            ('intervention', ['postbootstrap', 'postextrapkgs', 'postfinalapt',
                              'pretarup']),
            ]
        self.config = {}
        for section, keys in required_config_items:
            self.config[section] = {}
            for key in keys:
                if not self.conf.has_option(section, key):
                    raise ChrootError("Expected key %s in section %s" %
                                      (key,section))
                self.config[section][key] = self.conf.get(section, key)

    def makeTreeRoot(self):
        self.treeroot = tempfile.mkdtemp(dir=os.environ["HOME"],
                                         prefix="build-")
        self.buildid = "-".join(self.treeroot.split("-")[1:])
        print "Temporary work directory: %s" % self.treeroot
        print "Using build id %s for slave binaries" % self.buildid

    def intervene(self, stage):
        """Run a chroot if intervention at this stage is requested."""
        if self.config["intervention"][stage] == "1":
            print "Intervening at stage %s" % stage
            os.system("sudo chroot %s/chroot-autobuild /bin/su -" %
                      self.treeroot)

    def debootstrap(self):
        """Run debootstrap with the arguments from the config."""
        chrconf = self.config["chroot"]

        if chrconf["architecture"] == "host":
            print "Obtaining host architecture..."
            dpkg_proc = os.popen("dpkg --print-installation-architecture")
            chrconf["architecture"] = dpkg_proc.read().strip()

        print "Debootstrapping %s/%s/%s (%s) from %s ..." % (
            chrconf["distribution"],
            chrconf["distroseries"],
            chrconf["architecture"],
            chrconf["variant"],
            chrconf["debootstraparchive"])

        execute("sudo debootstrap --resolve-deps --arch %s "
                "--variant=%s %s %s %s" % (
                chrconf["architecture"],
                chrconf["variant"],
                chrconf["distroseries"],
                self.treeroot+"/chroot-autobuild",
                chrconf["debootstraparchive"]))

        # Make the user, paths and chown them...
        self.makeUserAndPaths()
        self.setupApt(True)

        print "Mouting chroot..."
        execute(self.bin+"/mount-chroot %s" % self.buildid)
        self.intervene("postbootstrap")

    def makeUserAndPaths(self):
        """Make the paths specified in the buildd group and touch files etc."""
        # 1. transfer the user and group
        print "Transferring user %s and group %s..." % (
            self.config['buildd']['user'],
            self.config['buildd']['group'])

        def xfer_element(what, filename):
            execute("sudo getent %s %s | "
                    "sudo sh -c 'cat >> %s/chroot-autobuild/etc/%s'"
                    %(filename, what, self.treeroot, filename))

        xfer_element(self.config['buildd']['user'], 'passwd')
        xfer_element(self.config['buildd']['user'], 'shadow')
        xfer_element(self.config['buildd']['group'], 'group')

        print "Making paths..."
        for path in self.config['buildd']['paths'].split():
            execute("sudo mkdir %s/chroot-autobuild/%s" % (
                self.treeroot, path))
            execute("sudo chown %s:%s %s/chroot-autobuild/%s" % (
                self.config['buildd']['user'],
                self.config['buildd']['group'],
                self.treeroot, path))

        print "Touching files..."
        for file in self.config['buildd']['touchfiles'].split():
            execute("sudo touch %s/chroot-autobuild/%s" % (
                self.treeroot, file))
            execute("sudo chown %s:%s %s/chroot-autobuild/%s" % (
                self.config['buildd']['user'],
                self.config['buildd']['group'],
                self.treeroot, file))

        print "Ensuring localhost is in /etc/hosts..."
        localhost_found = False
        try:
            f = open("%s/chroot-autobuild/etc/hosts", "r")
            r = f.read()
            f.close()
            if "localhost" in r:
                localhost_found = True
        except IOError:
            # Swallow the IOError and assume we didn't find localhost
            pass
        if not localhost_found:
            print "Did not find a localhost entry. Making /etc/hosts in chroot."
            execute("echo 127.0.0.1 localhost | "
                    "sudo sh -c 'cat >> %s/chroot-autobuild/etc/hosts'" %
                self.treeroot)

    def setupApt(self, bootstrap=False):
        root = self.config['apt']['archiveroot']
        if bootstrap:
            print "Configuring bootstrap archive apt sources"
            root = self.config['chroot']['debootstraparchive']
        else:
            print "Configuring production archive apt sources"

        pockets = ["-" + pocket for pocket in
                   self.config['apt']['pockets'].split()]
        pockets.append('')

        # This turns the string "a b c d"
        # into  [ ["a"], ["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d"] ]
        components = self.config['apt']['components'].split()
        component_sets = [components[:i+1] for i in range(len(components))]

        for component_set in component_sets:
            execute("sudo rm -f %s/chroot-autobuild/etc/apt/sources.list.%s" %
                    (self.treeroot, component_set[-1]))
            execute("sudo touch %s/chroot-autobuild/etc/apt/sources.list.%s" %
                    (self.treeroot, component_set[-1]))

            for pocket in pockets:
                execute("echo deb %s %s%s %s | "
                        "sudo sh -c 'cat >> "
                        "%s/chroot-autobuild/etc/apt/sources.list.%s'" %(
                    root, self.config['chroot']['distroseries'],
                    pocket, " ".join(component_set),
                    self.treeroot, component_set[-1]))

        execute("sudo rm -f %s/chroot-autobuild/etc/apt/sources.list" %(
            self.treeroot))

        execute("sudo ln -s sources.list.%s "
                "%s/chroot-autobuild/etc/apt/sources.list" %(
            components[0], self.treeroot))

        if self.config['apt']['signingdisabled'] == '1':
            execute(r'echo APT::Get::AllowUnauthenticated \"1\"\; | '
                    r'sudo sh -c "cat >> '
                    r'%s/chroot-autobuild/etc/apt/apt.conf.d/99buildd"' %
                    self.treeroot)
        else:
            execute("sudo rm -f "
                    "%s/chroot-autobuild/etc/apt/apt.conf.d/99buildd" %
                    self.treeroot)

    def umount(self):
        """Unmount the chroot ready for tarring up."""
        self.intervene("pretarup")
        execute(self.bin + "/scan-for-processes %s || true" % self.buildid)
        execute(self.bin + "/umount-chroot %s" % self.buildid)

    def run(self):
        self.loadConfig()
        # Okay, we know all the configuration we're expecting has been
        # loaded into self.config (dict of dicts)
        self.makeTreeRoot()
        self.debootstrap()
        # The chroot is made and currently configured for pre-buildd
        # package installation, so update it...
        execute(self.bin + "/update-debian-chroot %s" % self.buildid)
        # And install anything asked for in the config
        execute("sudo chroot %s/chroot-autobuild apt-get install %s" % (
            self.treeroot, self.config['buildd']['extrapkgs']))
        self.intervene('postextrapkgs')
        # Set us up for the internal apt config
        self.setupApt()
        self.intervene('postfinalapt')

        self.umount()
        # And tar it up...

        print "Happy to repack? [Y]"
        yesno = sys.stdin.readline().strip().lower()

        if affirmed(yesno):
            print "Preparing chroot tarball..."
            chroottarname = ("chroot-%s-%s-%s.tar.bz2"
                             %(self.config['chroot']['distribution'],
                               self.config['chroot']['distroseries'],
                               self.config['chroot']['architecture']))
            execute("sudo tar -C %s -cjf %s chroot-autobuild"
                    %(self.treeroot, chroottarname))
            execute("sudo chown $USER %s" % chroottarname)

        print "Cleaning up..."
        execute(self.bin + "/remove-build %s" % self.buildid)

        if affirmed(yesno):
            print "Constructed chroot-%s-%s-%s.tar.bz2" % (
                self.config['chroot']['distribution'],
                self.config['chroot']['distroseries'],
                self.config['chroot']['architecture'])

def process(chroottar, slavebin, cmd=None):
    """Unpack, mount, chroot in, umount, repack, the chroot"""
    # We use the slavebin for the buildds to do some tasks
    execute("mkdir $HOME/build-chroot-tool")
    print "Unpacking..."
    execute(slavebin + "/unpack-chroot chroot-tool " + chroottar)
    print "Mounting..."
    execute(slavebin + "/mount-chroot chroot-tool")
    # execute the desired command within the chroot
    if cmd:
        print "Chrooting in..."
        execute(cmd)
    # We eat the result code of scanning for processes
    print "Scanning for processes to kill..."
    os.system(slavebin + "/scan-for-processes chroot-tool")
    print "Unmounting..."
    execute(slavebin + "/umount-chroot chroot-tool")
    print "Happy to repack? [Y]"
    yesno = sys.stdin.readline().strip().lower()
    if affirmed(yesno):
        print "Re-packing..."
        execute("sudo tar -C $HOME/build-chroot-tool -cjf %s chroot-autobuild"
                % chroottar)
        execute("sudo chown $USER %s" % chroottar)
    print "Cleaning up..."
    execute(slavebin + "/remove-build chroot-tool")
    if affirmed(yesno):
        print "Done, updated %s" % chroottar
    else:
        print "Done, did not update %s" % chroottar

def do_generate(conffile, slavebin):
    """Generate a chroot based on the configuration file supplied"""
    # Simple override which helps a lot during bootstrapping
    os.environ["LC_ALL"] = "C"
    SlaveChrootBuilder(conffile, slavebin).run()

def do_intervene(chroottar, slavebin):
    chroot_in = ("sudo chroot $HOME/build-chroot-tool/chroot-autobuild "
                 "/bin/su -")
    process(chroottar, slavebin, cmd=chroot_in)

def do_upgrade(chroottar, slavebin):
    chroot_upgrade = slavebin + "/update-debian-chroot chroot-tool"
    process(chroottar, slavebin, cmd=chroot_upgrade)

def main():
    oparser = OptionParser()

    oparser.add_option("-r", "--binaryroot", dest="binaryroot",
                       metavar="BINARYROOT",
                       default="/usr/share/launchpad-buildd/slavebin",
                       help="root of slave binaries")

    oparser.add_option( "-g", "--generate", dest="generate",
                        metavar="CONFIG", default=None,
                        help="configuration file for a chroot to generate")

    oparser.add_option("-i", "--intervene", dest="intervene",
                       metavar="CHROOT", default=None,
                       help="chroot to unpack and chroot into")

    oparser.add_option("-u", "--upgrade", dest="upgrade",
                       metavar="CHROOT", default=None,
                       help="chroot to unpack and upgrade")

    (opts,args) = oparser.parse_args()

    slavebin = opts.binaryroot

    actions = {
        opts.generate: do_generate,
        opts.intervene: do_intervene,
        opts.upgrade: do_upgrade,
        }

    for option, function in actions.items():
        if option is not None:
            opt_path = os.path.abspath(option)
            function(opt_path, slavebin)
            return

if __name__ == "__main__":
    main()
