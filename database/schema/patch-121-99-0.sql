SET client_min_messages=ERROR;


-- Store the instant a build was first_dispatched. It will allow us to
-- calculate the average-build-lag-time in Soyuz as:
--
--   lag = date_first_dispatched - datecreated
--
-- See bug #235492.
ALTER TABLE build ADD COLUMN
    date_first_dispatched timestamp without time zone;


-- Store a librarian file containing the upload log messages generated
-- while processing the binaries produced by this build. Such information
-- is particularly useful for FAILEDTOUPLOAD builds.
ALTER TABLE build ADD COLUMN
    upload_log integer;

ALTER TABLE ONLY build
    ADD CONSTRAINT build__upload_log__fk
        FOREIGN KEY (upload_log) REFERENCES libraryfilealias(id);


INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
