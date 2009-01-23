SET client_min_messages=ERROR;

CREATE TABLE WebServiceBan (
    id serial PRIMARY KEY,
    date_created TIMESTAMP WITHOUT TIME ZONE 
                    DEFAULT timezone('UTC'::text, now()),
    person INTEGER REFERENCES Person(id),
    consumer INTEGER REFERENCES OAuthConsumer(id),
    token INTEGER REFERENCES OAuthAccessToken(id),
    ip    inet,
    active BOOL DEFAULT True);

ALTER TABLE WebServiceBan
  ADD CONSTRAINT person_or_consumer_or_token_or_none CHECK (
    null_count(ARRAY[person, consumer, token]) >= 2);

ALTER TABLE WebServiceBan
  ADD CONSTRAINT at_least_one_spec CHECK (
    ip IS NOT NULL OR null_count(ARRAY[person, consumer, token]) < 3);

-- The query to optimize is something like this:
-- SELECT active FROM  WebServiceBan 
-- WHERE CASE 
--          WHEN ip IS NULL 
--              THEN (person = X OR token = X or consumer = X)
--          WHEN ip IS NOT NULL AND 
--              person IS NULL AND token IS NULL AND consumer is NULL
--              THEN (X <<= ip)
--          ELSE
--              X <<= ip AND (person = X OR token = X OR consumer = X)
--       END

CREATE UNIQUE INDEX webserviceban__ip__key
    ON WebServiceBan (ip) 
    WHERE (person IS NULL AND consumer IS NULL AND 
           token IS NULL AND ip IS NOT NULL);

CREATE UNIQUE INDEX webserviceban__person__key
    ON WebServiceBan (person) 
    WHERE (person IS NOT NULL AND ip IS NULL);
    
CREATE UNIQUE INDEX webserviceban__person__ip__key
    ON WebServiceBan (person, ip) 
    WHERE (person IS NOT NULL AND ip IS NOT NULL);

CREATE UNIQUE INDEX webserviceban__consumer__key
    ON WebServiceBan (consumer) 
    WHERE (consumer IS NOT NULL AND ip IS NULL);
    
CREATE UNIQUE INDEX webserviceban__consumer__ip__key
    ON WebServiceBan (consumer, ip) 
    WHERE (consumer IS NOT NULL AND ip IS NOT NULL);

CREATE UNIQUE INDEX webserviceban__token__key
    ON WebServiceBan (token) 
    WHERE (token IS NOT NULL AND ip IS NULL);
    
CREATE UNIQUE INDEX webserviceban__token__ip__key
    ON WebServiceBan (token, ip) 
    WHERE (token IS NOT NULL AND ip IS NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 63, 0);

