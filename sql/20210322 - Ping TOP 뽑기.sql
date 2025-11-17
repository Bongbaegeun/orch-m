select h.host, hist.* from hosts h, items i, history hist
where h.hostid = i.hostid 
and i.name = 'SVR Ping'
and hist.itemid = i.itemid
order by clock desc