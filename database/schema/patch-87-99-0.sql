/*
 * Adds a index to speed up queries on LibraryFileAlias by filename
 */

SET client_min_messages=ERROR;

CREATE INDEX libraryfilealias_filename_idx on libraryfilealias using btree (filename);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);
