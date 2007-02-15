-- populate the last_scanned_id fora branch to the last
-- sequence item in the branchrevision table.
update branch
set last_scanned_id = revision_id
from (
    select rn1.branch, r.revision_id
    from revision r, branchrevision rn1
    join (
        select branch, max(sequence) as seq
        from branchrevision
        group by branch) 
    as rn2 on
        rn1.branch = rn2.branch 
        and rn1.sequence = rn2.seq
    where
	r.id = rn1.revision) as rev
where rev.branch = branch.id

-- populate branchrevision with the stored 
-- ancestry...