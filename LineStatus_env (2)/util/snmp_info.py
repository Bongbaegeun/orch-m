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

# 
# def fetch(handler, count):
#     result = []
#     for i in range(count):
#         try:
#             error_indication, error_status, error_index, var_binds = next(handler)
#             if not error_indication and not error_status:
#                 items = {}
#                 for var_bind in var_binds:
#                     items[str(var_bind[0])] = cast(var_bind[1])
#                 result.append(items)
#             else:
#                 raise RuntimeError('Got SNMP error: {0}'.format(error_indication))
#         except StopIteration:
#             break
#     return result
    
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

def getSnmp( line_info, port=161, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):

    ip = line_info.equip_ip
    oids =  [line_info.port_oid]
    credentials = line_info.snmp_read

    # ip = '220.86.29.36'
    # oids =  ['1.3.6.1.2.1.1.5.0']
    # credentials = 'public'

    # SNMP Version
    # http://snmplabs.com/pysnmp/docs/pysnmp-hlapi-tutorial.html
    # >>> CommunityData('public', mpModel=0)  # SNMPv1
    # CommunityData('public')
    # >>> CommunityData('public', mpModel=1)  # SNMPv2c
    # CommunityData('public')

    snmp_ver = 1 if line_info.snmp_ver == 'v2c' else 0

    handler = hlapi.getCmd(
        engine,
        hlapi.CommunityData(credentials,mpModel=snmp_ver),
        hlapi.UdpTransportTarget((ip, port)),
        context,
        *construct_object_types(oids)
    )
    line_info.dttm = datetime.datetime.now()
    value, line_info.ErrMessage = fetch(handler)

    # 장비에 따라서 결과값 변경.

        # AIH JAVA 소스 
        # if (StringUtils.isEmpty(snmpResult)) {
        #     rv.setModem_status("0");
        # } else if("V5724G".equals(model_name)){ //V5724G 예외처리
        #   if(snmpResult.contains("INTEGER: 4")){
        #       rv.setModem_status("1");
        #   } else {
        #       rv.setModem_status("0");
        #   }
        # } else if (snmpResult.contains("up") || snmpResult.contains("UP") || snmpResult.contains("Up")
        #         || snmpResult.contains("green") || snmpResult.contains("GREEN") || snmpResult.contains("Green")
        #         || snmpResult.contains("= 1")
        #         || snmpResult.contains("INTEGER: 1")
        #         ) {
        #     rv.setModem_status("1");
        # } else {
        #     rv.setModem_status("0");
        # }
    try : 

        if line_info.model_name == "V5724G" :
            value = "1" if value == "4" else "0" 
        elif value.upper() == "GREEN"  :
            value = "1" 
        elif value.upper() == "UP"  :
            value = "1" 
        elif value.upper() <> "1"  :
            value = "0" 

    except Exception, e: 
        print e

    # Test Code
    # value = "0"
    
    line_info.value = value

    return line_info
