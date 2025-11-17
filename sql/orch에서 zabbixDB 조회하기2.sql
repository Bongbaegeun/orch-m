SELECT svr_seq, item_seq, val, mon_time, 
    CASE WHEN expire_time >= cur_time THEN 'y'ELSE 'n' END monitored
FROM 
(
	SELECT svr_seq, item_seq, val, period, to_timestamp(mon_clock) as mon_time, 
		to_timestamp(mon_clock) + (60+period)*interval '1 second' as expire_time, now() as cur_time
	FROM 
	(

		SELECT 	key.serverseq AS svr_seq,
			key.moniteminstanceseq AS item_seq, 
			period, zabbix.clock AS mon_clock
			, CASE WHEN zabbix.value_str IS NULL THEN CAST(COALESCE(zabbix.value_int, '0') AS TEXT) ELSE zabbix.value_str END val
		FROM 	tb_server svr, 
			tb_mapzbkeyinstance key, 
			tb_moniteminstance item, 
			dblink
			( 'host=211.224.204.208 user=zabbix password=zabbix dbname=zabbix',
			'SELECT host as host_name, key_ as item_key, value_int, value_str, clock
			FROM
			(
				SELECT *, ROW_NUMBER() over (PARTITION BY itemid ORDER BY clock DESC) rn
				FROM
				(
					SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
					FROM history hist, (
					SELECT itemid, key_, i.hostid, host
					FROM items i, hosts h
					WHERE h.host=''SEP.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
					) item
				WHERE hist.itemid=item.itemid
				AND hist.clock > 1516947064

				UNION

				SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
				FROM history_log hist, (
					SELECT itemid, key_, i.hostid, host
					FROM items i, hosts h
					WHERE h.host=''SEP.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
				) item
				  WHERE hist.itemid=item.itemid
				  AND hist.clock > 1516947064

				  UNION

				  SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
				  FROM history_str hist, (
				  SELECT itemid, key_, i.hostid, host
				  FROM items i, hosts h
				  WHERE h.host=''SEP.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
				  ) item
				  WHERE hist.itemid=item.itemid
				  AND hist.clock > 1516947064

				  UNION

				  SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
				  FROM history_text hist, (
				  SELECT itemid, key_, i.hostid, host
				  FROM items i, hosts h
				  WHERE h.host=''SEP.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
				  ) item
				  WHERE hist.itemid=item.itemid
				  AND hist.clock > 1516947064

				  UNION

				  SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
				  FROM history_uint hist, (
				  SELECT itemid, key_, i.hostid, host
				  FROM items i, hosts h
				  WHERE h.host=''SEP.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
				  ) item
				  WHERE hist.itemid=item.itemid
				  AND hist.clock > 1516947064
				  ) all_hist
				) recent_hist
				WHERE rn=1' ) AS zabbix ( host CHARACTER VARYING (128), key_ CHARACTER VARYING (255), value_int NUMERIC(20,0), value_str TEXT, clock INTEGER )
		WHERE svr.onebox_id=zabbix.host
		AND key.serverseq=svr.serverseq 
		AND key.moniteminstanceseq=item.moniteminstanceseq 
		AND item.delete_dttm IS NULL
		AND key.monitemkey=zabbix.key_
	) seq
	LEFT OUTER JOIN tb_realtimeperf perf ON seq.svr_seq=perf.serverseq AND seq.item_seq=perf.moniteminstanceseq
) time_comp
