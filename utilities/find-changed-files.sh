#!/bin/bash
#
# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# Determine the changed files in the working tree, or if the working tree is
# clean then the changed files relative to the parent branch.

set -e
set -o pipefail

if [ -d .git ]; then
    git_diff_files() {
        git diff --name-only -z $@ | perl -l -0 -ne '
            # Only show paths that exist and are not symlinks.
            print if -e and not -l'
    }

    files=$(git_diff_files HEAD)
    if [ -z "$files" ]; then
        # git doesn't give us a way to track the parent branch, so just use
        # master by default and let the user override that using a
        # positional argument.
        files=$(git_diff_files "${1:-master}")
    fi
elif [ -d .bzr ]; then
    bzr() {
        # PYTHONPATH may point to the ./lib directory in the launchpad tree.
        # This directory includes a bzrlib. When this script calls bzr, we
        # want it to use the system bzrlib, not the one in the launchpad
        # tree.
        PYTHONPATH='' `which bzr` "$@"
    }

    diff_status=0
    bzr diff > /dev/null || diff_status=$?
    if [ $diff_status -eq 0 ] ; then
        # No uncommitted changes in the tree.
        if bzr status | grep -q "^Current thread:"; then
            # This is a loom, lint changes relative to the lower thread.
            rev_option="-r thread:"
        elif [ "$(bzr pipes | sed -n -e "/^\\*/q;p" | wc -l)" -gt 0 ]; then
            # This is a pipeline with at least one pipe before the
            # current, lint changes relative to the previous pipe
            rev_option="-r ancestor::prev"
        else
            # Lint changes relative to the parent.
            rev=`bzr info | sed \
                '/parent branch:/!d; s/ *parent branch: /ancestor:/'`
            rev_option="-r $rev"
        fi
    elif [ $diff_status -eq 1 ] ; then
        # Uncommitted changes in the tree, return those files.
        rev_option=""
    else
        # bzr diff failed
        exit 1
    fi
    # Extract filename from status line.  Skip symlinks.
    files=`bzr st --short $rev_option |
        sed -e '/^.[MN]/!d; s/.* //' -e '/@$/d'`
else
    echo "Not in a Git or Bazaar working tree" >&2
    exit 1
fi

echo $files
