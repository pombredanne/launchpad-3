SET client_min_messages=ERROR;

/*
   Keep track of mentoring opportunities. People can say what bugs or specs
   they would provide mentoring on for new people wanting to join a team,
   and we present that as lists of bugs or specs which newcomers may want to
   try first.
*/

CREATE TABLE MentoringOffer (
  id                serial PRIMARY KEY,
  owner             integer NOT NULL REFERENCES Person,
  date_created      timestamp without time zone NOT NULL
                        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  team              integer NOT NULL REFERENCES Person,
  bug               integer,
  specification     integer,
  CONSTRAINT context_required CHECK
      ((bug IS NOT NULL OR specification IS NOT NULL) AND NOT
       (bug IS NOT NULL AND specification IS NOT NULL)),
  CONSTRAINT single_offer_per_bug_key UNIQUE (bug, owner),
  CONSTRAINT single_offer_per_spec_key UNIQUE (specification, owner)
  );

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 87, 0);

