# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import os.path
import pwd
from subprocess import call
import sys


RETCODE_SUCCESS = 0
RETCODE_FAILURE_INSTALL = 200
RETCODE_FAILURE_BUILD_TREE = 201
RETCODE_FAILURE_INSTALL_BUILD_DEPS = 202
RETCODE_FAILURE_BUILD_SOURCE_PACKAGE = 203


class RecipeBuilder:

    def __init__(self, build_id, author_name, author_email,
                 package_name, suite):
        self.author_name = author_name
        self.author_email = author_email
        self.package_name = package_name
        self.suite = suite
        self.base_branch = None
        self.chroot_path = get_build_path(build_id, 'chroot-autobuild')
        self.work_dir_relative = os.environ['HOME'] + '/work'
        self.work_dir = os.path.join(self.chroot_path,
                                     self.work_dir_relative[1:])
        self.tree_path = os.path.join(self.work_dir, 'tree')
        self.username = pwd.getpwuid(os.getuid())[0]

    def install(self):
        return self.chroot(['apt-get', 'install', '-y', 'pbuilder',
                            'bzr-builder'])

    def buildTree(self):
        recipe_path_relative = os.path.join(self.work_dir_relative, 'recipe')
        manifest_path_relative = os.path.join(self.work_dir_relative,
                                              'manifest')
        self.tree_path_relative = os.path.join(self.work_dir_relative, 'tree')
        env = {'DEBEMAIL': self.author_email,
               'DEBFULLNAME': self.author_name}
        retcode = self.chroot(['su', '-c', 'bzr dailydeb --no-build %s %s'
                               ' --manifest %s' % (
                              recipe_path_relative, self.tree_path_relative,
                              manifest_path_relative), self.username],
                              env=env)
        if retcode == 0:
            for source in os.listdir(self.tree_path):
                if source in ('.', '..'):
                    continue
                else:
                    break
            self.source_dir_relative = os.path.join(self.tree_path_relative,
                                                    source)
        return retcode

    def installBuildDeps(self):
        return self.chroot(['sh', '-c', 'cd %s &&'
                     '/usr/lib/pbuilder/pbuilder-satisfydepends'
                     % self.source_dir_relative])

    def chroot(self, args, cwd=None, env=None):
        return call(['/usr/bin/sudo',
                     '/usr/sbin/chroot', self.chroot_path] + args, cwd=cwd,
                     env=env)

    def buildSourcePackage(self):
        return self.chroot(['su', '-c', 'cd %s && /usr/bin/dpkg-buildpackage -i'
                            ' -I -us -uc -S' % self.source_dir_relative,
                      self.username])

def get_build_path(build_id, *extra):
    return os.path.join(
        os.environ["HOME"], "build-" + build_id, *extra)

if __name__ == '__main__':
    builder = RecipeBuilder(*sys.argv[1:])
    if builder.install() != 0:
        sys.exit()
    if builder.buildTree() != 0:
        sys.exit(RETCODE_FAILURE_BUILD_TREE)
    if builder.installBuildDeps() != 0:
        sys.exit(RETCODE_FAILURE_INSTALL_BUILD_DEPS)
    if builder.buildSourcePackage() != 0:
        sys.exit(RETCODE_FAILURE_BUILD_SOURCE_PACKAGE)
    sys.exit(RETCODE_SUCCESS)
