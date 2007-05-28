SET client_min_messages=ERROR;

ALTER TABLE Person 
  ADD CONSTRAINT non_admin_renewable_memberships_require_defaultrenewalperiod
    CHECK (CASE WHEN (renewal_policy IN (20, 30))
           THEN (defaultrenewalperiod IS NOT NULL
                 AND defaultrenewalperiod > 0)
           END);

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 19, 0);

