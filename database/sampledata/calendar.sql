
-- update pg_ts_cfg set locale='en_AU.UTF-8' where ts_name = 'default';

INSERT INTO Calendar (owner, title, revision)
    VALUES (16, 'Foo Bar', 0);

UPDATE Person SET calendar = (SELECT id FROM Calendar WHERE title = 'Foo Bar') WHERE id = 16;

INSERT INTO CalendarSubscription (person, calendar)
    VALUES (16, (SELECT id FROM Calendar WHERE title = 'Foo Bar'));
