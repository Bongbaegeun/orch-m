SELECT * from dblink( 'host=211.224.204.225
user=zabbix
password=zabbix
dbname=zabbix', 
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
  WHERE h.host=''HATEST0124.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
  ) item
  WHERE hist.itemid=item.itemid
  AND hist.clock > 1516856293

  UNION

  SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
  FROM history_log hist, (
  SELECT itemid, key_, i.hostid, host
  FROM items i, hosts h
  WHERE h.host=''HATEST0124.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
  ) item
  WHERE hist.itemid=item.itemid
  AND hist.clock > 1516856293

  UNION

  SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
  FROM history_str hist, (
  SELECT itemid, key_, i.hostid, host
  FROM items i, hosts h
  WHERE h.host=''HATEST0124.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
  ) item
  WHERE hist.itemid=item.itemid
  AND hist.clock > 1516856293

  UNION

  SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
  FROM history_text hist, (
  SELECT itemid, key_, i.hostid, host
  FROM items i, hosts h
  WHERE h.host=''HATEST0124.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
  ) item
  WHERE hist.itemid=item.itemid
  AND hist.clock > 1516856293

  UNION

  SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
  FROM history_uint hist, (
  SELECT itemid, key_, i.hostid, host
  FROM items i, hosts h
  WHERE h.host=''HATEST0124.OB1'' AND key_ in (''9.linux.mem.Util'', ''9.linux.cpu.Util'', ''9.linux.process.Process[rabbitmq-server]'', ''9.linux.process.Process[/usr/sbin/mysqld]'', ''9.linux.process.Service[zabbix-agent]'', ''9.linux.process.Service[onebox-agent]'', ''9.linux.process.Service[onebox-vnfm]'', ''9.linux.process.Service[nova-api]'', ''9.linux.process.Service[apache2]'', ''9.linux.process.Service[neutron-server]'', ''9.linux.process.Service[glance-api]'', ''9.linux.process.Service[znmsc]'', ''9.linux.net.Status[eth0]'', ''9.linux.net.Status[eth2]'', ''9.linux.net.Status[eth3]'', ''9.linux.net.Status[eth4]'', ''11.UTM.vmem.Util'', ''11.UTM.vcpu.Util'', ''11.UTM.daemon.Status[vpn]'') AND i.hostid=h.hostid
  ) item
  WHERE hist.itemid=item.itemid
  AND hist.clock > 1516856293
  ) all_hist

  ) recent_hist

  WHERE rn=1'
  ) AS zabbix ( host character varying(128), key_ character varying(255), value_int numeric(20,0), value_str text, clock integer )

