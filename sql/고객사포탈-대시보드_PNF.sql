SELECT cnf.serverseq,
       cnf.nsseq,
       cnf.name,
       cnf.fnc,
       cnf.version,
       cnf.vdudseq,
       cnf.publicip,
       perf.state,
       perf.c4,
       perf.c5,
       perf.c6,
       case WHEN cnf.name = 'KT-UTM' OR cnf.name = 'KT-VNF' THEN 1 ELSE 2 END AS ord,
       nms.c8,
       perf.c9,
       perf.c10,
       perf.montargetcatseq,
       alarmcnt.cur,
       alarmcnt.total,
       cnf.description,
       cnf.weburl,
       cnf.nf_type, -- utm
 	   coalesce(c28, '0') AS c28,
       coalesce(c29, '0') AS c29,
       coalesce(c30, '0') AS c30,
       coalesce(vnic_sum, 0) AS vnic_sum
FROM
  (-- 구성정보
 SELECT serverseq, -- 2017.03.6 이중화작업으로 수정
 publicip,
 0 AS nsseq,
 'AXGATE-PNF'::text as name,
 '0'::text AS fnc,
 1 as version,
 0 as vdudseq,
 'AXGATEPNF'::text as description,
  web_url as weburl,
 'AXGATEPNF'::text AS nf_type
   FROM tb_server 
   WHERE serverseq = 1604 ) AS cnf -- 성능정보
LEFT OUTER JOIN
  (
  SELECT 0 as vdudseq ,
          CASE
              WHEN MAX(monitoredyn) = 'y' THEN 'RUNNING'
              ELSE 'STOP'
          END AS state ,
          MAX(montargetcatseq) AS montargetcatseq ,
          MAX(CASE
                  WHEN viewseq = 4 THEN monitorvalue
              END)::numeric::integer AS c4 ,
          MAX(CASE
                  WHEN viewseq = 5 THEN monitorvalue
              END)::numeric::integer AS c5 ,
          MAX(CASE
                  WHEN viewseq = 6 THEN monitorvalue
              END)::numeric::integer AS c6 ,
          MAX(CASE
                  WHEN viewseq = 9 THEN monitorvalue
              END)::numeric::integer AS c9 ,
          MAX(CASE
                  WHEN viewseq = 10 THEN monitorvalue
              END)::numeric::integer AS c10
   FROM
     (
     SELECT CASE
                 WHEN mgc.groupname = 'vcpu'
                      AND mii.monitortype = 'Util' THEN 4
                 WHEN mgc.groupname = 'vmem'
                      AND mii.monitortype = 'Util' THEN 5
                 WHEN mgc.groupname = 'vdisk'
                      AND mii.monitortype = 'Util' THEN 6
                 WHEN mgc.groupname = 'vnet'
                      AND mii.monitortype = 'Rx Rate' THEN 9
                 WHEN mgc.groupname = 'vnet'
                      AND mii.monitortype = 'Tx Rate' THEN 10
             END AS viewseq ,
             rtp.serverseq ,
             s.nsseq ,
             rtp.monitorvalue ,
             rtp.monitoredyn ,
             mii.montargetcatseq ,
             0 as vdudseq
      FROM tb_realtimeperf AS rtp
      LEFT OUTER JOIN tb_server AS s ON rtp.serverseq = s.serverseq
      LEFT OUTER JOIN tb_moniteminstance AS mii ON mii.moniteminstanceseq = rtp.moniteminstanceseq
      LEFT OUTER JOIN tb_montargetcatalog AS mtc ON mtc.montargetcatseq = mii.montargetcatseq
      LEFT OUTER JOIN tb_mongroupcatalog AS mgc ON mgc.mongroupcatseq = mii.mongroupcatseq
      WHERE s.serverseq = 1604 ) AS perf
   WHERE perf.viewseq IS NOT null  
   ) AS perf ON cnf.vdudseq = perf.vdudseq -- 장애 수
