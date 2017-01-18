# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import pkg_resources


def main():
    # Run the script.
    bzr_distribution = pkg_resources.get_distribution(
        pkg_resources.Requirement.parse('bzr'))
    namespace = globals().copy()
    namespace['__name__'] = '__main__'
    bzr_distribution.run_script('bzr', namespace)
