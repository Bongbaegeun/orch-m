SELECT clock/60*60 as clk,  round(avg(value), 2) as avg_val
FROM history_uint hist, items i, hosts h
WHERE i.key_='9.linux.temperature.SVR' 
AND h.host='BONG190813.OB1' 
AND i.hostid=h.hostid 
AND hist.itemid=i.itemid 
AND hist.clock BETWEEN 1565708400 AND 1565794799
GROUP BY clk
ORDER BY DD



SELECT to_timestamp( clock/60*60) as day, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
FROM history_uint hist, items i, hosts h
WHERE i.key_='9.linux.temperature.SVR' 
AND h.host='BONG190813.OB1' 
AND i.hostid=h.hostid 
AND hist.itemid=i.itemid 
AND hist.clock BETWEEN 1565708400 AND 1565794799
GROUP BY day
ORDER BY day



SELECT 'D' as day, clock/30*30 as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
FROM history_uint hist, items i, hosts h
WHERE i.key_='9.linux.temperature.SVR'
AND h.host='BONG190813.OB1'
AND i.hostid=h.hostid
AND hist.itemid=i.itemid
AND hist.clock BETWEEN 1565708400 AND 1565794799
GROUP BY clk



select to_timestamp(t.clock) as day, i.name, t.value_avg, t.value_max
from trends t, items i, hosts h
where t.itemid = i.itemid
and h.hostid = 13747
and i.itemid = 169130
order by day DESC

limit 100


select * from trends limit 10

select * from items
where hostid = 13747
 limit 50

select * from hosts
where host = 'BONG190813.OB1'
 limit 100

