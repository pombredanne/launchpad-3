CREATE TABLE ComponentSelection (
  id            serial PRIMARY KEY,
  distrorelease integer NOT NULL REFERENCES DistroRelease,
  component     integer NOT NULL REFERENCES Component
);

CREATE TABLE SectionSelection (
  id            serial PRIMARY KEY,
  distrorelease integer NOT NULL REFERENCES DistroRelease,
  section       integer NOT NULL REFERENCES Section
);
