
-- update pg_ts_cfg set locale='en_AU.UTF-8' where ts_name = 'default';

INSERT INTO Calendar (owner, title, revision)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            'Sample Person\'s Calendar', 0);
INSERT INTO Calendar (owner, title, revision)
    VALUES ((SELECT id from Person WHERE displayname = 'Foo Bar'),
            'Foo Bar\'s Calendar', 0);

UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
                  timezone_name = 'Australia/Perth'
    WHERE id = (SELECT id from Person WHERE displayname = 'Sample Person');
UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
                  timezone_name = 'Africa/Johannesburg'
    WHERE id = (SELECT id from Person WHERE displayname = 'Foo Bar');

INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '#9db8d2');
INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
            '#9dd2b8');

INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Foo Bar'),
            (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
            '#9dd2b8');
INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Foo Bar'),
            (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '#9db8d2');

INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-1', (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '2005-01-03 08:00:00', '01:00:00', 'Event 1', 'Desc 1', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-2', (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '2005-01-03 10:00:00', '01:00:00', 'Event 2', 'Desc 2', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-3', (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '2005-01-04 08:00:00', '01:00:00', 'Event 1', 'Desc 1', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-4', (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
            '2005-01-04 08:00:00', '01:00:00', 'Foo Bar 1', 'Desc 1', 'Location', '');
