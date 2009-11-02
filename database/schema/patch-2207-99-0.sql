-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE sourceformatselection (
  id serial PRIMARY KEY,
  distroseries integer NOT NULL
    CONSTRAINT sourceformatselection__distroseries__fk
    REFERENCES distroseries,
  format text NOT NULL,
  CONSTRAINT sourceformatselection__distroseries__format__key
    UNIQUE (distroseries, format)
);

INSERT INTO sourceformatselection (distroseries, format) SELECT id, '1.0' AS format FROM distroseries;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
