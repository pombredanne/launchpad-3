
set client_min_messages=ERROR;


CREATE TABLE Poll (
  id          serial NOT NULL PRIMARY KEY,
  team        integer NOT NULL
                CONSTRAINT poll_team_fk REFERENCES Person
                CONSTRAINT is_team CHECK (is_team(team)),
  name        text NOT NULL, -- used for url traversal
  title       text NOT NULL,
  dateopens   timestamp without time zone NOT NULL,
  datecloses  timestamp without time zone NOT NULL,
  proposition text NOT NULL,
  type        integer NOT NULL, -- enum in dbschema.PollAlgorithm
  allowspoilt boolean NOT NULL DEFAULT False,
  secrecy     integer NOT NULL, -- enum in dbschema.PollSecrecy
  CONSTRAINT poll_team_key UNIQUE (team, name),
  CONSTRAINT sane_dates CHECK (dateopens < datecloses)
);

CREATE TABLE PollOption (
  id        serial NOT NULL PRIMARY KEY,
  poll      integer NOT NULL REFERENCES Poll,
  name      text NOT NULL,
  shortname text NOT NULL,
  active    boolean NOT NULL DEFAULT True, -- See Q.A
  CONSTRAINT polloption_name_key UNIQUE (name,poll),
  CONSTRAINT polloption_shortname_key UNIQUE (shortname,poll),
  CONSTRAINT polloption_poll_key UNIQUE (poll,id) -- Used for foreign key
);

CREATE INDEX polloption_poll_idx ON PollOption(poll);

CREATE TABLE VoteCast (
  id       serial NOT NULL PRIMARY KEY,
  person   integer NOT NULL CONSTRAINT votecast_person_fk REFERENCES Person,
  poll     integer NOT NULL CONSTRAINT votecast_poll_fk REFERENCES Poll,
  CONSTRAINT votecast_person_key UNIQUE (person, poll)
);

CREATE INDEX votecast_poll_idx ON VoteCast(poll);

CREATE TABLE Vote (
  id         serial NOT NULL PRIMARY KEY,
  person     integer
                CONSTRAINT vote_person_fk REFERENCES Person
                CONSTRAINT is_person CHECK (is_person(person)),
  poll       integer NOT NULL
                -- We need this fk as well as the vote_person_poll one below
                -- because person is NULL for secret ballots.
                CONSTRAINT vote_poll_fk REFERENCES Poll,
  preference integer NOT NULL,
  option     integer, -- NULL is a spoilt ballot, none-of-the-above
  token      text NOT NULL CONSTRAINT vote_token_key UNIQUE,
  CONSTRAINT vote_poll_option_fk
                FOREIGN KEY (poll,option) REFERENCES PollOption(poll,id)
);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,1,0);
