Prototype for adding calendars to launchpad
===========================================

This code is probably in the wrong place, it doesn't have the proper copyright
notices, etc.  There are no lp:url annotations in configure.zcml.

TODO: write some stuff



Hooking up the views
--------------------

Going to /+calendar shows the calendar of the currently logged on user.  This
is implementing by registering canonical.calendar.DefaultCalendar as a view
(called '+calendar') for the root object.
