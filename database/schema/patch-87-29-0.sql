/*
 * This adds 'unreviewedcount' column to RosettaStats implementations
 * POFile and DistroReleaseLanguage tables.
 *
 * Used to quickly find PO files with messages requiring review, so
 * translations do not get lost.
 */

SET client_min_messages=ERROR;

-- Add count of pomsgset's with unreviewed suggestions.
ALTER TABLE POFile
    ADD COLUMN unreviewedcount INTEGER NOT NULL DEFAULT 0;
ALTER TABLE DistroReleaseLanguage
    ADD COLUMN unreviewedcount INTEGER NOT NULL DEFAULT 0;

-- Allow quick selection of POFiles with unreviewed suggestions.
CREATE INDEX pofile_unreviewedcount__idx ON POFile
    USING btree(id, unreviewedcount);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 29, 0);

