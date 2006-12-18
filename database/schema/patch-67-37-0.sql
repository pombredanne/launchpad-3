SET client_min_messages=ERROR;

-- ProductSeries.datesyncpublished is used to  determine how old is the data
-- in a vcs-import Branch when its Branch.last_mirrored is older than
-- ProductSeries.datelastsynced.

-- We use the wordscrashedtoghether naming convention for consistency with the
-- rest of the ProductSeries table.

ALTER TABLE ProductSeries ADD COLUMN date_published_sync
    TIMESTAMP WITHOUT TIME ZONE;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 37, 0);
