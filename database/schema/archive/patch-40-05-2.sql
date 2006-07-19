SET client_min_messages=ERROR;

/* Create a load of indexes on foreign key references to the LibraryFileAlias
table to speed up Librarian garbage collection.
*/

create index person_emblem_idx on person(emblem);
create index person_hackergotchi_idx on person(hackergotchi);
create index pofile_rawfile_idx on pofile(rawfile);
create index pofile_exportfile_idx on pofile(exportfile);
create index bugattachment_libraryfile_idx on bugattachment(libraryfile);
create index build_buildlog_idx on build(buildlog);
create index message_raw_idx on message(raw);
create index messagechunk_blob_idx on messagechunk(blob);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 5, 2);