LEFT OUTER JOIN
  (
  SELECT 0 as nsseq,
          0 as vdudseq,
          sum(CASE
                  WHEN faultstagecode != '해제'
                       AND faultgradecode NOT IN('WARNING', 'MINOR') THEN 1
                  ELSE 0
              END) AS cur,
          sum(CASE
                  WHEN faultgradecode NOT IN('WARNING', 'MINOR') THEN 1
                  ELSE 0
              END) AS total
   FROM tb_curalarm AS ca
   LEFT OUTER JOIN tb_server AS s ON ca.onebox_id = s.onebox_id
   LEFT OUTER JOIN tb_montargetcatalog AS mtc ON ca.montargetcatseq = mtc.montargetcatseq
   WHERE s.serverseq = 1604
            ) AS alarmcnt ON cnf.nsseq = alarmcnt.nsseq
LEFT OUTER JOIN
  (
  SELECT c8,
          0 as nsseq
   FROM
     (
     SELECT mvi.serverseq,
             sum((CASE
                      WHEN mvi.viewseq = 8 THEN rtp.monitorvalue
                  END)::int)::text || '/' || count(CASE
                                                       WHEN mvi.viewseq = 8 THEN rtp.monitorvalue
                                                   END)::text c8
      FROM tb_monviewinstance AS mvi
      LEFT OUTER JOIN tb_moniteminstance AS mii ON mvi.moniteminstanceseq = mii.moniteminstanceseq
      LEFT OUTER JOIN tb_realtimeperf AS rtp ON rtp.moniteminstanceseq = mii.moniteminstanceseq
      AND rtp.monitoredyn = 'y'
      WHERE mvi.moniteminstanceseq IS NOT NULL
        AND mii.delete_dttm IS NULL
      GROUP BY mvi.serverseq 
      ) AS item
   WHERE item.serverseq =1604
   LIMIT 1
   ) AS nms ON cnf.nsseq = nms.nsseq -- 2017.04.24 utm cpu/mem/vdisk/vnic
LEFT OUTER JOIN
  ( SELECT rps.serverseq, -- utm
 rps.c28,
 rps.c29,
 rps.c30,
 rps.c54 + rps.c55 + rps.c56 + rps.c57 + rps.c58 + rps.c59 AS vnic_sum
   FROM
     (SELECT mvi.serverseq, -- UTM
 max(CASE
         WHEN mvi.viewseq = 34 THEN rtp.monitorvalue
     END) c28, -- utm cpu
 max(CASE
         WHEN mvi.viewseq = 35 THEN rtp.monitorvalue
     END) c29, -- utm mem
 max(CASE
         WHEN mvi.viewseq = 36 THEN rtp.monitorvalue
     END) c30, -- utm vdisk
 -- Network(vNIC): Wan
 sum((CASE
          WHEN mvi.viewseq = 54
               OR mvi.viewseq = 38 THEN rtp.monitorvalue
      END)::int) c54,
 sum((CASE
          WHEN mvi.viewseq = 55
               OR mvi.viewseq = 40 THEN rtp.monitorvalue
      END)::int) c55, -- Network(vNIC): Office
 sum((CASE
          WHEN mvi.viewseq = 56
               OR mvi.viewseq = 39 THEN rtp.monitorvalue
      END)::int) c56,
 sum((CASE
          WHEN mvi.viewseq = 57
               OR mvi.viewseq = 41 THEN rtp.monitorvalue
      END)::int) c57, -- Network(vNIC): Server
 sum((CASE
          WHEN mvi.viewseq = 58 THEN rtp.monitorvalue
      END)::int) c58,
 sum((CASE
          WHEN mvi.viewseq = 59 THEN rtp.monitorvalue
      END)::int) c59
      FROM tb_monviewinstance AS mvi
      LEFT OUTER JOIN tb_moniteminstance AS mii ON mvi.moniteminstanceseq = mii.moniteminstanceseq
      LEFT OUTER JOIN tb_realtimeperf AS rtp ON rtp.moniteminstanceseq = mii.moniteminstanceseq
      AND rtp.monitoredyn = 'y'
      LEFT OUTER JOIN tb_curalarm AS ca ON mii.moniteminstanceseq = ca.moniteminstanceseq
      AND ca.faultstagecode = '발생'
      WHERE mvi.moniteminstanceseq IS NOT NULL
        AND mii.delete_dttm IS NULL
        AND mvi.serverseq = 1604
      GROUP BY mvi.serverseq   
      ) rps) AS rpss ON cnf.serverseq = rpss.serverseq
ORDER BY ord





select * from tb_server order by serverseq

select * from  tb_curalarm

s
order by serverseq


select * from  tb_montargetvdud

select * from tb_monviewcatalog
order by viewseq