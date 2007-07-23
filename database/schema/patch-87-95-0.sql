SET client_min_messages=ERROR;

CREATE TABLE OpenIdRPConfig (
  id serial PRIMARY KEY,
  trust_root text NOT NULL,
  displayname text NOT NULL,
  logo integer,
  allowed_sreg text,
  creation_rationale integer DEFAULT 13,
  CONSTRAINT openidrpconfig__logo__fk
    FOREIGN KEY (logo) REFERENCES LibraryFileAlias(id)
);

CREATE UNIQUE INDEX openidrpconfig__trust_root__key
  ON OpenIdRPConfig(trust_root);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 95, 0);
