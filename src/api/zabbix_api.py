# -*- coding: utf-8 -*-
import os, time
import threading
from util import db_sql
from util.db_mng import dbManager
from util import snmp

from pyzabbix import ZabbixAPI
import redis

ZB_SERVER = 'http://%s/zabbix'

def snmp_get ( snmp_info ) :
    try :         
        # SNMP
        return snmp.getSnmp(snmp_info, snmp_info['snmp_port'])
    except Exception, e:
        print ("SNMP ERROR : " + e)

def ping_check ( ip ) :
    response = os.popen("ping -c 1 -w 1 " + ip ).read()
    # print (response)
    return True if "1 received" in response else False

def get_hostid (zapi, hostname):
    # Host 있냐?
    ret = zapi.host.exists( host=hostname )
    if ret :
        host = zapi.host.get( filter={'host': '%s' % hostname} )
        return host[0]['hostid']
    else :
        return 0

def get_hostinterfaceid (zapi, hostname):
    # Host 있냐?
    ret = zapi.host.exists( host=hostname )
    if ret :
        host = zapi.host.get( filter={'host': '%s' % hostname} )
        hostinterface = zapi.hostinterface.get( hostids = host[0]['hostid'] )
        return hostinterface
    else :
        return 0

def create_host (snmp_info, cfg, template_model, logger):

    ZABBIX_SERVER = ZB_SERVER % cfg['zb_ip']
    ZABBIX_USER = cfg['zb_id']
    ZABBIX_PASSWORD = cfg['zb_passwd']
    
    hostname = snmp_info['onebox_id']
    group_name = snmp_info['zabbix_group']
    snmp_ip =  snmp_info['public_ip']
    snmp_port =  snmp_info['port']
    snmp_community = snmp_info['community']
    onebox_flavor = snmp_info['onebox_flavor']

    # TEMPLATE_NAME = cfg['icmp_template_name'] if group_name == 'Icmp' else cfg['snmp_template_name']

    if group_name == "Icmp":
        TEMPLATE_NAME = cfg['icmp_template_name']
    else:
        TEMPLATE_NAME = cfg['snmp_template_name']

        # Alias 적용할 템플릿 변경
        alias = False

        for tpl_m in template_model:
            if onebox_flavor == tpl_m['hw_model']:
                alias = True
                break

        if alias:
            TEMPLATE_NAME = cfg['snmp_template_name_alias']

        logger.debug("TEMPLATE_NAME = %s" % str(TEMPLATE_NAME))

    # logger.info ( " %s, %s,  %s, " % ( ZABBIX_SERVER, ZABBIX_USER, ZABBIX_PASSWORD, ) )

    zapi = ZabbixAPI(ZABBIX_SERVER)
    zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
    logger.info ( "create_host - Connected to Zabbix API Version %s" % zapi.api_version() )

    # 중복방지, Host 있냐?
    ret = zapi.host.exists( host=hostname )
    logger.info (ret)
    if ret :
        logger.error ('Host %s exists' % hostname)
        return False

    # Group 있냐?, 없으면 생성
    ret = zapi.hostgroup.exists( name=group_name )
    if ret == False :
        ret = zapi.hostgroup.create( name=group_name )
        groupid = ret['groupids'][0]
        logger.info('Group %s created' % groupid)
    else :    
        ret = zapi.hostgroup.get(filter={'name': '%s' % group_name})
        groupid = ret[0]['groupid']
        
    logger.info ( "Group ID: %s" % groupid )
    
    ret = zapi.template.get(filter={'name': '%s' % TEMPLATE_NAME})
    templateid = ret[0]['templateid']
    logger.info ( "Template ID: %s" % templateid )
    if group_name == 'Icmp' :
        ret = zapi.host.create( host=hostname,
            status= 1,
            interfaces=[{
                "type": 1,
                "main": 1,
                "useip": 1,
                "ip": snmp_ip,
                "dns": "",
                "port": 10050
            }],
            groups=[{
                "groupid": groupid
            }],
            templates=[{
                "templateid": templateid
            }]
        )    
    else :
        ret = zapi.host.create( host=hostname,
            status= 1,
            interfaces=[{
                "type": 2,
                "main": 1,
                "useip": 1,
                "ip": snmp_ip,
                "dns": "",
                "port": snmp_port,
                "bulk" : 0
            }],
            groups=[{
                "groupid": groupid
            }],
            templates=[{
                "templateid": templateid
            }]
        )    

        # SNMP_COMMUNITY 는 zabbix 2.4 에서 설정이 안되어, USER_MACRO 에 등록해서 사용한다.            
        ret = zapi.usermacro.create( hostid=ret['hostids'][0], macro = '{$SNMP_COMMUNITY}', value = snmp_community )
    logger.info(ret)
    
    return True

