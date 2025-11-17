SELECT clk, val 
FROM (
	(
        SELECT clock/600*600 as clk, round(avg(value), 2) as val
        FROM history_uint hist, items i, hosts h
        WHERE i.key_='9.linux.cpu.Util' 
        AND h.host='BMT14.OB1' 
        AND i.hostid=h.hostid 
        AND hist.itemid=i.itemid
        -- AND hist.clock BETWEEN c.sdttm AND c.edttm
        -- 1533567601;1533654000
        AND hist.clock BETWEEN 1533567601 AND 1533654000
        GROUP BY clk
        )
        UNION
        (
        SELECT clock clk, round(value, 2) as val
        FROM history_uint hist, items i, hosts h
        WHERE i.key_='9.linux.cpu.Util' AND h.host='BMT14.OB1' AND i.hostid=h.hostid AND hist.itemid=i.itemid
        AND to_char(current_timestamp, 'YYYY-MM-DD HH24:MI')<='2018-08-08 00:00:00'
        AND hist.clock>cast(extract(epoch from now()) as int)/600*600
        )
        
        UNION
        (
        SELECT clock/600*600 as clk, round(avg(value), 2) as val
        FROM history hist, items i, hosts h
        WHERE i.key_='9.linux.cpu.Util' AND h.host='BMT14.OB1' AND i.hostid=h.hostid AND hist.itemid=i.itemid
        AND hist.clock BETWEEN 1533567601 AND 1533654000
        -- AND hist.clock BETWEEN c.sdttm AND c.edttm
        GROUP BY clk
        )
        UNION
        (
        SELECT clock clk, round(value, 2) as val
        FROM history hist, items i, hosts h
        WHERE i.key_='9.linux.cpu.Util' AND h.host='BMT14.OB1' AND i.hostid=h.hostid AND hist.itemid=i.itemid
        AND to_char(current_timestamp, 'YYYY-MM-DD HH24:MI')<='2018-08-08 00:00:00'
        AND hist.clock>cast(extract(epoch from now()) as int)/600*600
        )) as stat
        
WHERE val is not null
ORDER BY clk desc
