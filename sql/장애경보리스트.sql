-- 수정후
SELECT 
CASE 	WHEN tc.faultstagecode = '해제' THEN '5'
	WHEN tc.faultstagecode = '조치' THEN '5'
	WHEN tc.faultstagecode = '인지' THEN '5'
	WHEN tc.faultgradecode = 'CRITICAL' THEN '4'
	WHEN tc.faultgradecode = 'MAJOR' THEN '3'
	WHEN tc.faultgradecode = 'MINOR' THEN '2'
	WHEN tc.faultgradecode = 'WARNING' THEN '1'
	ELSE '0'
END sorting_grade  -- 기초코드 관리가 되지 않아 기본 등급별 우선순위 컬럼임 
	   
, CASE 	WHEN tc.faultstagecode = '발생' THEN '2'
	ELSE '1'
END sorting_event

, to_char(tc.mon_dttm, 'yyyymmddhh24miss') sorting_date
, COUNT(tc.faultgradecode) OVER(PARTITION BY tc.faultgradecode ) as main_count 
, tc.faultgradecode faultgradecode  -- 장애등급         	     
, tser.servername servername   -- 서버명
-- , tmt.targetname  targetname   -- 감시대상
-- , tmg.groupname   item         -- item
-- , concat (tmi.monitoritem, '['||tmi.monitorobject||']') monitortype			      
, tmt.visiblename  targetname   -- 감시대상
, tmg.visiblename   item        -- 감시그룹
, tmg.mongroupcatseq itemCode   -- 감시그룹코드 
, CONCAT (tmi.visiblename, '['||tmi.monitorobject||']') monitortype --감시item
, CASE 	WHEN tmi.monitorobject IS NULL THEN tmg.groupname
	WHEN tmi.monitorobject IS NOT NULL THEN tmi.monitorobject
END obj   -- 상세측정대상	     
		
