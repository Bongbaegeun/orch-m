from pyzabbix.api import ZabbixAPI
import psycopg2

def get_onebox_list() : 
            
    Query = """ select servername, mgmtip from tb_server
                where nfsubcategory in ( 'One-Box', 'KtPnf') """

    dbConn = psycopg2.connect( database='orch_v1', user='onebox', password='kkh@2016!ok',
                                     host='192.168.123.14', port=5432 ,application_name='Orch-m Test' )
    dbConn.autocommit = True
    
    return dbConn.select(Query)


zapi = ZabbixAPI(url='http://127.0.0.1/zabbix/', user='Admin', password='onebox2016!')
zbx_svr = {}

# zabbix server host 모두 가져오기.
for h in zapi.hostinterface.get(selectHosts=["host", "ip"]) :
    zbx_svr[h["hosts"][0]["host"]] = h["ip"]

# Logout from Zabbix
zapi.user.logout()

# tb_server 에 모두 가져오기
onebox_list = get_onebox_list()

for r in onebox_list :
    if r[0] in zbx_svr :
        zbx_ip = zbx_svr[ r[0] ] 
        
        if zbx_ip <> r[1] :
            print ( "%s,  %s  %s" % ( r[0], zbx_ip, r[1] ))
