-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE binarypackagebuild
    ADD COLUMN archive integer REFERENCES archive,
    ADD COLUMN pocket integer,
    ADD COLUMN processor integer REFERENCES processor,
    ADD COLUMN virtualized boolean,
    ADD COLUMN date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    ADD COLUMN date_started timestamp without time zone,
    ADD COLUMN date_finished timestamp without time zone,
    ADD COLUMN date_first_dispatched timestamp without time zone,
    ADD COLUMN builder integer REFERENCES builder,
    ADD COLUMN status integer,
    ADD COLUMN log integer REFERENCES libraryfilealias,
    ADD COLUMN upload_log integer REFERENCES libraryfilealias,
    ADD COLUMN dependencies text,
    ADD COLUMN failure_count integer DEFAULT 0;

ALTER TABLE sourcepackagerecipebuild
    ADD COLUMN archive integer REFERENCES archive,
    ADD COLUMN pocket integer,
    ADD COLUMN processor integer REFERENCES processor,
    ADD COLUMN virtualized boolean,
    ADD COLUMN date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    ADD COLUMN date_started timestamp without time zone,
    ADD COLUMN date_finished timestamp without time zone,
    ADD COLUMN date_first_dispatched timestamp without time zone,
    ADD COLUMN builder integer REFERENCES builder,
    ADD COLUMN status integer,
    ADD COLUMN log integer REFERENCES libraryfilealias,
    ADD COLUMN upload_log integer REFERENCES libraryfilealias,
    ADD COLUMN dependencies text,
    ADD COLUMN failure_count integer DEFAULT 0;

ALTER TABLE translationtemplatesbuild
    ADD COLUMN processor integer REFERENCES processor,
    ADD COLUMN virtualized boolean,
    ADD COLUMN date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    ADD COLUMN date_started timestamp without time zone,
    ADD COLUMN date_finished timestamp without time zone,
    ADD COLUMN date_first_dispatched timestamp without time zone,
    ADD COLUMN builder integer REFERENCES builder,
    ADD COLUMN status integer,
    ADD COLUMN log integer REFERENCES libraryfilealias,
    ADD COLUMN failure_count integer DEFAULT 0;

-- TODO: Indices

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 41, 0);
