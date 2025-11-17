    SELECT host as host_name, key_ as item_key, value_int, value_str, clock
    FROM
        (
        SELECT *, ROW_NUMBER() over (PARTITION BY itemid ORDER BY clock DESC) rn
        FROM
        
            (
            SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
            FROM history hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='INSTEST1.OB1' AND key_ in ('icmpping[]', 'net.tcp.service[tcp,,10050]') AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid AND to_timestamp(hist.clock) > (current_timestamp - interval '20 second')
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
            FROM history_log hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='INSTEST1.OB1' AND key_ in ('icmpping[]', 'net.tcp.service[tcp,,10050]') AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid AND to_timestamp(hist.clock) > (current_timestamp - interval '20 second')
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
            FROM history_str hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='INSTEST1.OB1' AND key_ in ('icmpping[]', 'net.tcp.service[tcp,,10050]') AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid AND to_timestamp(hist.clock) > (current_timestamp - interval '20 second')
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
            FROM history_text hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='INSTEST1.OB1' AND key_ in ('icmpping[]', 'net.tcp.service[tcp,,10050]') AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid AND to_timestamp(hist.clock) > (current_timestamp - interval '20 second')
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
            FROM history_uint hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='INSTEST1.OB1' AND key_ in ('icmpping[]', 'net.tcp.service[tcp,,10050]') AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid AND to_timestamp(hist.clock) > (current_timestamp - interval '20 second')
            ) all_hist
        
        ) recent_hist
    
    WHERE rn=1
