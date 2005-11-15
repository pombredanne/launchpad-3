
set client_min_messages=ERROR;

/* Add a "Sprint" table, to which we can assign specs for discussion and
 * implementation. */

CREATE TABLE Sprint (
  id                serial PRIMARY KEY,
  owner             integer NOT NULL CONSTRAINT sprint_owner_fk
                                     REFERENCES Person(id),
  name              text NOT NULL CONSTRAINT sprint_name_uniq UNIQUE,
  title             text NOT NULL,
  summary           text NOT NULL,
  home_page         text,
  address           text,
  time_zone         text NOT NULL,
  time_starts       timestamp WITHOUT TIME ZONE NOT NULL,
  time_ends         timestamp WITHOUT TIME ZONE NOT NULL,
  datecreated       timestamp WITHOUT TIME ZONE NOT NULL
                    DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

ALTER TABLE Sprint ADD CONSTRAINT sprint_starts_before_ends
    CHECK (time_starts < time_ends);

CREATE INDEX sprint_datecreated_idx ON Sprint(datecreated);


/* Table to make sure we know who is attending */

CREATE TABLE SprintAttendance (
  id                serial PRIMARY KEY,
  attendee          integer NOT NULL CONSTRAINT sprintattendance_attendee_fk
                                     REFERENCES Person(id),
  sprint            integer NOT NULL CONSTRAINT sprintattendance_sprint_fk
                                     REFERENCES Sprint(id),
  time_starts       timestamp WITHOUT TIME ZONE NOT NULL,
  time_ends         timestamp WITHOUT TIME ZONE NOT NULL
);

ALTER TABLE SprintAttendance ADD CONSTRAINT sprintattendance_attendance_uniq
    UNIQUE (attendee, sprint);

ALTER TABLE SprintAttendance ADD CONSTRAINT
    sprintattendance_starts_before_ends CHECK (time_starts < time_ends);

CREATE INDEX sprintattendance_sprint_idx ON SprintAttendance(sprint);

/* Table to make sure we know what will be discussed */

CREATE TABLE SprintSpecification (
  id                serial PRIMARY KEY,
  sprint            integer NOT NULL CONSTRAINT sprintspec_sprint_fk
                                     REFERENCES Sprint(id),
  specification     integer NOT NULL CONSTRAINT sprintspec_spec_fk
                                     REFERENCES Specification(id)
);

ALTER TABLE SprintSpecification ADD CONSTRAINT sprintspec_uniq
    UNIQUE (specification, sprint);

CREATE INDEX sprintspec_sprint_idx ON SprintSpecification(sprint);

INSERT INTO LaunchpadDatabaseRevision VALUES (25,27,0);

