    SELECT svr.orgnamescode, ii.serverseq, svr.servername, tc.targetname, tc.targetversion, gc.groupname,
	    ii.monitoritem, ii.monitorobject, ii.unit, ii.visiblename, ii.value_type, 
	    COALESCE((select c.customername from tb_customer c where c.customerseq = svr.customerseq), svr.servername) customername
    	,(select c.group_seq from tb_customer c where c.customerseq = svr.customerseq) group_seq
	    ,(select cg.group_name from tb_customer c, tb_customer_group cg where c.customerseq = svr.customerseq and c.group_seq = cg.seq) group_name
	    ,svr.nfsubcategory nfsubcat
	,(select nw.display_name from tb_onebox_nw nw where svr.serverseq = nw.serverseq and ii.monitorobject = nw.name ) display_name
    FROM tb_moniteminstance ii, tb_montargetcatalog tc, tb_mongroupcatalog gc, tb_server svr
    WHERE ii.moniteminstanceseq=82822
	AND svr.serverseq=ii.serverseq
        AND tc.montargetcatseq=ii.montargetcatseq 
        AND gc.mongroupcatseq=ii.mongroupcatseq

-- groupname net 이고, monitorobject 가 eth1 을 비교해서 wan 값을 가져온다



select * from tb_montargetcatalog

select * from tb_monrequest
order by req_dttm desc
limit 100