, tc.orgnamescode orgnamescode   -- 지역본부
, tcu.customername customername  -- 고객
, tc.faultstagecode faultstagecode -- 단계
, tc.faultsummary faultsummary    -- 장애요약
, to_char(tc.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') mon_dttm           -- 발생시간   
-- , tc.mon_dttm  mon_dttm           -- 발생시간
/* 추가 참고 정보 컬럼*/ 
, tc.serveruuid serveruuid       --서버코드	     
, tc.customerseq  customerseq    --고객코드  
, trg.orgname orgname            
, trg.officecode officecode 
, tc.montargetcatseq montargetcatseq	  
, tc.monitorvalue  monitorvalue     -- 측정값   
, tc.curalarmseq curalarmseq
, tc.perceive_detail  perceive_detail -- 인지내용
, tc.perceive_user  perceive_user  -- 인지자
, tc.perceive_dttm  perceive_dttm  -- 인지일시
, tc.resolve_detail resolve_detail -- 조치내용
, tc.resolve_user  resolve_user  -- 조치자	     
, tc.resolve_dttm  resolve_dttm  -- 조치일시
, tmg.mongroupcatseq mongroupcatseq --ITEM SEQ 	     

, CASE	WHEN tc.perceive_dttm IS NOT NULL THEN  'Y'
	WHEN tc.perceive_dttm IS NULL THEN  'N'
END per_check  -- 인지유무 flag

, CASE 	WHEN tc.resolve_dttm IS NOT NULL THEN  'Y'
	WHEN tc.resolve_dttm IS NULL THEN 'N'
END res_check  -- 조치유무 flag 
, ( SELECT max ( tmc.visiblename )
	FROM tb_curalarm tc2, tb_monviewinstance tmv, tb_monviewcatalog tmc
	WHERE tc2.moniteminstanceseq = tmv.moniteminstanceseq
	AND tmv.viewseq = tmc.viewseq
	AND tc.curalarmseq = tc2.curalarmseq
) detail_object
FROM tb_curalarm tc
LEFT OUTER JOIN tb_org_new trg ON (tc.orgnamescode = trg.orgnamescode)
LEFT OUTER JOIN tb_customer tcu ON (tc.customerseq = tcu.customerseq)
LEFT OUTER JOIN tb_server tser ON (tc.serveruuid = tser.serveruuid)
LEFT OUTER JOIN tb_montargetcatalog tmt ON (tc.montargetcatseq = tmt.montargetcatseq)
LEFT OUTER JOIN tb_mongroupcatalog tmg ON (tc.mongroupcatseq = tmg.mongroupcatseq)
LEFT OUTER JOIN tb_moniteminstance tmi ON (tc.moniteminstanceseq = tmi.moniteminstanceseq) 










-- 수정전.
SELECT 
CASE 	WHEN tc.faultstagecode = '해제' THEN '5'
	WHEN tc.faultstagecode = '조치' THEN '5'
	WHEN tc.faultstagecode = '인지' THEN '5'
	WHEN tc.faultgradecode = 'CRITICAL' THEN '4'
	WHEN tc.faultgradecode = 'MAJOR' THEN '3'
	WHEN tc.faultgradecode = 'MINOR' THEN '2'
	WHEN tc.faultgradecode = 'WARNING' THEN '1'
	ELSE '0'
END sorting_grade  -- 기초코드 관리가 되지 않아 기본 등급별 우선순위 컬럼임 
	   
, CASE 	WHEN tc.faultstagecode = '발생' THEN '2'
	ELSE '1'
END sorting_event

, to_char(tc.mon_dttm, 'yyyymmddhh24miss') sorting_date
, COUNT(tc.faultgradecode) OVER(PARTITION BY tc.faultgradecode ) as main_count 
, tc.faultgradecode faultgradecode  -- 장애등급         	     
, tser.servername servername   -- 서버명
-- , tmt.targetname  targetname   -- 감시대상
-- , tmg.groupname   item         -- item
-- , concat (tmi.monitoritem, '['||tmi.monitorobject||']') monitortype			      
, tmt.visiblename  targetname   -- 감시대상
, tmg.visiblename   item        -- 감시그룹
, tmg.mongroupcatseq itemCode   -- 감시그룹코드 
, CONCAT (tmi.visiblename, '['||tmi.monitorobject||']') monitortype --감시item
, CASE 	WHEN tmi.monitorobject IS NULL THEN tmg.groupname
	WHEN tmi.monitorobject IS NOT NULL THEN tmi.monitorobject
END obj   -- 상세측정대상	     
		
, tc.orgnamescode orgnamescode   -- 지역본부
, tcu.customername customername  -- 고객
, tc.faultstagecode faultstagecode -- 단계
, tc.faultsummary faultsummary    -- 장애요약
, to_char(tc.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') mon_dttm           -- 발생시간   
-- , tc.mon_dttm  mon_dttm           -- 발생시간
/* 추가 참고 정보 컬럼*/ 
, tc.serveruuid serveruuid       --서버코드	     
, tc.customerseq  customerseq    --고객코드  
, trg.orgname orgname            
, trg.officecode officecode 
, tc.montargetcatseq montargetcatseq	  
, tc.monitorvalue  monitorvalue     -- 측정값   
, tc.curalarmseq curalarmseq
, tc.perceive_detail  perceive_detail -- 인지내용
, tc.perceive_user  perceive_user  -- 인지자
, tc.perceive_dttm  perceive_dttm  -- 인지일시
, tc.resolve_detail resolve_detail -- 조치내용
, tc.resolve_user  resolve_user  -- 조치자	     
, tc.resolve_dttm  resolve_dttm  -- 조치일시
, tmg.mongroupcatseq mongroupcatseq --ITEM SEQ 	     

, CASE	WHEN tc.perceive_dttm IS NOT NULL THEN  'Y'
	WHEN tc.perceive_dttm IS NULL THEN  'N'
END per_check  -- 인지유무 flag

, CASE 	WHEN tc.resolve_dttm IS NOT NULL THEN  'Y'
	WHEN tc.resolve_dttm IS NULL THEN 'N'
END res_check  -- 조치유무 flag 

, ( 	SELECT max(tmc.visiblename) 
	FROM tb_monviewinstance tmv, tb_monviewcatalog tmc
	WHERE tmv.viewseq = tmc.viewseq   
	AND tmv.serverseq = tser.serverseq
	AND tmv.monitorobject = tmi.monitorobject
	AND  tmc.targetcode = tmt.targetcode
	AND  tmc.groupname = tmg.groupname
) AS detail_object     

FROM tb_curalarm tc
LEFT OUTER JOIN tb_org_new trg ON (tc.orgnamescode = trg.orgnamescode)
LEFT OUTER JOIN tb_customer tcu ON (tc.customerseq = tcu.customerseq)
LEFT OUTER JOIN tb_server tser ON (tc.serveruuid = tser.serveruuid)
LEFT OUTER JOIN tb_montargetcatalog tmt ON (tc.montargetcatseq = tmt.montargetcatseq)
LEFT OUTER JOIN tb_mongroupcatalog tmg ON (tc.mongroupcatseq = tmg.mongroupcatseq)
LEFT OUTER JOIN tb_moniteminstance tmi ON (tc.moniteminstanceseq = tmi.moniteminstanceseq) 



SELECT * FROM tb_curalarm

