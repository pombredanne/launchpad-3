This directory contains integration tests for proper interaction between
Launchpad and Mailman.  These are /not/ unit tests, and cannot be run inside
of either application though, so this directory is not a Python package.

Here are the steps to run these integration tests:

- Edit your launchpad.conf file, changing the following values in your
  <mailman> section:

    build yes
    var_dir /tmp/var/mailman
    smtp localhost:9025
    xmlrpc_runner_sleep 2
    launch yes

  We'll make this better when the new config stuff lands.
  
- make schema
- make mailman_instance
- make run_all

At this point you will have a running launchpad.dev and Mailman's qrunners
should be running as well.  Look at your stdout to see for sure.

From the top of your Launchpad tree run this:

% lib/canonical/launchpad/mailman/itests/runtests.py

This will run all the integration doctests in this directory.

NOTES:

- If you've done this before and possibly have old branches laying around, you
  will probably want to clean out and rebuild Mailman.  This may also be
  necessary if your var_dir is on a temporary file system and you've rebootted
  since the last time you ran the tests.  To clean everything out:

  % rm -rf /tmp/var/mailman (or whatever var_dir points to above)
  % rm -rf lib/mailman
  % make mailman_instance

  If you don't remove lib/mailman, 'make mailman_instance' will not do
  anything.
