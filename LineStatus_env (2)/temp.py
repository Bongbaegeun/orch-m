# -*- coding: utf-8 -*-

import multiprocessing as mp
import time
from pysnmp import hlapi

def construct_object_types(list_of_oids):
    object_types = []
    for oid in list_of_oids:
        object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))
    return object_types
    
def fetch(handler, count):
    result = []
    for i in range(count):
        try:
            error_indication, error_status, error_index, var_binds = next(handler)
            if not error_indication and not error_status:
                items = {}
                for var_bind in var_binds:
                    items[str(var_bind[0])] = cast(var_bind[1])
                result.append(items)
            else:
                raise RuntimeError('Got SNMP error: {0}'.format(error_indication))
        except StopIteration:
            break
    return result

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

    
def get(target, oids, credentials, port=161, engine=hlapi.SnmpEngine(), context=hlapi.ContextData()):
    handler = hlapi.getCmd(
        engine,
        credentials,
        hlapi.UdpTransportTarget((target, port)),
        context,
        *construct_object_types(oids)
    )
    return fetch(handler, 1)[0]


result_list = []
def log_result(result):
    # This is called whenever foo_pool(i) returns a result.
    # result_list is modified only by the main process, not the pool workers.

    print result
    # time.sleep(1)
    result_list.append(result)


def foo_pool(ip, oid):
    # SNMP 값 가져오기
    return get(ip, [oid], hlapi.CommunityData('public'))
  

def apply_async_with_callback():
    
    pool = mp.Pool(5)

    ip_list = []

    for i in range(100):
        ip_list.append (['220.86.29.36', '1.3.6.1.2.1.1.5.0'])

    for r in ip_list :
        pool.apply_async(foo_pool, (r[0], r[1]), callback = log_result)
        
    pool.close()
    pool.join()
    print(result_list)

if __name__ == '__main__':
    apply_async_with_callback()