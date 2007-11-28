SET client_min_messages=ERROR;

UPDATE person 
SET defaultrenewalperiod = NULL 
WHERE defaultrenewalperiod = 0;

-- Note a team has a sticky defaultrenewalperiod across changes in
-- renewal_policy
ALTER TABLE Person
  ADD CONSTRAINT sane_defaultrenewalperiod CHECK (
    CASE
      WHEN teamowner IS NULL THEN
        defaultrenewalperiod IS NULL
      WHEN renewal_policy IN (20, 30) THEN
        defaultrenewalperiod IS NOT NULL AND defaultrenewalperiod > 0
      ELSE
        defaultrenewalperiod IS NULL OR defaultrenewalperiod > 0
    END
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 14, 0);

