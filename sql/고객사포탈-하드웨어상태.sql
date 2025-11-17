                      SELECT
                                  mvci.viewseq
                                  , mii.moniteminstanceseq
                                  , srv.serverseq, srv.servername, srv.publicip, srv.onebox_id
                                  , mii.unit
                                  , rtp.monitoredyn
                                  , mtc.visiblename as targetname, mtc.targetversion
                                  , mii.monitorobject
                                  -- , mii.visiblename as itemname
                                  , mic.visiblename as itemname
                                  , case when rtp.monitoredyn = 'y' then rtp.monitorvalue
                                             else '0' end as monitorvalue
                                  , case when day.type = 'int' then day.avg_int
                                             else day.avg_float::int end as dayvalue
                                  , case when week.type = 'int' then week.avg_int
                                             else week.avg_float::int end as weekvalue
                                  , case when month.type = 'int' then month.avg_int
                                             else month.avg_float::int end as monthvalue
                      FROM tb_server as srv
                      LEFT OUTER JOIN tb_moniteminstance as mii ON srv.serverseq = mii.serverseq
                      LEFT OUTER JOIN tb_montargetcatalog as mtc ON mii.montargetcatseq = mtc.montargetcatseq
                      LEFT OUTER JOIN tb_mongroupcatalog mgc ON mii.mongroupcatseq=mgc.mongroupcatseq
                      
                      LEFT OUTER JOIN (
                                  SELECT
                                             mvi.serverseq, mvc.viewseq, mvc.viewname, mvc.monitortype, mvi.monitorobject, mvc.targettype, mvc.targetcode, mvi.moniteminstanceseq, mvc.groupname
                                  FROM tb_monviewcatalog as mvc
                                  LEFT OUTER JOIN tb_monviewinstance AS mvi ON mvc.viewseq = mvi.viewseq
                                  WHERE mvc.viewseq in (4, 5, 6, 9, 10)
                      ) AS mvci on mvci.serverseq = srv.serverseq
                                                                   AND mvci.groupname=mgc.groupname AND mvci.monitortype=mii.monitortype
                                                                   AND ( (mvci.targettype is not null AND mvci.targettype=mtc.targettype) OR (mvci.targettype is null AND mvci.targetcode=mtc.targetcode) )
                                                           AND ( (mvci.monitorobject is not null AND mii.monitorobject=mvci.monitorobject ) OR (mvci.monitorobject is null) )
                      
                      -- 감시항목의 측정 데이터를 불러오기
                      LEFT OUTER JOIN tb_realtimeperf AS rtp ON mii.moniteminstanceseq = rtp.moniteminstanceseq
                      
                      -- 전일 데이터 불러오기
                      LEFT OUTER JOIN tb_monitemtrend_day as day on day.moniteminstanceseq = mii.moniteminstanceseq and day.day = substring((now() - interval '1 day')::text from 1 for 10)
                      
                      -- 전주 데이터 가져오기
                      LEFT OUTER JOIN tb_monitemtrend_week as week on week.moniteminstanceseq = mii.moniteminstanceseq and week.week = substring((date_trunc('week', CURRENT_TIMESTAMP - interval '1 week'))::text from 1 for 10)
                      
                      -- 전월 데이터 가져오기
                      LEFT OUTER JOIN tb_monitemtrend_month as month on month.moniteminstanceseq = mii.moniteminstanceseq and month.month = substring((date_trunc('month', CURRENT_TIMESTAMP - interval '1 month'))::text from 1 for 10)
                      
                      -- item명 가져오기
                      left outer join (select mm.visiblename, mc.monitemcatseq from tb_mapping_monportal as mm, tb_monitemcatalog as mc where mm.item_id = mc.item_id) as mic on mii.monitemcatseq = mic.monitemcatseq
                      WHERE srv.customerseq = 236
				AND mii.delete_dttm is null
                                  AND mtc.targetcode = 'os'
                                  AND mvci.moniteminstanceseq is not null
AND srv.onebox_id = 'GAJA.OB1'
ORDER BY srv.serverseq, mvci.viewseq
