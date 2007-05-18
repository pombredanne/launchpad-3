/*
 * This patch renames DistroReleaseQueue* to PackageUpload* and adds the
 * Archive table.
 */

SET client_min_messages=ERROR;

ALTER TABLE Archive ADD COLUMN description TEXT;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 1);
