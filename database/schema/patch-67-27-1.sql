SET client_min_messages=ERROR;

create unique index translationimportqueueentry__status__dateimported__id__idx
on translationimportqueueentry(status,dateimported,id);

create index translationimportqueueentry__content__idx
on translationimportqueueentry(content) where content is not null;

create index buildqueue__build__idx on buildqueue(build);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 27, 1);

