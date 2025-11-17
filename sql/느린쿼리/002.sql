SELECT q.faultgradecode,
			        q.servername,
			        q.serveruuid ,
			        q.targetname,
			        q.targetcode,
			        q.item,
			        q.itemcode,
			        q.monitortype,
			        q.obj,
			        q.orgnamescode,
			        q.customername,
			        q.faultstagecode,
			        q.faultsummary,
			        q.resolve_dttm,
			        q.curalarmseq,
			        q.mainguidecode,
			        q.subguidecode,
			        q.resolvedetail,
			        q.sorting_event,
			        q.sorting_grade,
			        q.sorting_date,
			        q.ob_service_number ,
			        q.service_number
			   FROM   
			   		(
		              SELECT a.faultgradecode faultgradecode ,
		                     a.servername     servername ,
		                     a.serveruuid     serveruuid ,
		                     a.targetname     targetname ,
		                     a.targetcode     targetcode ,
		                     a.item           item ,
		                     a.itemcode       itemcode ,
		                     CASE
		                            WHEN a.detail_object IS NULL THEN a.monitortype
		                            WHEN a.detail_object IS NOT NULL THEN a.monitortype
		                                          ||',['||a.detail_object||']'
		                      END              monitortype ,
		                     a.obj            obj ,
		                     a.orgnamescode   orgnamescode ,
		                     a.customername   customername ,
		                     a.faultstagecode faultstagecode ,
		                     a.faultsummary   faultsummary ,
		                     a.mon_dttm       resolve_dttm ,
		                     a.curalarmseq    curalarmseq ,
		                     a.mainguidecode  mainguidecode ,
		                     a.subguidecode   subguidecode ,
		                     a.resolve_detail resolvedetail ,
		                     a.sorting_event ,
		                     a.sorting_grade ,
		                     a.sorting_date ,
		                     a.ob_service_number ,
		                     a.service_number
	              		FROM(
	                          SELECT tc.sorting_grade 
	                          		,tc.sorting_event 
	                          		,tc.sorting_date 
	                          		,tc.main_count 
	                          		,tc.faultgradecode 
	                          		,tc.orgnamescode 
	                          		,tc.montargetcatseq 
	                          		,tc.monitorvalue 
	                          		,tc.curalarmseq 
	                          		,tc.perceive_detail 
	                          		,tc.perceive_user 
	                          		,tc.perceive_dttm 
	                          		,tc.resolve_detail 
	                          		,tc.resolve_user 
	                          		,tc.resolve_dttm 
	                          		,tc.mainguidecode 
	                          		,tc.subguidecode 
	                          		,tc.per_check 
	                          		,tc.res_check 
	                          		,tc.faultstagecode 
	                          		,tc.faultsummary 
	                          		,tc.mon_dttm 
	                          		,tc.serveruuid 
	                          		,tc.customerseq
	                                 ,tser.servername servername -- 서버명
	                                 ,tmt.visiblename targetname -- 감시대상
	                                 ,tmt.targetcode -- 감시대상코드
	                                 ,tmg.visiblename item -- 감시그룹
	                                 ,tmg.mongroupcatseq itemcode -- 감시그룹코드
	                                 ,Concat (tmi.visiblename, '['||tmi.monitorobject||']') monitortype --감시item
	                                 ,CASE
	                                        WHEN tmi.monitorobject IS NULL THEN tmg.groupname
	                                        WHEN tmi.monitorobject IS NOT NULL THEN tmi.monitorobject
	                                   END obj -- 상세측정대상
	                                 ,tc.customername customername -- 고객
	                                 ,trg.orgname orgname
	                                 ,tmg.mongroupcatseq mongroupcatseq --ITEM SEQ
	                                 ,(
	                                        SELECT Max(tmc.visiblename)
	                                        FROM   tb_monviewinstance tmv,
	                                               tb_monviewcatalog tmc
	                                        WHERE  tmv.viewseq = tmc.viewseq
	                                        AND    tmv.serverseq = tser.serverseq
	                                        AND    tmv.monitorobject = tmi.monitorobject
	                                        AND    tmc.targetcode = tmt.targetcode
	                                        AND    tmc.groupname = tmg.groupname ) AS detail_object ,
				                                   tser.ob_service_number ,
				                                   tmi.service_number
	                                        FROM(
	                                              SELECT *
	                                                FROM
	                                                   (
	                                                     SELECT
	                                                              CASE
	                                                                       WHEN tc1.faultstagecode = '해제' THEN '5'
	                                                                       WHEN tc1.faultstagecode = '조치' THEN '5'
	                                                                       WHEN tc1.faultstagecode = '인지' THEN '5'
	                                                                       WHEN tc1.faultgradecode = 'CRITICAL' THEN '4'
	                                                                       WHEN tc1.faultgradecode = 'MAJOR' THEN '3'
	                                                                       WHEN tc1.faultgradecode = 'MINOR' THEN '2'
	                                                                       WHEN tc1.faultgradecode = 'WARNING' THEN '1'
	                                                                       ELSE '0'
	                                                              END sorting_grade -- 기초코드 관리가 되지 않아 기본 등급별 우선순위 컬럼임
	                                                              ,CASE WHEN tc1.faultstagecode = '발생' THEN '2' ELSE '1'
	                                                              END sorting_event 
	                                                              ,To_char(tc1.mon_dttm, 'yyyymmddhh24miss')sorting_date 
	                                                              ,Count(tc1.faultgradecode) OVER(partition BY tc1.faultgradecode )AS main_count 
	                                                              ,tc1.faultgradecode faultgradecode -- 장애등급
	                                                              ,tc1.orgnamescode orgnamescode -- 지역본부
	                                                              ,tc1.mongroupcatseq 
	                                                              ,tc1.montargetcatseq montargetcatseq 
	                                                              ,tc1.monitorvalue    monitorvalue -- 측정값
	                                                              ,tc1.curalarmseq     curalarmseq 
	                                                              ,tc1.perceive_detail perceive_detail -- 인지내용
	                                                              ,tc1.perceive_user perceive_user -- 인지자
	                                                              ,tc1.perceive_dttm perceive_dttm -- 인지일시
	                                                              ,tc1.resolve_detail resolve_detail -- 조치내용
	                                                              ,tc1.resolve_user resolve_user -- 조치자
	                                                              ,tc1.resolve_dttm resolve_dttm -- 조치일시
	                                                              ,tc1.mainguidecode mainguidecode 
	                                                              ,tc1.subguidecode  subguidecode 
	                                                              ,CASE
	                                                                       WHEN tc1.perceive_dttm IS NOT NULL THEN 'Y'
	                                                                       WHEN tc1.perceive_dttm IS NULL THEN 'N'
	                                                                END per_check -- 인지유무 flag
	                                                              ,CASE
	                                                                       WHEN tc1.resolve_dttm IS NOT NULL THEN 'Y'
	                                                                       WHEN tc1.resolve_dttm IS NULL THEN 'N'
	                                                              END res_check -- 조치유무 flag
	                                                              ,tc1.faultstagecode faultstagecode -- 단계
	                                                              ,tc1.faultsummary faultsummary -- 장애요약
	                                                              ,To_char(tc1.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') mon_dttm -- 발생시간
	                                                              /* 추가 참고 정보 컬럼*/
	                                                              ,tc1.serveruuid serveruuid --서버코드
	                                                              ,tc1.customerseq customerseq
	                                                              ,(
	                                                                     SELECT tcu.customername
	                                                                     FROM   tb_customer tcu
	                                                                     WHERE  tcu.customerseq = tc1.customerseq 
	                                                               )customername 
	                                                              ,tc1.moniteminstanceseq
	                                                              ,(select servername from tb_server tser where tc1.serveruuid = tser.serveruuid)servername
	                                                              
	                                                     FROM     tb_histalarm tc1
	                                                      
	                                                     ORDER BY 
	                                           			 
																  sorting_date DESC,
	                                                              sorting_event DESC,
	                                                              sorting_grade DESC
															 
	                                                      
	                                                              ) ttt 
	                                                   ) tc
	                                     LEFT OUTER JOIN
	                                                     (
	                                                       SELECT DISTINCT orgnamescode,
	                                                                       orgname --, officecode
	                                                       FROM            tb_org_new 
	                                                     ) trg
	                                     ON (tc.orgnamescode = trg.orgnamescode)
	                                                     
	                                     LEFT OUTER JOIN tb_server tser
	                                     ON (tc.serveruuid = tser.serveruuid)
	                                     LEFT OUTER JOIN tb_montargetcatalog tmt ON (tc.montargetcatseq = tmt.montargetcatseq)
	                                     LEFT OUTER JOIN tb_mongroupcatalog tmg ON (tc.mongroupcatseq = tmg.mongroupcatseq)
	                                     LEFT OUTER JOIN tb_moniteminstance tmi ON (tc.moniteminstanceseq = tmi.moniteminstanceseq))a
	                                     ) q
	                                     offset cast(50 as Int) * (cast(1 as Int) -1) limit cast(50 as Int)