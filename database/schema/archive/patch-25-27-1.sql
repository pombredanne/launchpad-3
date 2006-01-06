SET client_min_messages=ERROR;

CREATE UNIQUE INDEX pomsgidsighting_potmsgset_pluralform_uniq
    ON PoMsgIdSighting (potmsgset, pluralform)
    WHERE inlastrevision = true;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 27, 1);