# Host 모니터 활성화, 비활성화
def set_monitor (hostname, status, cfg, logger):
    ZABBIX_SERVER = ZB_SERVER % cfg['zb_ip']
    ZABBIX_USER = cfg['zb_id']
    ZABBIX_PASSWORD = cfg['zb_passwd']

    zapi = ZabbixAPI(ZABBIX_SERVER)
    zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
    logger.info ( "set_monitor - Connected to Zabbix API Version %s" % zapi.api_version() )

    hostid = get_hostid(zapi, hostname)
    
    if hostid != 0 :
        ret = zapi.host.update( hostid=hostid, status=status)  # 0: enabled, 1: disabled
        logger.info ( "set_monitor - Host %s status changed to %s" % (hostname, status) )
        return True
    else :
        logger.error ('set_monitor - Host %s does not exist' % hostname)
        return False

# def update_macro (hostname, snmp_community):
#     zapi = ZabbixAPI(ZABBIX_SERVER)
#     zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)

#     hostid = get_hostid(zapi, hostname)

#     if hostid != 0 :
#         ret = zapi.host.update( hostid=hostid, macro = '{$SNMP_COMMUNITY}', value = snmp_community )
#         logger.info ( "update_macro - Host %s snmp_community to %s" % (hostname, snmp_community) )
#         return True
#     else :
#         logger.error ('update_macro - Host %s snmp_community change fail' % hostname)
#         return False


def update_host (snmp_info, cfg, logger):
    ZABBIX_SERVER = ZB_SERVER % cfg['zb_ip']
    ZABBIX_USER = cfg['zb_id']
    ZABBIX_PASSWORD = cfg['zb_passwd']

    hostname = snmp_info['onebox_id']
    group_name = snmp_info['zabbix_group']
    snmp_ip =  snmp_info['public_ip']
    snmp_port =  snmp_info['port']
    snmp_community = snmp_info['community']

    zapi = ZabbixAPI(ZABBIX_SERVER)
    zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
    logger.info ( "update_host - Connected to Zabbix API Version %s, modify_snmp_host" % zapi.api_version() )

    interface = get_hostinterfaceid(zapi, hostname)
    if interface != 0 :
        if group_name == 'Icmp' :
            ret = zapi.hostinterface.update( interfaceid=interface[0]['interfaceid'], ip = snmp_ip )
            logger.info ( "update_host - Host %s ip to %s" % (hostname, snmp_ip) ) 
            return True
        else :
            ret = zapi.hostinterface.update( interfaceid=interface[0]['interfaceid'], ip = snmp_ip, port = snmp_port )
            logger.info ( "update_host - Host %s snmp_ip to %s, snmp_port to %s" % (hostname, snmp_ip, snmp_port) ) 
    else : 
        logger.error ('update_host - Host %s fail' % hostname)
        return False

    # SNMP 일 경우  COMMUNITY 값 변경
    # MACRO 변경
    hostid = get_hostid(zapi, hostname)
    if hostid != 0 :
        ret = zapi.host.update( hostid=hostid, macros = [ { "macro" : "{$SNMP_COMMUNITY}", "value" : snmp_community}] )
        logger.info ( "update_host-macro - Host %s snmp_community change to %s" % (hostname, snmp_community) )
    else :
        logger.error ('update_host-macro - Host %s snmp_community change fail' % hostname)
        return False
    
    return True

def delete_host (onebox_id, cfg, logger):
    ZABBIX_SERVER = ZB_SERVER % cfg['zb_ip']
    ZABBIX_USER = cfg['zb_id']
    ZABBIX_PASSWORD = cfg['zb_passwd']
    
    hostname = onebox_id
    zapi = ZabbixAPI(ZABBIX_SERVER)
    zapi.login(ZABBIX_USER, ZABBIX_PASSWORD)
    logger.info ( "delete_host - Connected to Zabbix API Version %s, modify_snmp_host" % zapi.api_version() )

    hostid = get_hostid(zapi, hostname)
    if hostid != 0 :
        ret = zapi.host.delete( hostid )
        logger.info ( "delete_host - Host %s deleted " % hostname )
    else :
        logger.error ('delete_host - Host %s fail to delete' % hostname)
        return False
    
    return True
  
