

CREATE TABLE bounty (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    title text NOT NULL,
    summary text NOT NULL,
    description text NOT NULL,
    usdvalue decimal (10,2) NOT NULL,
    difficulty integer NOT NULL,
    duration interval NOT NULL,
    reviewer integer NOT NULL REFERENCES Person,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    owner integer NOT NULL REFERENCES Person,
    deadline timestamp,
    claimant integer REFERENCES Person,
    dateclaimed timestamp without time zone
    );



