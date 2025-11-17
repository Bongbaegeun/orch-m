SELECT A.host, avg(hist.value_avg) :: INTEGER
FROM trends hist,
( SELECT h.host, i.itemid
FROM hosts h, items i
WHERE i.name = 'CPU Util'
AND i.hostid = h.hostid ) A
where hist.clock >= 1617330511
AND hist.itemid = A.itemid
GROUP BY host
ORDER BY avg DESC
limit 10
