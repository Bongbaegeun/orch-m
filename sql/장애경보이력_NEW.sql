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
               case when position( 'license' in q.obj ) > 0 then q.faultsummary || '( ' || q.monitorvalue || ' 일 남음 )' 
                                  else q.faultsummary 
                             end  faultsummary,
              q.mon_dttm,
              q.resolve_dttm,
              q.duration_dttm,
              q.curalarmseq,
              q.mainguidecode,
              q.subguidecode,
              q.resolvedetail,
              q.sorting_event,
              q.sorting_grade,
              q.sorting_date,
              q.ob_service_number ,
              q.service_number,
              q.mgmtip
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
                               when a.detail_object IS NOT NULL THEN a.detail_object
                      END monitortype ,
                        a.obj            obj ,
                        a.orgnamescode   orgnamescode ,
                        a.customername   customername ,
                        a.faultstagecode faultstagecode ,
                        a.faultsummary   faultsummary ,
                        a.mon_dttm       mon_dttm ,
                        to_char(a.resolve_dttm, 'yyyy-mm-dd hh24:mi:ss')resolve_dttm,
                        a.duration_dttm,
                        a.curalarmseq    curalarmseq ,
                        a.mainguidecode  mainguidecode ,
                        a.subguidecode   subguidecode ,
                        a.resolve_detail resolvedetail ,
                        a.sorting_event ,
                        a.sorting_grade ,
                        a.sorting_date ,
                        a.ob_service_number ,
                        a.service_number,
                        a.monitorvalue,
                        a.mgmtip
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
                                ,tc.duration_dttm
                                 ,tser.servername servername 
                                 ,tmt.visiblename targetname 
                                 ,tmt.targetcode 
                                 ,tmg.visiblename item 
                                 ,tmg.mongroupcatseq itemcode 
                                 ,Concat (tmi.visiblename, '['||tmi.monitorobject||']') monitortype 
                                 ,CASE
                                        WHEN tmi.monitorobject IS NULL THEN tmg.groupname
                                        WHEN tmi.monitorobject IS NOT NULL THEN tmi.monitorobject
                                   END obj 
                                 ,tc.customername customername 
                                 ,trg.orgname orgname
                                 ,tmg.mongroupcatseq mongroupcatseq
                                 ,tser.mgmtip 
                                 ,
                                 tmi.visiblename detail_object, 
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
                                                              END sorting_grade 
                                                              ,CASE WHEN tc1.faultstagecode = '발생' THEN '2' ELSE '1'
                                                              END sorting_event 
                                                              ,To_char(tc1.mon_dttm, 'yyyymmddhh24miss')sorting_date 
                                                              ,Count(tc1.faultgradecode) OVER(partition BY tc1.faultgradecode )AS main_count 
                                                              ,tc1.faultgradecode faultgradecode
                                                              ,tc1.orgnamescode orgnamescode
                                                              ,tc1.mongroupcatseq 
                                                              ,tc1.montargetcatseq montargetcatseq 
                                                              ,tc1.monitorvalue    monitorvalue
                                                              ,tc1.curalarmseq     curalarmseq 
                                                              ,tc1.perceive_detail perceive_detail
                                                              ,tc1.perceive_user perceive_user
                                                              ,tc1.perceive_dttm perceive_dttm
                                                              ,tc1.resolve_detail resolve_detail
                                                              ,tc1.resolve_user resolve_user
                                                              ,tc1.resolve_dttm resolve_dttm
                                                              ,tc1.mainguidecode mainguidecode 
                                                              ,tc1.subguidecode  subguidecode 
                                                              ,CASE
                                                                       WHEN tc1.perceive_dttm IS NOT NULL THEN 'Y'
                                                                       WHEN tc1.perceive_dttm IS NULL THEN 'N'
                                                                END per_check
                                                              ,CASE
                                                                       WHEN tc1.resolve_dttm IS NOT NULL THEN 'Y'
                                                                       WHEN tc1.resolve_dttm IS NULL THEN 'N'
                                                              END res_check
                                                              ,tc1.faultstagecode faultstagecode
                                                              ,tc1.faultsummary faultsummary
                                                              ,To_char(tc1.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') mon_dttm
                                                              ,(tc1.resolve_dttm - tc1.mon_dttm)duration_dttm
                                                              ,tc1.serveruuid serveruuid
                                                              ,tc1.customerseq customerseq
                                                              ,(
                                                                     SELECT tcu.customername
                                                                     FROM   tb_customer tcu
                                                                     WHERE  tcu.customerseq = tc1.customerseq 
                                                               )customername 
                                                              ,tc1.moniteminstanceseq
                                                              -- ,(select servername from tb_server tser where tc1.serveruuid = tser.serveruuid)servername
                                                              , tser.servername
                                                              
                                                     FROM     tb_histalarm tc1, tb_server tser
                                                     WHERE 1 = 1
                                                     AND mon_dttm ::date between TO_DATE('2020-07-01', 'YYYY-MM-DD') and TO_DATE('2020-07-29', 'YYYY-MM-DD')
                                                     AND tc1.serveruuid = tser.serveruuid
                                                   
                                                              ) ttt 
                                                   ) tc
                                     LEFT OUTER JOIN
                                                     (
                                                       SELECT DISTINCT orgnamescode,
                                                                       orgname
                                                       FROM            tb_org_new 
                                                     ) trg
                                     ON (tc.orgnamescode = trg.orgnamescode)
                                     LEFT OUTER JOIN tb_server tser
                                     ON (tc.serveruuid = tser.serveruuid)
                                     LEFT OUTER JOIN tb_montargetcatalog tmt ON (tc.montargetcatseq = tmt.montargetcatseq)
                                     LEFT OUTER JOIN tb_mongroupcatalog tmg ON (tc.mongroupcatseq = tmg.mongroupcatseq)
                                     LEFT OUTER JOIN tb_moniteminstance tmi ON (tc.moniteminstanceseq = tmi.moniteminstanceseq))a
                                     ) q
                                     where 1 = 1
                                     order by mon_dttm desc
                                       
--                                     offset cast(10 as Int) * (cast(0 as Int) -1) limit cast(0 as Int)