    UPDATE tb_monviewinstance vi SET moniteminstanceseq=vv.moniteminstanceseq
    FROM (

        SELECT ii.serverseq, ii.moniteminstanceseq, vm.monitorobject, vm.viewseq
        FROM (SELECT vi.serverseq, vi.viewseq, viewname, targetcode, targettype, groupname, monitortype, monitorobject 
            FROM tb_monviewinstance vi, tb_monviewcatalog vc
            WHERE vi.viewseq=vc.viewseq AND vi.serverseq=1508) vm, tb_moniteminstance ii
        LEFT OUTER JOIN tb_montargetcatalog tc ON ii.montargetcatseq=tc.montargetcatseq
        LEFT OUTER JOIN tb_mongroupcatalog gc ON ii.mongroupcatseq=gc.mongroupcatseq
        WHERE ii.delete_dttm is null AND ii.serverseq=vm.serverseq
            AND vm.groupname=gc.groupname AND vm.monitortype=ii.monitortype
            AND ( (vm.targettype is not null AND vm.targettype=tc.targettype) OR (vm.targettype is null AND vm.targetcode=tc.targetcode) )

            
            AND ( (vm.monitorobject is not null AND ii.monitorobject=vm.monitorobject ) OR (vm.monitorobject is null AND ii.monitorobject is null) )
        ORDER BY serverseq, vm.viewseq




         ) vv
    WHERE vi.serverseq=vv.serverseq AND vi.viewseq=vv.viewseq 
        AND ( (vi.monitorobject is not null AND vi.monitorobject=vv.monitorobject ) OR (vi.monitorobject is null AND vv.monitorobject is null) )


select * from tb_server

select * from tb_moniteminstance
where serverseq=1508
and delete_dttm is null

select * from tb_monviewinstance
where serverseq=1508
order by viewseq

select * from tb_monitemcatalog
order by monitemcatseq

select * from tb_monviewcatalog
order by viewseq


select * from tb_montargetcatalog
order by montargetcatseq

SELECT * FROM tb_montargetcatalog WHERE montargetcatseq=86 AND delete_dttm is null

select * from tb_SERVER
ORDER BY serverseq

SELECT vendorcode, targetmodel FROM tb_montargetcatalog WHERE montargetcatseq=79