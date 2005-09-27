set client_min_messages=ERROR;

ALTER TABLE DistroReleaseLanguage
    ADD constraint distroreleaselanguage_distrorelease_language_uniq
    UNIQUE(distrorelease,language);

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 32, 0);

