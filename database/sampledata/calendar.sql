
-- update pg_ts_cfg set locale='en_AU.UTF-8' where ts_name = 'default';

INSERT INTO Calendar (owner, title, revision)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            'Foo Bar', 0);

UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Foo Bar')
    WHERE id = (SELECT id from Person WHERE displayname = 'Sample Person');

INSERT INTO CalendarSubscription (person, calendar)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            (SELECT id FROM Calendar WHERE title = 'Foo Bar'));

INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, location, recurrence)
    VALUES ('sample-id-1', (SELECT id FROM Calendar WHERE title = 'Foo Bar'),
            '2005-01-01 08:00:00', '01:00:00', 'Event 1', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, location, recurrence)
    VALUES ('sample-id-2', (SELECT id FROM Calendar WHERE title = 'Foo Bar'),
            '2005-01-01 10:00:00', '01:00:00', 'Event 2', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, location, recurrence)
    VALUES ('sample-id-3', (SELECT id FROM Calendar WHERE title = 'Foo Bar'),
            '2005-01-02 08:00:00', '01:00:00', 'Event 1', 'Location', '');
