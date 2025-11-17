SELECT t.active_yn,
       t.location_info,
       t.servername,
       t.serverseq,
       t.targetname,
       t.groupname --  , t.detail_monitor
,
       CASE
           WHEN t.detail_object IS NULL THEN t.detail_monitor
           WHEN t.detail_object IS NOT NULL THEN t.detail_monitor||',['||t.detail_object||']'
       END detail_monitor,
       (CASE
            WHEN t.value_type = 'status'
                 AND t.monitorvalue2 > 0 THEN 'UP'
            WHEN t.value_type = 'status'
                 AND t.monitorvalue2 <= 0 THEN 'DOWN'
                 
            WHEN t.groupname = 'HA Status'
                 AND t.monitorvalue2 = 2 THEN 'Active'
            WHEN t.groupname = 'HA Status'
                 AND t.monitorvalue2 = 1 THEN 'Standby'
            WHEN t.groupname = 'HA Status'
                 AND t.monitorvalue2 = 0 THEN 'Inactive'

            ELSE t.monitorvalue
            
        END || ' '|| CASE
                         WHEN t.unit = 'Mb' THEN 'Mbps'
                         ELSE t.unit
                     END) monitorvalue,
                     
       t.monitorvalue2 ,
       t.unit ,
       t.value_type ,
       t.orgnamescode,
       t.serveruuid,
       t.itemseq,
       t.stime,
       t.etime,
       t.ob_service_number,
       t.customername,
       t.service_number,
       t.monitoryn,
       t.monitoredyn
FROM
  (SELECT t.active_yn ,
          t.location_info ,
          t.servername ,
          t.serverseq ,
          t.targetname ,
          t.groupname ,
          t.detail_monitor,
          (CASE
               WHEN position('.' IN t.monitorvaluecheck) > 0 THEN to_char(t.monitorvalue, 'FM999,999,999,990.00')
               WHEN position('.' IN t.monitorvaluecheck) <= 0 THEN to_char(t.monitorvalue, 'FM999,999,999,999')
               ELSE to_char(t.monitorvalue, 'FM999,999,999,999')
           END) AS monitorvalue ,
          cast(t.monitorvalue AS numeric) monitorvalue2 ,
          t.unit ,
          t.value_type ,
          t.orgnamescode ,
          t.serveruuid ,
          t.itemseq ,
          t.stime ,
          t.etime ,
          t.detail_object ,
          t.ob_service_number ,
          t.customername ,
          t.service_number ,
          t.monitoryn ,
          t.monitoredyn
   FROM
     (SELECT COALESCE(trt.monitoredyn, 'n') active_yn ,
             CONCAT (tsr.orgnamescode,
                     '/'||tsr.servername) location_info ,
                    tsr.servername servername ,
                    tsr.serverseq serverseq ,
                    tmtg.visiblename targetname --감시대상
 ,
                    tmgc.visiblename groupname --감시그룹
 ,
                    CONCAT (tmi.visiblename,
                            '['||tmi.monitorobject||']') detail_monitor --감시item
 ,
                           trt.monitorvalue AS monitorvaluecheck ,
                           CASE
                               WHEN tmi.monitortype = 'Rx Rate'
                                    OR tmi.monitortype = 'Tx Rate' THEN (cast(trt.monitorvalue AS numeric)/ (1024*1024))
                               ELSE cast(trt.monitorvalue AS numeric)
                           END monitorvalue ,
                           coalesce(CASE
                                        WHEN tmi.monitortype = 'Rx Rate'
                                             OR tmi.monitortype = 'Tx Rate' THEN 'Mbps'
                                        ELSE tmi.unit
                                    END, '') unit ,
                           tsr.orgnamescode orgnamescode --국사명(hidden)
 ,
                           tmi.value_type /* 성능그래프 사용 변수*/ ,
                           tsr.serveruuid serveruuid --성능그래프 svr-uuid
 ,
                           tmi.moniteminstanceseq itemseq --성능그래프 itemseq
 ,
                           to_char(NOW(), 'yyyy-mm-dd hh24:mi:ss') stime --성능그래프 stime
 ,
                           to_char(now(), 'yyyy-mm-dd hh24:mi:ss') etime --성능그래프 etime
 /* 주석처리
			       , (select max(tmc.visiblename)
					    from tb_monviewinstance tmv
						   , tb_monviewcatalog tmc
						where tmv.viewseq = tmc.viewseq
						  and tmv.serverseq = tsr.serverseq
						  and tmc.defaultobject =  tmv.monitorobject
					 ) as detail_object2
					*/ ,

        (SELECT max(tmc.visiblename)
         FROM tb_monviewinstance tmv ,
              tb_monviewcatalog tmc
         WHERE tmv.viewseq = tmc.viewseq
           AND tmv.serverseq = tsr.serverseq
           AND tmv.monitorobject = tmi.monitorobject
           AND tmc.targetcode = tmtg.targetcode
           AND tmc.groupname = tmgc.groupname ) AS detail_object ,
                           tsr.ob_service_number ,
                           tcu.customername ,
                           tmi.service_number ,
                           tmi.monitoryn --감시 on/off
 ,
                           CASE
                               WHEN trt.monitoredyn IS NULL THEN 'n' -- 실시간 감시데이터 여부

                               ELSE trt.monitoredyn
                           END AS monitoredyn
      FROM tb_server tsr
      LEFT OUTER JOIN tb_moniteminstance tmi on(tsr.serverseq = tmi.serverseq)
      LEFT OUTER JOIN tb_mongroupcatalog tmgc on(tmi.mongroupcatseq = tmgc.mongroupcatseq)
      LEFT OUTER JOIN tb_realtimeperf trt on(tsr.serverseq = trt.serverseq
                                             AND tmi.moniteminstanceseq = trt.moniteminstanceseq)
      LEFT OUTER JOIN tb_montargetcatalog tmtg on(tmi.montargetcatseq = tmtg.montargetcatseq)
      LEFT OUTER JOIN tb_customer tcu on(tsr.customerseq = tcu.customerseq)
      WHERE tmi.delete_dttm IS NULL
        AND tmtg.montargetcatseq = 100 --and tmi.monitoryn = 'y'
 --and tmi.realtimeyn = 'y'

        AND tsr.serverseq = 1854
      ORDER BY tmtg.visiblename ,
               tmgc.visiblename ,
               CONCAT (tmi.visiblename,
                       '['||tmi.monitorobject||']') ASC)t) t