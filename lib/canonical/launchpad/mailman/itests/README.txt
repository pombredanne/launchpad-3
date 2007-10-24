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

  We'll make this better when the new config stuff lands.
  
- make schema
- make mailman_instance
- make run_all

At this point you will have a running launchpad.dev and Mailman's qrunners
should be running as well.  Look at your stdout to see for sure.

From the top of your Launchpad tree run this:

% lib/canonical/launchpad/mailman/itests/runtests.py

You should see all the numbered integration tests run in order, with no
failures.

XXX You might also want a +mail-configure.zcml in your override-includes.
