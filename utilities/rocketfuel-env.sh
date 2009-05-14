# Copyright <YEARS> Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3; see the file LICENSE for
#
# Common environment variables for the rocketfuel-* scripts.
#
# The ones you can set are:
#
# LP_PROJECT_ROOT - The root directory of all your Canonical stuff.  Your
#                   Launchpad shared repository will live in a child directory
#                   of this directory.
# LP_SHARED_REPO  - Your Launchpad shared repository directory.  All of your
#                   Launchpad development branches will live under here.
# LP_TRUNK_NAME   - The directory name (not path!) to your rocketfuel trunk
#                   mirror directory.  This is relative to your shared repo.
# LP_SOURCEDEPS_DIR - The name of the directory (not path!) where your
#                   trunk sourcecode will be placed.  This is relative to your
#                   LP_PROJECT_ROOT and should /not/ have the 'sourcecode'
#                   path appended to it, since this is automatically added by
#                   the scripts.

LP_PROJECT_ROOT=${LP_PROJECT_ROOT:=~/canonical}
LP_SHARED_REPO=${LP_SHARED_REPO:=lp-branches}
LP_PROJECT_PATH=$LP_PROJECT_ROOT/$LP_SHARED_REPO
LP_TRUNK_NAME=${LP_TRUNK_NAME:=trunk}
LP_TRUNK_PATH=$LP_PROJECT_PATH/$LP_TRUNK_NAME

LP_SOURCEDEPS_DIR=${LP_SOURCEDEPS_DIR:=lp-sourcedeps}
LP_SOURCEDEPS_PATH=$LP_PROJECT_ROOT/$LP_SOURCEDEPS_DIR/sourcecode

# Force tilde expansion
LP_SOURCEDEPS_PATH=$(eval echo ${LP_SOURCEDEPS_PATH})
