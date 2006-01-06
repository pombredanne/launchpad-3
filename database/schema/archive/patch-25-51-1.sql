set client_min_messages=ERROR;

create index person_sorting_idx on
    person(displayname, familyname, givenname, name);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 51, 1);

