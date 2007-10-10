SET client_min_messages=ERROR;
-- Removes the calendar (bug 136541).

DROP TABLE CalendarSubscription;
DROP TABLE CalendarEvent;

ALTER TABLE Person
    DROP COLUMN calendar;
ALTER TABLE Product
    DROP COLUMN calendar;
ALTER TABLE Project
    DROP COLUMN calendar;
-- Distributions don't have a calendar.

DROP TABLE Calendar;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
