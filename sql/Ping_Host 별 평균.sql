select to_timestamp( (hist.clock /3600) *3600) as datetime, h.host, round( avg(hist.value), 2) as avg
from hosts h, history hist, items i
where h.hostid = i.hostid
and hist.itemid = i.itemid
and i.name = 'SVR Ping'
and hist.clock > extract(epoch from now()- interval '1 day' ) 
group by h.host, to_timestamp( (hist.clock /3600)* 3600)
order by datetime, avg

