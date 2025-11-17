SELECT
                                  cnf.serverseq, cnf.nsseq, cnf.name, cnf.fnc, cnf.version, cnf.vdudseq,
                                  cnf.publicip,perf.state, perf.c4, perf.c5, perf.c6,
                                  case when cnf.name = 'KT-UTM' or cnf.name = 'KT-VNF' or cnf.name = 'AXGATE-UTM' then 1 else 2 end as ord, 
                                  nms.c8,
                                  perf.c9, perf.c10, perf.montargetcatseq,
                                  alarmcnt.cur, alarmcnt.total, cnf.description,cnf.weburl, cnf.nf_type,
                                  -- utm
                                  coalesce(c28, '0') as c28, coalesce(c29, '0') as c29, coalesce(c30, '0') as c30, coalesce(vnic_sum, 0) as vnic_sum 
                      FROM (
                      
                                  -- 구성정보
                                  SELECT
                                             s.serverseq,  
                                             -- 2017.03.6 이중화작업으로 수정
                                             s.publicip,
                                             ns.nsseq, nc.name, '' AS fnc, nc.version, vdud.vdudseq, nf.description, nf.weburl, nf.name AS nf_type
                                  FROM tb_nfcatalog AS nc
                                  LEFT JOIN tb_nfr AS nf ON nf.nfcatseq = nc.nfcatseq
                                  LEFT JOIN tb_nsr AS ns ON ns.nsseq = nf.nsseq
                                  LEFT JOIN TB_NFCATALOG AS ncl ON nf.NFCATSEQ = ncl.NFCATSEQ
                                  LEFT OUTER JOIN tb_server AS s ON s.nsseq = ns.nsseq
                                  LEFT OUTER JOIN tb_vdud AS vdud ON vdud.nfcatseq = nc.nfcatseq
                                  WHERE ns.nsseq = 1113
                      ) AS cnf
                      
                      -- 성능정보
                      LEFT OUTER JOIN (
                                  select
                                             vdudseq
                                             , CASE
                                                        WHEN MAX(monitoredyn) = 'y' THEN 'RUNNING'
                                                        ELSE 'STOP' end as state
                                             , MAX(montargetcatseq) AS montargetcatseq
                                             , MAX(case when viewseq = 4 THEN monitorvalue END)::numeric::integer AS c4
                                             , MAX(case when viewseq = 5 THEN monitorvalue END)::numeric::integer AS c5
                                             , MAX(case when viewseq = 6 THEN monitorvalue END)::numeric::integer AS c6
                                             , MAX(case when viewseq = 9 THEN monitorvalue END)::numeric::integer AS c9
                                             , MAX(case when viewseq = 10 THEN monitorvalue END)::numeric::integer AS c10
                                  from (
                                             SELECT
                                                        CASE
                                                                   WHEN mgc.groupname = 'vcpu' AND mii.monitortype = 'Util' THEN 4 
                                                                   WHEN mgc.groupname = 'vmem' AND mii.monitortype = 'Util' THEN 5
                                                                   WHEN mgc.groupname = 'vdisk' AND mii.monitortype = 'Util' THEN 6
                                                                   WHEN mgc.groupname = 'vnet' AND mii.monitortype = 'Rx Rate' THEN 9
                                                                   WHEN mgc.groupname = 'vnet' AND mii.monitortype = 'Tx Rate' THEN 10
                                                        END AS viewseq
                                                        , rtp.serverseq
                                                        , s.nsseq
                                                        , rtp.monitorvalue
                                                        , rtp.monitoredyn
                                                        , mii.montargetcatseq
                                                        , mtv.vdudseq
                                             FROM tb_realtimeperf as rtp
                                             LEFT OUTER JOIN tb_server as s on rtp.serverseq = s.serverseq
                                             LEFT OUTER JOIN tb_moniteminstance as mii on mii.moniteminstanceseq = rtp.moniteminstanceseq
                                             LEFT OUTER JOIN tb_montargetcatalog as mtc on mtc.montargetcatseq = mii.montargetcatseq
                                             LEFT OUTER JOIN tb_mongroupcatalog as mgc on mgc.mongroupcatseq = mii.mongroupcatseq
                                             LEFT OUTER JOIN tb_montargetvdud as mtv on mtv.serverseq = s.serverseq and mtv.montargetcatseq = mii.montargetcatseq
                                             WHERE s.nsseq = 1113
                                  ) AS perf
                                  WHERE perf.viewseq is not null
                                  GROUP BY vdudseq
                      ) AS perf ON cnf.vdudseq = perf.vdudseq
                      
                      -- 장애 수
                      LEFT OUTER JOIN (
                                  SELECT
                                             ca.nsseq, mtv.vdudseq,
                                             sum(CASE WHEN faultstagecode != '해제' AND faultgradecode NOT IN('WARNING', 'MINOR') THEN 1 ELSE 0 END) AS cur,
                                             sum(CASE WHEN faultgradecode NOT IN('WARNING', 'MINOR') THEN 1 ELSE 0 END) AS total
                                  FROM tb_curalarm as ca
                                  LEFT OUTER JOIN tb_server AS s ON ca.nsseq = s.nsseq
                                  LEFT OUTER JOIN tb_montargetcatalog as mtc on ca.montargetcatseq = mtc.montargetcatseq
                                  LEFT OUTER JOIN tb_montargetvdud as mtv on mtv.serverseq = s.serverseq
                                                        and mtv.montargetcatseq = mtc.montargetcatseq
                                                        and mtv.vdudseq = mtv.vdudseq
                                  WHERE ca.nsseq = 1113
                                  group by ca.nsseq, mtv.vdudseq
                      ) AS alarmcnt ON cnf.nsseq = alarmcnt.nsseq and cnf.vdudseq = alarmcnt.vdudseq
                      
                      -- 2017.03.30 c8 컬럼 표시를 up에서 1/1으로 변경
                      left outer join ( 
                                  SELECT c8, svr.nsseq
                                             FROM ( 
                                                        SELECT mvi.serverseq,
                                                                   sum((case when mvi.viewseq = 8 then rtp.monitorvalue end)::int)::text || '/' ||
                                                                   count(case when mvi.viewseq = 8 then rtp.monitorvalue end)::text c8                  
                                                        FROM tb_monviewinstance AS mvi 
                                                        LEFT OUTER JOIN tb_moniteminstance AS mii ON mvi.moniteminstanceseq = mii.moniteminstanceseq
                                                        LEFT OUTER JOIN tb_realtimeperf AS rtp ON rtp.moniteminstanceseq = mii.moniteminstanceseq AND rtp.monitoredyn = 'y' 
                                                        WHERE mvi.moniteminstanceseq is not null 
                                                                   AND mii.delete_dttm is null 
                                                        GROUP BY mvi.serverseq
                                             ) AS item
                                             LEFT OUTER JOIN (
                                                        SELECT svr.serverseq, svr.customerseq, svr.nsseq
                                                        FROM tb_maphostinstance AS mhi
                                                        LEFT OUTER JOIN tb_server AS svr ON mhi.serverseq = svr.serverseq 
                                                        LEFT OUTER JOIN tb_customer AS customer ON svr.customerseq = customer.customerseq
                                                        WHERE svr.nfsubcategory = 'One-Box' 
                                             ) AS svr ON item.serverseq = svr.serverseq
                                             where svr.nsseq = 1113
                                  limit 1) AS nms ON cnf.nsseq = nms.nsseq
                      
                      -- 2017.04.24 utm cpu/mem/vdisk/vnic
                      left outer join (
                                  select rps.serverseq, 
                                  -- utm
                                  rps.c28, rps.c29, rps.c30, 
                                  rps.c54 + rps.c55 + rps.c56 + rps.c57 + rps.c58 + rps.c59 as vnic_sum 
                                  from (
                                             SELECT
                                                        mvi.serverseq, 
                                                        -- UTM
                                                        max(case when mvi.viewseq = 34 then rtp.monitorvalue end) c28, -- utm cpu
                                                        max(case when mvi.viewseq = 35 then rtp.monitorvalue end) c29, -- utm mem
                                                        max(case when mvi.viewseq = 36 then rtp.monitorvalue end) c30, -- utm vdisk
                                                        -- Network(vNIC): Wan
                                                        sum((case when mvi.viewseq = 54 or mvi.viewseq = 38 then rtp.monitorvalue end)::int) c54,
                                                        sum((case when mvi.viewseq = 55 or mvi.viewseq = 40 then rtp.monitorvalue end)::int) c55,
                                                        -- Network(vNIC): Office
                                                        sum((case when mvi.viewseq = 56 or mvi.viewseq = 39 then rtp.monitorvalue end)::int) c56,
                                                        sum((case when mvi.viewseq = 57 or mvi.viewseq = 41 then rtp.monitorvalue end)::int) c57,
                                                        -- Network(vNIC): Server
                                                        sum((case when mvi.viewseq = 58 then rtp.monitorvalue end)::int) c58,
                                                        sum((case when mvi.viewseq = 59 then rtp.monitorvalue end)::int) c59
                                             FROM tb_monviewinstance AS mvi 
                                             LEFT OUTER JOIN tb_moniteminstance AS mii ON mvi.moniteminstanceseq = mii.moniteminstanceseq
                                             LEFT OUTER JOIN tb_realtimeperf AS rtp ON rtp.moniteminstanceseq = mii.moniteminstanceseq AND rtp.monitoredyn = 'y' 
                                             LEFT OUTER JOIN tb_curalarm AS ca ON mii.moniteminstanceseq = ca.moniteminstanceseq AND ca.faultstagecode = '발생'
                                             WHERE mvi.moniteminstanceseq is not null 
                                                        AND mii.delete_dttm is null 
                                                        and mvi.serverseq = (select ts.serverseq from tb_server ts where ts.nsseq = 1113)
                                             GROUP BY mvi.serverseq
                                  ) rps
                      ) AS rpss ON cnf.serverseq = rpss.serverseq 
                      order by ord