class snmp_host_start(threading.Thread):
    """
    - FUNC: tb_server_snmp 의 status 필드를 조회해서 새로 등록된 Host 가 
            ping 동작이 되면 Zabbix 에 활성화 명령
    - INPUT
        cfg(M): Orch-M 설정 정보
    """

    def __init__( self, cfg, logger ):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.logger = logger
        self.zabbix_server = ZB_SERVER % cfg['zb_ip']
        self.zabbix_user = ZB_SERVER % cfg['zb_id']
        self.zabbix_password = ZB_SERVER % cfg['zb_passwd']
        self.dbm = dbManager( 'snmpchk', self.cfg['db_name'], self.cfg['db_user'], self.cfg['db_passwd'],
                    self.cfg['db_addr'], int(self.cfg['db_port']), connCnt=1, _logger=logger )
        self.redis = redis

    def run(self):
        FNAME = 'SNMP-HOST status check'
        # self.logger.info ( FNAME )
        while True:
            self.logger.info ( FNAME )
            ret = self.dbm.select( db_sql.GET_SNMP_HOST_STATUS())

            for row in ret:
                if ret != None and len(ret) > 0 :
                    serverseq    = row['serverseq']
                    hostname     = row['onebox_id']
                    public_ip    = row['public_ip']
                    zabbix_group = row['zabbix_group']

                    snmp_info = {}
                    # snmp_info = 
                    snmp_info['snmp_ver']       = row['version']
                    snmp_info['snmp_community'] = row['community']
                    snmp_info['snmp_ip']        = row['public_ip']
                    snmp_info['snmp_port']      = row['port']

                    # FortiOS Version OID
                    snmp_info['snmp_oid'] = ['.1.3.6.1.4.1.12356.101.4.1.1.0']

                    # 22. 6.15 - lsh
                    # SNMP 조회후 FortiOS Version 정보 DB 기록 요청

                    # 22. 7.28
                    # ICMP 만 모니터링 하는 장비 신설. Ping 체크만
                    try :
                        
                        if zabbix_group == 'Icmp' :
                            if ping_check (snmp_info['snmp_ip']) :
                                time.sleep(2)
                                set_monitor (hostname, '0', self.cfg, self.logger)
                                self.dbm.execute( db_sql.UPDATE_SNMP_HOST_STATUS(serverseq) )
                                
                        else :
                            snmp_info = snmp_get ( snmp_info )
                            # 에러 날때
                            # INFO:orchm:{'ErrMessage': 'Got SNMP error: No SNMP response received before timeout', 'snmp_ip': '183.102.117.97', 'snmp_community': 'fortitest', 'snmp_port': '161', 'value': '0', 'snmp_oid': ['.1.3.6.1.4.1.12356.101.4.1.1.0'], 'dttm': datetime.datetime(2022, 6, 15, 10, 59, 3, 620406), 'snmp_ver': 'v2c'}
                            # self.logger.info ( snmp_info )
                            os_version = snmp_info['value']
                            # errMessage 가 비었으면 조회성공
                            # if len(snmp_info['ErrMessage']) == 0 :
                            #     # 시간차 이슈로 잠시 대기
                            #     time.sleep(2)
                            #     set_monitor (hostname, '0', self.cfg, self.logger)
                            #     self.dbm.execute( db_sql.UPDATE_SNMP_HOST_STATUS(serverseq) )
                            #     self.dbm.execute( db_sql.UPDATE_OS_VERSION(serverseq, os_version) )
                            #     self.logger.info ( "Host %s Active" % public_ip )
                            #
                            #     # 설치 후, 첫 장애 알람은 오지 않도록 하자
                            #     # key : onebox_id.event, value : 1, expire = 30M
                            #     redis = self.redis.Redis(host=self.cfg['zb_ip'], port=6379, db=2)
                            #
                            #     key = '%s.event' % str(hostname)
                            #     data = 1
                            #     expire = 60 * 30
                            #     redis.set(key, data, expire)
                            #
                            #     redis.close()

                            # snmp 장비도 Ping 체크만 되어도 감시 활성화
                            # 시간차 이슈로 잠시 대기
                            time.sleep(2)
                            set_monitor(hostname, '0', self.cfg, self.logger)
                            self.dbm.execute(db_sql.UPDATE_SNMP_HOST_STATUS(serverseq))
                            self.dbm.execute(db_sql.UPDATE_OS_VERSION(serverseq, os_version))
                            self.logger.info("Host %s Active" % public_ip)

                            # 설치 후, 첫 장애 알람은 오지 않도록 하자
                            # key : onebox_id.event, value : 1, expire = 30M
                            redis = self.redis.Redis(host=self.cfg['zb_ip'], port=6379, db=2)

                            key = '%s.event' % str(hostname)
                            data = 1
                            expire = 60 * 30
                            redis.set(key, data, expire)

                            redis.close()

                    except Exception, e:
                        self.logger.fatal(e)                    
                
            time.sleep(60)  
  