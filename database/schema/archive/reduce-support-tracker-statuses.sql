/* NEW (old), OPEN (old), ANSWERED (old) -> OPEN (new) */
UPDATE ticket SET status=10,answerer=NULL,dateanswered=NULL WHERE status IN (20, 30);
/* CLOSED (old) -> ANSWERED (new) */
UPDATE ticket SET status=20 WHERE status=40;
/* REJECTED (old) -> REJECTED (new) */
UPDATE ticket SET status=30 WHERE status=50;
