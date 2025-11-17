SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
FROM history_uint hist, (


    SELECT itemid, key_, i.hostid , host
    FROM items i, hosts h, 
    ( 
      SELECT DISTINCT ikey.monitemkey AS item_key, period
      FROM tb_mapzbkeyinstance ikey, 
     (
        SELECT moniteminstanceseq, period 
        FROM tb_moniteminstance mii, tb_server svr
        WHERE mii.serverseq=svr.serverseq
        AND mii.delete_dttm IS NULL
        AND mii.realtimeyn='y' 
        AND mii.monitoryn='y'  
      ) item
      WHERE item.moniteminstanceseq = ikey.moniteminstanceseq 
      ORDER BY item_key
    ) item
    WHERE  1=1
    AND h.hostid = i.hostid
    AND i.key_ = item.item_key
    AND i.delay = item.period
    -- and h.host = 'UBUNTU18.OB1'
    

    ) item
WHERE hist.itemid=item.itemid 
AND hist.clock > 1623197400

