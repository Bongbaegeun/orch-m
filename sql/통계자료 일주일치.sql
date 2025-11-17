

-- 통계 가져오기.
SELECT mtd.day, mii.monitorobject, mii.moniteminstanceseq, mtc.monitoritem, mtd.avg_int
FROM tb_monitemcatalog AS mtc, tb_moniteminstance AS mii 
LEFT OUTER JOIN tb_monitemtrend_day AS mtd ON mtd.moniteminstanceseq = mii.moniteminstanceseq 
LEFT OUTER JOIN tb_monviewinstance AS mvi ON  mvi.moniteminstanceseq = mii.moniteminstanceseq 
WHERE mii.delete_dttm is null 
AND mii.serverseq =386
AND mtc.monitemcatseq = mii.monitemcatseq 
AND mtc.monitemcatseq in ('78','79','90','91','105','106')
AND TO_DATE(mtd.day, 'YYYY-MM-DD') BETWEEN  CURRENT_DATE-7  AND  CURRENT_DATE -1
ORDER BY day, monitorobject

--GROUP BY mvi.serverseq




select * 
from tb_monitemcatalog
order by monitemcatseq

--
SELECT *  FROM tb_server
--
--
SELECT *  FROM tb_moniteminstance
where moniteminstanceseq = 47314


SELECT *  FROM tb_monviewcatalog

order by viewseq
--

SELECT *  FROM tb_monitemtrend_day mtd
WHERE mtd.day = '2017-09-15'
  



select * 
from tb_monviewinstance
where moniteminstanceseq = 47314
order by monitorobject