
-- update pg_ts_cfg set locale='en_AU.UTF-8' where ts_name = 'default';


-- Create some calendars

INSERT INTO Calendar (owner, title, revision)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            'Sample Person\'s Calendar', 0);
UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
                  timezone_name = 'Australia/Perth'
    WHERE id = (SELECT id from Person WHERE displayname = 'Sample Person');

INSERT INTO Calendar (owner, title, revision)
    VALUES ((SELECT id from Person WHERE displayname = 'Foo Bar'),
            'Foo Bar\'s Calendar', 0);
UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
                  timezone_name = 'Africa/Johannesburg'
    WHERE id = (SELECT id from Person WHERE displayname = 'Foo Bar');

INSERT INTO Calendar (owner, title, revision)
    VALUES ((SELECT owner from Project WHERE name = 'ubuntu'),
            'Ubuntu Project Calendar', 0);
UPDATE Project SET calendar = (SELECT id FROM Calendar WHERE title = 'Ubuntu Project Calendar')
    WHERE id = (SELECT id from Project WHERE name = 'ubuntu');


-- Add some subscriptions for "Sample Person"

INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '#c0d0ff');
INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
            '#c0ffc8');
INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Sample Person'),
            (SELECT id FROM Calendar WHERE title = 'Ubuntu Project Calendar'),
            '#faffd2');

-- Subscriptions for "Foo Bar"
INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Foo Bar'),
            (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
            '#c0ffc8');
INSERT INTO CalendarSubscription (person, calendar, colour)
    VALUES ((SELECT id from Person WHERE displayname = 'Foo Bar'),
            (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '#c0d0ff');

-- Add events to "Sample Person's Calendar"
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-1@launchpad.example.org', (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '2005-01-03 08:00:00', '01:00:00', 'Event 1', 'Desc 1', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-2@launchpad.example.org', (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '2005-01-03 10:00:00', '01:00:00', 'Event 2', 'Desc 2', 'Location', '');
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-3@launchpad.example.org', (SELECT id FROM Calendar WHERE title = 'Sample Person\'s Calendar'),
            '2005-01-04 08:00:00', '01:00:00', 'Event 1', 'Desc 1', 'Location', '');

-- Add events to "Foo Bar's Calendar"
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-4@launchpad.example.org', (SELECT id FROM Calendar WHERE title = 'Foo Bar\'s Calendar'),
            '2005-01-04 08:00:00', '01:00:00', 'Foo Bar 1', 'Desc 1', 'Location', '');

-- Add events to "Ubuntu Project Calendar"
INSERT INTO CalendarEvent (unique_id, calendar, dtstart, duration,
                           title, description, location, recurrence)
    VALUES ('sample-id-5@launchpad.example.org', (SELECT id from Calendar WHERE title = 'Ubuntu Project Calendar'),
            '2004-12-06 08:00:00', '11 days 08:30:00', 'The Mataro Sessions', 'The Ubuntu conference in Mataro', 'Mataro, Spain', '');
