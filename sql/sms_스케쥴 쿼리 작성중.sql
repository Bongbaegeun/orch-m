-- 최근 장애 로그 가져오기 

    SELECT svr.orgnamescode, ii.serverseq, svr.servername, tc.targetname, tc.targetversion, gc.groupname,
	    ii.monitoritem, ii.monitorobject, ii.unit, ii.visiblename, ii.value_type, 
	    COALESCE((select c.customername from tb_customer c where c.customerseq = svr.customerseq), svr.servername) customername
    FROM tb_moniteminstance ii, tb_server svr, tb_montargetcatalog tc, tb_mongroupcatalog gc
    WHERE ii.moniteminstanceseq=4564 AND svr.serverseq=ii.serverseq
        AND tc.montargetcatseq=ii.montargetcatseq AND gc.mongroupcatseq=ii.mongroupcatseq


-- 구버젼 장애등급
select grade, 'status' as value_type from tb_smssendgrade where status_send_yn = 'y'
union all
select grade, 'perf' as value_type from tb_smssendgrade where perf_send_yn = 'y'


UPDATE tb_smsschedule set allow_stm = '16:00:00'
where serverseq = 362

SELECT *
  FROM tb_smsschedule;






SELECT 'ONEBOX'
  , CASE EXTRACT ( 'dow' from current_timestamp ) 
	WHEN '1' THEN monday 
	WHEN '2' THEN tuesday
	WHEN '3' THEN wednesday
	WHEN '4' THEN thursday
	WHEN '5' THEN friday
	WHEN '6' THEN saturday
	WHEN '7' THEN sunday END AS Condition 
	, critical_status_yn 
FROM tb_smsschedule
WHERE serverseq = 362
-- AND group_seq = 25
-- 허용시간 범위가 종료가 작을경우 하루를 더해준다. 
AND  ( ( allow_stm > allow_etm AND CURRENT_TIME > allow_stm AND CURRENT_TIMESTAMP < CURRENT_DATE + allow_etm + INTERVAL '1 day' )
	OR
 	( allow_stm < allow_etm AND CURRENT_TIME > allow_stm AND CURRENT_TIME < allow_etm )
	)

	
-- SMS 수신 불가 기간 
AND deny_yn = 'N' AND NOT ( CURRENT_DATE >= deny_sdt AND CURRENT_DATE <= deny_edt )

UNION ALL

SELECT 'GROUP'
  , CASE EXTRACT ( 'dow' from current_timestamp ) 
	WHEN '1' THEN monday 
	WHEN '2' THEN tuesday
	WHEN '3' THEN wednesday
	WHEN '4' THEN thursday
	WHEN '5' THEN friday
	WHEN '6' THEN saturday
	WHEN '7' THEN sunday END AS Condition 
	, critical_status_yn	
FROM tb_smsschedule
WHERE serverseq = 0
AND group_seq = 25
-- 허용시간 범위가 종료가 작을경우 하루를 더해준다. 
AND  ( ( allow_stm > allow_etm AND CURRENT_TIME > allow_stm AND CURRENT_TIMESTAMP < CURRENT_DATE + allow_etm + INTERVAL '1 day' )
	OR
 	( allow_stm < allow_etm AND CURRENT_TIME > allow_stm AND CURRENT_TIME < allow_etm )
	)
-- SMS 수신 불가 기간 
AND NOT ( CURRENT_DATE >= deny_sdt AND CURRENT_DATE <= deny_edt )

UNION ALL

SELECT 'ALL'
  , CASE EXTRACT ( 'dow' from current_timestamp ) 
	WHEN '1' THEN monday 
	WHEN '2' THEN tuesday
	WHEN '3' THEN wednesday
	WHEN '4' THEN thursday
	WHEN '5' THEN friday
	WHEN '6' THEN saturday
	WHEN '7' THEN sunday END AS Condition 
	, critical_status_yn	
FROM tb_smsschedule
WHERE serverseq = 9999
AND group_seq = 9999
-- 허용시간 범위가 종료가 작을경우 하루를 더해준다. 
AND  ( ( allow_stm > allow_etm AND CURRENT_TIME > allow_stm AND CURRENT_TIMESTAMP < CURRENT_DATE + allow_etm + INTERVAL '1 day' )
	OR
 	( allow_stm < allow_etm AND CURRENT_TIME > allow_stm AND CURRENT_TIME < allow_etm )
	)
-- SMS 수신 불가 기간 
AND NOT ( CURRENT_DATE >= deny_sdt AND CURRENT_DATE <= deny_edt )







