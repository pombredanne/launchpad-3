/*
 * This adds 'unreviewed_count' column to RosettaStats implementations
 * POFile and DistroReleaseLanguage tables.
 *
 * Used to quickly find PO files with messages requiring review, so
 * translations do not get lost.
 */

SET client_min_messages=ERROR;

-- Add count of pomsgset's with unreviewed suggestions.
ALTER TABLE POFile
    ADD COLUMN unreviewed_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE DistroReleaseLanguage
    ADD COLUMN unreviewed_count INTEGER NOT NULL DEFAULT 0;

-- Allow quick selection of POFiles with unreviewed suggestions.
CREATE UNIQUE INDEX pofile__unreviewed_count__id__key ON POFile
    USING btree(unreviewed_count, id);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 17, 0);
