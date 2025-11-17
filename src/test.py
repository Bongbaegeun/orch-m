from util import snmp


snmp_info = {}
snmp_info['snmp_ver'] = 'v2c'
snmp_info['snmp_community'] = 'flex@2022'
snmp_info['snmp_ip'] = '183.102.117.100'
snmp_info['snmp_port'] = 161

# Device Model
snmp_info['snmp_oid'] = ['.1.3.6.1.2.1.1.5.0']

ret = snmp.getSnmp(snmp_info), snmp_info['snmp_port']
print ( snmp_info['value']  )

