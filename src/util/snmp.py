#-*- coding: utf-8 -*-
import datetime
from pysnmp import hlapi

############################################################################################
# SNMP 관련 함수.
############################################################################################
def construct_object_types(list_of_oids):
    object_types = []
    for oid in list_of_oids:
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
    return object_types

    
def fetch(handler):
    try : 
        error_indication, error_status, error_index, var_binds = next(handler)
        if not error_indication and not error_status:
            result =  cast(var_binds[0][1])
        else:
            raise RuntimeError('Got SNMP error: {0}'.format(error_indication))
    except Exception, e: 
        return "0", str(e)

    return str(result), ""
    
def cast(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return float(value)
        except (ValueError, TypeError):
            try:
                return str(value)
            except (ValueError, TypeError):
                pass
    return value

def getSnmp( snmp_info, port=161, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):

    ip = snmp_info['snmp_ip']
    oids = snmp_info['snmp_oid']
    credentials = snmp_info['snmp_community']

    # ip = '220.86.29.36'
    # oids =  ['1.3.6.1.2.1.1.5.0']
    # credentials = 'public'

    # SNMP Version
    # http://snmplabs.com/pysnmp/docs/pysnmp-hlapi-tutorial.html
    # >>> CommunityData('public', mpModel=0)  # SNMPv1
    # CommunityData('public')
    # >>> CommunityData('public', mpModel=1)  # SNMPv2c
    # CommunityData('public')

    snmp_ver = 1 if snmp_info['snmp_ver'] == 'v2c' else 0

    handler = hlapi.getCmd(
        engine,
        hlapi.CommunityData(credentials,mpModel=snmp_ver),
        hlapi.UdpTransportTarget((ip, port)),
        context,
        *construct_object_types(oids)
    )
    snmp_info['dttm'] = datetime.datetime.now()
    value, snmp_info['ErrMessage'] = fetch(handler)
    
    snmp_info['value'] = value

    return snmp_info