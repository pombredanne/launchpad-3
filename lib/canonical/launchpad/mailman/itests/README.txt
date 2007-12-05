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

  You may also need to either change xmlrpc_url or ensure that you have a
  mapping for xmlrpc-private.launchpad.dev in your /etc/hosts file.

  We'll make this better when the new config stuff lands.
  
- Add the following text to the file override-includes/+mail-configure.zcml

-----snip snip-----
<configure
    xmlns="http://namespaces.zope.org/zope"
    xmlns:mail="http://namespaces.zope.org/mail"
    i18n_domain="zope">

    <mail:smtpMailer
        name="itests"
        hostname="localhost"
        port="9025"
        />
    <mail:directDelivery
        permission="zope.SendMail"
        mailer="itests" />

</configure>
-----snip snip-----

  Just be careful to move this file aside when you want to do normal Launchpad
  development.  This basically tells Launchpad to email the integration test
  smtp server instead of the normal localhost:25 server.

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
