/* 3 points for rejecting a bug task */
INSERT INTO KarmaAction (NAME, category, points) VALUES (16, 2, 3);

/* 5 points for rejecting a bug task */
INSERT INTO KarmaAction (NAME, category, points) VALUES (17, 2, 5);

/* 1 point for changing a bug task's severity */
INSERT INTO KarmaAction (NAME, category, points) VALUES (18, 2, 1);

/* 1 point for changing a bug task's priority */
INSERT INTO KarmaAction (NAME, category, points) VALUES (19, 2, 1);

/* 5 points for marking a bug as a duplicate */
INSERT INTO KarmaAction (NAME, category, points) VALUES (20, 2, 5);

/* 10 points for adding a bug watch */
INSERT INTO KarmaAction (NAME, category, points) VALUES (21, 2, 10);

/* Adding a comment shouldn't give any points at all */
UPDATE KarmaAction SET points=0 WHERE name=2;
