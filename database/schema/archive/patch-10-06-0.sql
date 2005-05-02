SET client_min_messages=ERROR;

/* Fix this scary constraint. Lets make distroreleases have unique names */
ALTER TABLE distrorelease DROP CONSTRAINT distrorelease_distribution_key;
ALTER TABLE distrorelease ADD CONSTRAINT distrorelease_name_key UNIQUE (name);

/* Add an expires column to LibraryFileAlias, so people can start flagging
   this as soon as the Librarian API supports it
 */
ALTER TABLE LibraryFileAlias ADD COLUMN expires timestamp without time zone;

INSERT INTO LaunchpadDatabaseRevision VALUES (10, 6, 0);

