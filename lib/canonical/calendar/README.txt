Prototype for adding calendars to launchpad
===========================================

This code is probably in the wrong place, it doesn't have the proper copyright
notices, etc.

TODO: this package is going away:

    adapters will go to canonical.launchpad.component
    view/traverser hybrids will disappear completely
    unit tests will go whereever the units they test go
    README.txt will become canonical/launchpad/doc/calendars.txt


Hooking up the views
--------------------

Going to /calendar shows the calendar of the currently logged on user.  This
is implementing by registering canonical.calendar.UsersCalendarTraverser as a
view (called 'calendar') for the root object and registering an adapter from
IPerson (actually, any ICalendarOwner) to ICalendar.

Going to a person in /foaf and adding /calendar at the end of the URL will
show the calendar of that person.  This is implemented by registering
canonical.calendar.CalendarAdapterTraverser as a view (also called 'calendar')
for ICalendarOwner.

XXX Steve Alexander says using views in this fashion is a bad idea (without
detailing that assertion), so we have to write custom traversers for
ICalendarOwners.
