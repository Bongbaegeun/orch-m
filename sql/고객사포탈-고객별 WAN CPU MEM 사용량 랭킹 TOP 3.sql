SELECT A.servername, A.serverseq, A.orgnamescode, ROUND(A.avg, 2) as value
	,'WAN' as category
	,CASE WHEN rank <= 3 THEN rank ELSE NULL END TOP 
	,CASE WHEN total_count-2 <= rank THEN total_count - rank  +1 ELSE NULL END BOTTOM
FROM 
(
	SELECT svr.servername servername, svr.serverseq serverseq, svr.orgnamescode
	    ,avg(mtd.avg_int)
	    ,ROW_NUMBER() OVER (order by avg(mtd.avg_int) DESC ) rank
	    ,count(*) over () as total_count
	FROM tb_server svr, tb_server_wan wan, tb_moniteminstance mii, tb_monitemtrend_day mtd
	WHERE customerseq = 988
	AND svr.serverseq = wan.serverseq
	AND svr.serverseq = mii.serverseq
	AND mii.monitorobject = wan.nic
	AND mii.monitoritem in ( 'Network RX_Rate', 'Network TX_Rate')
	AND mii.moniteminstanceseq = mtd.moniteminstanceseq
	AND to_date(mtd.day, 'YYYY-MM-DD') > CURRENT_DATE -7
-- 	SDNET or ONEBOX 구분 필요.
--	AND substr( svr.ob_service_number,1,1) = 'W' 

	GROUP BY svr.servername, svr.serverseq
) A
WHERE ( rank <= 3 or total_count -3 < rank )
UNION ALL
SELECT A.servername, A.serverseq, A.orgnamescode, ROUND(A.avg, 2) as value
	,'CPU' as category
	,CASE WHEN rank <= 3 THEN rank ELSE NULL END TOP 
	,CASE WHEN total_count-2 <= rank THEN total_count - rank  +1 ELSE NULL END BOTTOM
FROM 
(
	SELECT svr.servername servername, svr.serverseq serverseq, svr.orgnamescode
		    , avg(mtd.avg_float)
		    , ROW_NUMBER() OVER (order by avg(mtd.avg_float) DESC ) rank
		    , count(*) over () as total_count
	FROM tb_server svr, tb_moniteminstance mii, tb_monitemtrend_day mtd
	WHERE svr.customerseq = 988
	AND svr.serverseq = mii.serverseq
	AND mii.monitoritem in ( 'CPU Util' )
	AND mii.moniteminstanceseq = mtd.moniteminstanceseq
	AND to_date(mtd.day, 'YYYY-MM-DD') > CURRENT_DATE -7
-- 	SDNET or ONEBOX 구분 필요.
--	AND substr( svr.ob_service_number,1,1) = 'W' 
	GROUP BY svr.servername, svr.serverseq
) A
WHERE ( rank <= 3 or total_count -3 < rank )
UNION ALL
SELECT A.servername, A.serverseq, A.orgnamescode, ROUND(A.avg, 2) as value
	,'MEM' as category
	,CASE WHEN rank <= 3 THEN rank ELSE NULL END TOP 
	,CASE WHEN total_count-2 <= rank THEN total_count - rank  +1 ELSE NULL END BOTTOM
FROM 
(
	SELECT svr.servername servername, svr.serverseq serverseq, svr.orgnamescode
		    , avg(mtd.avg_int)
		    , ROW_NUMBER() OVER (order by avg(mtd.avg_int) DESC ) rank
		    , count(*) over () as total_count
	FROM tb_server svr, tb_moniteminstance mii, tb_monitemtrend_day mtd
	WHERE svr.customerseq = 988
	AND svr.serverseq = mii.serverseq
	AND mii.monitoritem in ( 'Memory UtilRate' )
	AND mii.moniteminstanceseq = mtd.moniteminstanceseq
	AND to_date(mtd.day, 'YYYY-MM-DD') > CURRENT_DATE -7
-- 	SDNET or ONEBOX 구분 필요.
--	AND substr( svr.ob_service_number,1,1) = 'W' 
	GROUP BY svr.servername, svr.serverseq
) A
WHERE ( rank <= 3 or total_count -3 < rank )

