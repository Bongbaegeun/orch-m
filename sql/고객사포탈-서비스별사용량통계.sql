SELECT 
                CASE 
                                WHEN monitoritem = 'VCPU Util' THEN 4 
                                WHEN monitoritem = 'VCPU UtilRate' THEN 4 
                                WHEN monitoritem = 'CALLBOX VCPU Util' THEN 4 

                                WHEN monitoritem = 'VMEM UtilRate' THEN 5 
                                WHEN monitoritem = 'CALLBOX VMEM UtilRate' THEN 5
                                
                                WHEN monitoritem = 'UTM VDisk UtilRate' THEN 6 
                                WHEN monitoritem = 'CALLBOX VDisk UtilRate' THEN 6 
                                WHEN monitoritem = 'WiMS VDisk UtilRate' THEN 6 
                                WHEN monitoritem = 'XMS VDisk UtilRate' THEN 6 
                                
                                WHEN monitoritem = 'UTM VNet Rx_Rate' THEN 9 
                                WHEN monitoritem = 'CALLBOX VNet Rx_Rate' THEN 9 
                                WHEN monitoritem = 'WAF Network Rx_Rate' THEN 9 
                                WHEN monitoritem = 'WiMS VNet Rx_Rate' THEN 9 
                                WHEN monitoritem = 'XMS VNet Rx_Rate' THEN 9 
                                
                                WHEN monitoritem = 'UTM VNet Tx_Rate' THEN 10 
                                WHEN monitoritem = 'CALLBOX VNet Tx_Rate' THEN 10 
                                WHEN monitoritem = 'WAF Network Tx_Rate' THEN 10 
                                WHEN monitoritem = 'WiMS VNet Tx_Rate' THEN 10 
                                WHEN monitoritem = 'XMS VNet Tx_Rate' THEN 10 
                END AS viewseq , 
                mii.moniteminstanceseq , 
                mtc.montargetcatseq , 
                srv.serverseq, 
                srv.servername, 
                srv.publicip, 
                srv.onebox_id , 
                mii.unit , 
                rtp.monitoredyn , 
                mtc.visiblename AS targetname, 
                mtc.targetversion , 
                mii.monitorobject 
                -- , mii.visiblename 
                , 
                mic.visiblename , 
                CASE 
                                WHEN rtp.monitoredyn = 'y' THEN rtp.monitorvalue 
                                ELSE '0' 
                END AS monitorvalue , 
                CASE 
                                WHEN day.type = 'int' THEN day.avg_int 
                                ELSE day.avg_float::int 
                END AS dayvalue , 
                CASE 
                                WHEN week.type = 'int' THEN week.avg_int 
                                ELSE week.avg_float::int 
                END AS weekvalue , 
                CASE 
                                WHEN month.type = 'int' THEN month.avg_int 
                                ELSE month.avg_float::int 
                END AS monthvalue , 
                mtc.vendorcode , 
                mtc.targettype 
FROM            tb_moniteminstance AS mii 
LEFT OUTER JOIN tb_server          AS srv 
ON              srv.serverseq = mii.serverseq 
LEFT OUTER JOIN tb_montargetcatalog AS mtc 
ON              mtc.montargetcatseq = mii.montargetcatseq 
LEFT OUTER JOIN tb_realtimeperf AS rtp 
ON              mii.moniteminstanceseq = rtp.moniteminstanceseq 
                -- 전일 데이터 불러오기 
LEFT OUTER JOIN tb_monitemtrend_day AS day 
ON              day.moniteminstanceseq = mii.moniteminstanceseq 
AND             day.day = substring((Now() - interval '1 day')::text FROM 1 FOR 10) 
                -- 전주 데이터 가져오기 
LEFT OUTER JOIN tb_monitemtrend_week AS week 
ON              week.moniteminstanceseq = mii.moniteminstanceseq 
AND             week.week = substring((date_trunc('week', CURRENT_TIMESTAMP - interval '1 week'))::text FROM 1 FOR 10)
                -- 전월 데이터 가져오기 
LEFT OUTER JOIN tb_monitemtrend_month AS month 
ON              month.moniteminstanceseq = mii.moniteminstanceseq 
AND             month.month = substring((date_trunc('month', CURRENT_TIMESTAMP - interval '1 month'))::text FROM 1 FOR 10)
                -- item명 가져오기 
LEFT OUTER JOIN 
                ( 
                       SELECT mm.visiblename, 
                              mc.monitemcatseq 
                       FROM   tb_mapping_monportal AS mm, 
                              tb_monitemcatalog    AS mc 
                       WHERE  mm.item_id = mc.item_id) AS mic 
ON              mii.monitemcatseq = mic.monitemcatseq 
WHERE           srv.customerseq = 316 
AND             mtc.targetcode ='vnf' 
AND             mii.delete_dttm IS NULL 
AND             mii.monitoritem IN ( 'VCPU Util', 
                                    'VCPU UtilRate', 
                                    'VMEM UtilRate', 
                                    'UTM VDisk UtilRate', 
                                    'WiMS VDisk UtilRate', 
                                    'XMS VDisk UtilRate', 
                                    'UTM VNet Rx_Rate', 
                                    'UTM VNet Tx_Rate', 
                                    'WAF Network Rx_Rate', 
                                    'WAF Network Tx_Rate', 
                                    'WiMS VNet Rx_Rate', 
                                    'WiMS VNet Tx_Rate', 
                                    'XMS VNet Rx_Rate', 
                                    'XMS VNet Tx_Rate', 
                                    'CALLBOX VCPU Util', 
                                    'CALLBOX VMEM UtilRate', 
                                    'CALLBOX VDisk UtilRate', 
                                    'CALLBOX VNet Rx_Rate', 
                                    'CALLBOX VNet Tx_Rate' ) 
AND             srv.onebox_id = 'OBD148.OB1' 
ORDER BY        mtc.montargetcatseq, 
                viewseq, 
                mii.monitorobject