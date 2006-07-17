set client_min_messages=error;

create unique index buildqueue__builder__id__idx on buildqueue(builder, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 49, 2);

