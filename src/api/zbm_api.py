#-*- coding: utf-8 -*-
import psycopg2, json, time, threading, yaml
from time import sleep
from datetime import datetime
from util import rest_api, db_mng, db_sql
from api import web_api

import errno
from socket import error as SockErr
import time
import copy

# AES
from util.aes_cipher import AESCipher


#import logging
#fLogger = logging.getLogger('ZBM_API')
# 개발시 로그표시 유무.

ZABBIX = str(0)
SNMPV1 = str(1)
TRAPPER = str(2)
SIMPLE = str(3)
SNMPV2C = str(4)
INTERNAL = str(5)
SNMPV3 = str(6)
ZABBIX_ACTIVE = str(7)
AGGREGATE = str(8)
HTTPTEST = str(9)
EXTERNAL = str(10)
DB_MONITOR = str(11)
IPMI = str(12)
SSH = str(13)
TELNET = str(14)
CALCULATED = str(15)
JMX = str(16)
SNMPTRAP = str(17)


HEADER={"content-type":"application/json-rpc"}
METHOD="POST"

ZBM_URL = {
           'AddHost': '/HostService/create',
           'ModHost': '/HostService/update',
           'ModHostAddr': '/HostService/updateAddr',
           'DelHost': '/HostService/removeHost',
           'ChkItem': '/ItemService/getItemStatus',
           'AddTemp': '/TemplateService/importTemplate',
           'DelTemp': '/TemplateService/removeTemplate',
           
        #    'ModItemTemplate': '/TemplateService/updateTemplateItem',
           'ModItemTemplate': '/TemplateService/updateTemplateItem',

           'ModItemInst': '/ItemService/updateItem',
           'ModItemProtoInst':'/DiscoveryService/updateItemPrototype',
           'ModDiscoveryInst':'/DiscoveryService/updateDiscovery',
           'SetItemMonStatus':'/ItemService/disableItem',
           'AddTrigger':'/TriggerService/createTrigger',
           'AddTriggerProto':'/DiscoveryService/createTriggerPrototype',
           'DelTrigger':'/TriggerService/removeTrigger',
           'DelTriggerProto':'/DiscoveryService/removeTriggerPrototype',
           'ModTrigger':'/TriggerService/updateTrigger',
           'ModTriggerProto':'/DiscoveryService/updateTriggerPrototype',
           'AddTemplateItem':'/ItemService/addItem',
           'DelTemplateItem':'/ItemService/removeItem',
           'DelHostItem':'/ItemService/removeItem',
           'DelHostDisc':'/DiscoveryService/removeDiscovery'
           }

from util.gsf import VarShared
GVAR_FNAME = './cfg/orchm_shared.var'
GVAR_RELEASE = 'zbm_release'
gVar = VarShared(GVAR_FNAME)

DEF_HOST = 'localhost'
DEF_PORT = '7070'

CFG_NAME = './cfg/orchm.cfg'
cfg = None
with open(CFG_NAME, "r") as f:
    cfg = yaml.load(f)

if cfg.has_key('zbm_ip') :
    DEF_HOST = cfg['zbm_ip']
if cfg.has_key('zbm_port') :
    DEF_PORT = cfg['zbm_port']


def setArg(arg, argName, noneType=None):
    return (lambda x: x[argName] if 
    
    (argName) else noneType)(arg)

def _dataTypeToZB( _dataType ):
    """
    - FUNC: zbms 용의 데이터 타입으로 변환한다.
    - INPUT
        _dataType(M): Orch에서 사용하는 데이터 타입
    - OUTPUT : zbms 용 데이터 타입(float, int, str, text, log), 정의되지 않은 경우 None 반환
    """
    dataType = str(_dataType).lower()
    if dataType.find( 'float' ) > -1:
        return 'float' 
    elif dataType.find( 'int' ) > -1:
        return 'int'
    elif dataType.find( 'str' ) > -1:
        return 'str'
    elif dataType.find( 'text' ) > -1:
        return 'text'
    elif dataType.find( 'log' ) > -1:
        return 'log'
    else:
        return None

def alertGradeToZB( _grade ):
    """
    - FUNC: zbms 용의 장애 등급으로 변환한다.
    - INPUT
        _grade(M): Orch에서 사용하는 장애 등급
    - OUTPUT : zbms 용 장애 등급
        warn->2, minor->3, major->4, critical->5, 기타->None
    """
    grade = str(_grade).lower()
    if grade.find( 'warn' ) > -1 :
        return str(2)
    elif grade.find( 'min' ) > -1 :
        return str(3)
    elif grade.find( 'maj' ) > -1 :
        return str(4)
    elif grade.find( 'cri' ) > -1 :
        return str(5)
    else:
        return None

def makeZbKey( targetSeq, targetType, groupName, itemType, keyParam=None ):
    """
    - FUNC: zbms 용 항목 구분 Key를 생성한다.
    - INPUT
        targetSeq(M): 모니터링 아이템의 타켓 Sequence 번호
        targetType(M): 모니터링 아이템의 타켓 타입
        groupName(M): 모니터링 아이템의 그룹 이름
        itemType(M): 모니터링 아이템의 타입
        keyParam(O): 구분 Key에 추가될 기타 요소
    - OUTPUT : zbms 용 항목 구분 Key
        ex) 12.OS.CPU.UTIL
    """
    _key = str(targetSeq) +'.'+ str(targetType).replace(' ', '_') +'.'+ str(groupName).replace(' ', '_') +'.'+ str(itemType).replace(' ', '_')
    _key = _key.replace(' ', '')
    if keyParam == None:
        return _key
    else:
        return _key + str(keyParam).replace(' ', '_')

def makeZbCondition(_cdt, repeat=None):
    """
    - FUNC: zbms 용 임계치 조건문으로 변환한다.(orch의 조건문 마다 repeat이 설정된다.)
    - INPUT
        _cdt(M): Orch의 임계치 조건문
    - OUTPUT : zbms 용 임계치 조건문
    """
    if type(_cdt) == list :
        cdt = []
        for tmp in _cdt :
            if type( tmp ) == list or type( tmp ) == dict :
                cdt.append( makeZbCondition( tmp ) )  
            else:
                cdt.append( tmp )
        
    else:
        cdt = _cdt.copy()
        
    return cdt

def convertItem( logger, targetSeq, groupName, itemList, keyList, keyInput=None ):
    """
    - FUNC: zbms 용 Item parameter로 변환
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 감시 대상 Sequence
        groupName(M): 감시 그룹 이름
        itemList(M): 감시 항목 정보 리스트
        keyList(O): 변환한 감시 항목의 Key 정보를 저장할 객체
        keyInput(O): Zabbix에서 사용할 Key정보에 들어갈 parameter 정보
    - OUTPUT : zbms 용 Item Parameter
    """
    ret = { 'item':[], 'key':[] }
    
    chkItem = None
    macro = ( lambda x : '' if keyInput == None else ' - {#%s}'%keyInput )(keyInput)
    try:
        for _item in itemList :
            chkItem = _item
            item = {}
            item['name'] = str(_item['name']) + macro
            item['application'] = str(groupName)
            item['agent_type'] = str(ZABBIX_ACTIVE)
            if _item.has_key('monitor_method') : 
                if str(_item['monitor_method']).lower() == 'passive' :
                    item['agent_type'] = str(ZABBIX)
                elif str(_item['monitor_method']).lower() == 'simple' :
                    item['agent_type'] = str(SIMPLE)
                elif str(_item['monitor_method']).lower() == 'trap' :
                    item['agent_type'] = str(TRAPPER)
            
            if keyInput != None:
                item['key'] = _item['key']%('{#%s}'%keyInput)
            else:
                item['key'] = _item['key']

            logger.info ( "item['key'] : %s " % str(item['key']))
            logger.info ( "keyList : %s " % str(keyList))

            if item['key'] in keyList :
                logger.error( 'Duplicated ZB Key, key=%s, target=%s, group=%s, item=%s'%(
                                        item['key'], str(targetSeq), groupName, str(_item) ) )
                return False, 'Duplicated ZB Key, key=%s'%(item['key'])
            else:
                keyList.append( item['key'] )
            
            item['data_type'] = _dataTypeToZB(_item['data_type'])
            if item['data_type'] == None :
                logger.error( 'Unknown ZB DataType, dataType=%s, target=%s, group=%s, item=%s'%(
                                        _item['data_type'], str(targetSeq), groupName, str(_item) ) )
                return False, 'Unknown ZB DataType, dataType=%s'%(_item['data_type'])
            
            item['period'] = str(_item['period'])
            ## zabbix에 bps, B 같은 unit 설정하면 KBps, Mbps 등으로 장애 측정값이 반환되어 사용하지 않음
#             if _item.has_key('unit') : item['unit'] = str(_item['unit'])
            if _item.has_key('history') : item['history'] = str(_item['history'])
            if _item.has_key('statistic') : item['trend'] = str(_item['statistic'])
            if _item.has_key('description') : item['desc'] = str(_item['description'])
            
            item['trigger'] = []
            ## 기본은 템플릿에 트리거 정보를 추가하지 않으며 'threshold_zb_yn'가 'y'일 경우만 추가
            if _item.has_key('threshold') and _item.has_key('threshold_zb_yn') and str(_item['threshold_zb_yn']).lower() == 'y' : 
                trgList = []
                for _trg in _item['threshold'] :
                    trg = {}
                    trg['name'] = str(_trg['name']) + macro
                    trg['grade'] = alertGradeToZB(_trg['grade'])
                    if trg['grade'] == None:
                        logger.error( 'Unknown ZB Trigger Grade, grade=%s, target=%s, group=%s, item=%s'%(
                                                _trg['grade'], str(targetSeq), groupName, str(_item) ) )
                        return False, 'Unknown ZB Trigger Grade, grade=%s'%(_trg['grade'])
                     
                    trg['desc'] = _trg['description']
                    try:
                        trg['conditions'] = makeZbCondition( _trg['conditions'] )
                    except Exception, e:
                        logger.error( 'ZB Trigger Condition Error, condition=%s, target=%s, group=%s, item=%s'%(
                                        str(_trg['conditions']), str(targetSeq), groupName, str(_item) ) )
                        logger.fatal( e )
                        return False, 'ZB Trigger Condition Error, condition=%s'%str(_trg['conditions'])
                    ## trigger의 key 값
                    trg['comments'] = _trg['t_key']
                    trgList.append( trg )
                item['trigger'] = trgList
                
            item['graph'] = {}
            if _item.has_key('graph_yn') and str(_item['graph_yn']).upper() == 'Y' :
                item['graph']['xy'] = {'x':1, 'y':1}
            
            ret['item'].append( item )
        
        ret['key'] = keyList
        return True, ret
    except Exception, e:
        logger.error( 'ZB Item Convert Error, Item=%s'%str(chkItem) )
        logger.fatal( e )
        return False, 'ZB Item Conver Exception, e=%s'%str(e)
    
def convertDiscovery( logger, targetSeq, targetType, groupName, discoveryList, keyList ):
    """
    - FUNC: zbms 용 Discovery parameter로 변환
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 감시 대상 Sequence
        targetType(M): 감시 대상 종류(Key 생성 시 사용)
        groupName(M): 감시 그룹 이름(Key 생성 시 사용)
        discoveryList(M): Discovery 정보 리스트
        keyList(M): 변환한 Discovery의 Key 정보를 저장할 객체
    - OUTPUT : zbms 용 Discovery Parameter
    """
    ret = { 'discovery':[], 'key':[] }
    
    chkDisc = None
    try:
        for _disc in discoveryList :
            disc = {}
            disc['name'] = chkDisc = _disc['name']
            if _disc.has_key('zb_key'): disc['key'] = _disc['zb_key']
            else : disc['key'] = makeZbKey( targetSeq, targetType, groupName, disc['name'] )
            if disc['key'] in keyList :
                logger.error( 'Duplicated ZB Key, key=%s, target=%s, group=%s, discovery=%s'%(
                                        disc['key'], str(targetSeq), groupName, str(_disc) ) )
                return False, 'Duplicated ZB Key, key=%s'%(disc['key'])
            else:
                keyList.append( disc['key'] )
            
            disc['period'] = _disc['period']
            disc['desc'] = _disc['description']
            if _disc.has_key('remain'): disc['remain'] = _disc['remain']
            
            disc['agent_type'] = str(ZABBIX_ACTIVE)
            if _disc.has_key('monitor_method') : 
                if str(_disc['monitor_method']).lower() == 'passive' :
                    disc['agent_type'] = str(ZABBIX)
                elif str(_disc['monitor_method']).lower() == 'simple' :
                    disc['agent_type'] = str(SIMPLE)
                elif str(_disc['monitor_method']).lower() == 'trap' :
                    disc['agent_type'] = str(TRAPPER)
            
            if not _disc.has_key('item') :
                disc['item'] = []
            else:
                returnKey = _disc['return_field']
                isSucc, _ret = convertItem( logger, targetSeq, groupName, _disc['item'], keyList, returnKey)
                if not isSucc :
                    return False, _ret
                else:
                    disc['item'] = _ret['item']
            
            ret['discovery'].append( disc )
        
        ret['key'] = keyList
        return True, ret
    except Exception, e:
        logger.error( 'ZB Discovery Convert Error, Item=%s'%str(chkDisc) )
        logger.fatal( e )
        return False, 'ZB Discovery Convert Exception, e=%s'%str(e)

def handleSock(logger, sockErr):
    """
    - FUNC: zbms API 연결 실패 시 SocketError 인 오류를 처리
        1. errno.ECONNREFUSED : 연결 상태 관리를 release로 변경
    - INPUT
        logger(M): 로그 기록 객체
        sockErr(M): SocketError
    """
    logger.fatal(sockErr)
    if sockErr.errno == errno.ECONNREFUSED:
        gVar.locked_write_param(GVAR_RELEASE, 'y')
        logger.error('ZBM Connection Release')
        return
    
    return

def getResponse( logger, response, title, returnRes=False ):
    """
    - FUNC: zbms 연동한 결과를 Orch-M 용으로 변환
    - INPUT
        logger(M): 로그 기록 객체
        response(M): zbms 연동 결과
        title(M): 로그에 남길 요청 기능 이름
        returnRes(O): 요청 결과 값의 반환 여부
    - OUTPUT : Orch-M 용 zbms 연동 결과
    """
    if response != None and response.body != None :
        _body = json.loads(response.body)
        if _body.has_key('result') :
            logger.info( 'Success: %s'%title )
            if returnRes: return json.loads( _body['result'] )
            else: return True
        
        logger.error( _body['error'])
        if returnRes : return None
        else: return False
    else:
        # logger.error( 'REST Response Body is Null, response=%s'%str(response) )
        if returnRes : return None
        else: return False

def addTemplate( logger, targetSeq, targetName, targetVer, targetDesc, itemList=[], discoveryList=[], _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 템플릿 생성 요청
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 템플릿(대상) Sequence(zabbix 템플릿 ID, zabbix 템플릿의 이름 구성)
        targetName(M): 감시 대상 이름(zabbix 템플릿의 이름 구성)
        targetVer(M): 감시 대상 모니터링 버전 (zabbix 템플릿의 이름 구성)
        targetDesc(M): 감시 대상 설명 (zabbix 템플릿 설명)
        itemList(O): 감시 대상에 속한 감시 항목 리스트 (zabbix Item)
        discoveryList(O): 감시 대상에 속한 Discovery 리스트 (zabbix Discovery)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 템플릿 생성 결과(True/False)
    """
    try:
        body = {"template":{
                    "name":str(targetSeq),
                    "visible_name": str(targetSeq)+'.'+targetName+'[%s]'%targetVer,
                    "desc":targetDesc,
                    "item":itemList,
                    "discovery": discoveryList
                    }
                }
        logger.info( 'Add Template, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['AddTemp']), METHOD, body, 15 )
        return getResponse( logger, response, 'Add Template' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
     
    return False

def delTemplate( logger, targetSeq, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 템플릿 삭제 요청
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 템플릿(대상) Sequence(zabbix 템플릿 ID)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 템플릿 삭제 결과(True/False)
    """
    try:
        body = {"template_name":str(targetSeq)}
        logger.info( 'Del Template, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['DelTemp']), METHOD, body, 5 )
        return getResponse( logger, response, 'Del Template' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
     
    return False


def chkItemStatus( logger, hostName, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 감시항목 모니터링 상태 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 모니터링 상태(1:disable, 3:not_support)
    """
    try:
        body = { "hostname": hostName }
        logger.info( 'Check Item Status, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ChkItem']), METHOD, body, 5 )
        return getResponse( logger, response, 'Chk Item Status', True )
    except SockErr, e:
        handleSock(logger, e)
        return None
    except Exception, e:
        logger.fatal(e)
     
    return None

def addHost( logger, hostName, visibleName, ip, targetList, desc, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box(호스트) 등록
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        visibleName(M): One-Box 서버 이름(zabbix의 호스트 이름)
        ip(M): One-Box IP(zabbix의 호스트 IP)
        targetList(M): One-Box 감시할 감시대상 리스트(zabbix 템플릿 ID)
        desc(M): One-Box 서버 설명(zabbix의 호스트 설명)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : One-Box 등록 결과(True/False)
    """
    try:
        body = {"svr": {
                    "hostname": hostName,
                    "visible_name": visibleName,
                    "host_ip": ip,
                    "host_desc": desc,
                    "templates": targetList
                        }
                }
        logger.info( 'Add Server, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['AddHost']), METHOD, body, 5 )
        return getResponse( logger, response, 'Add Server' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
     
    return False

def modHost( logger, hostName, prevTargetList, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box(호스트)의 템플릿 변경 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        prevTargetList(M): 감시할 대상 Sequence List(zabbix 템플릿 ID 리스트, 기존 템플릿이 해당 템플릿으로 교체)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : One-Box 템플릿 변경 결과(True/False)
    """
    try:
        body = {"svr":{
                        "hostname":hostName,
                        "templates": prevTargetList
                    }
                }
        logger.info( 'Modify Server Template, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ModHost']), METHOD, body, 5 )
        return getResponse( logger, response, 'Modify Server Template' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def modHostAddr( logger, hostName, svrIP, svrNewIP, svrPort, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box(호스트)의 주소 변경 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        svrIP(M): One-Box 서버 기존 IP
        svrNewIP(M): One-Box 서버 신규 IP
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : One-Box 주소 변경 결과(True/False)
    """
    try:
        body = {"svr":{
                        "hostname":hostName,
                        "host_ip": svrIP,
                        "host_new_ip": svrNewIP,
                        "host_port": svrPort,
                    }
                }
        logger.info( 'Modify Server Address, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ModHostAddr']), METHOD, body, 5 )
        return getResponse( logger, response, 'Modify Server Address' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def delHost( logger, hostName, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box(호스트) 삭제 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : One-Box 삭제 결과(True/False)
    """
    try:
        body = { "svr":{ "hostname":hostName } }
        logger.info( 'Del Server, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['DelHost']), METHOD, body, 5 )
        return getResponse( logger, response, 'Del Server' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)

    return False

def setItemPeriod( logger, hostName, key, period=None, history=None, trend=None, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 감시항목 주기 설정 변경 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        key(M): 감시항목 구분 Key(zabbix의 Item Key)
        period(O): 감시항목의 감시 주기(초)
        history(O): 감시항목 측정 데이터 history 보관 기간(일)
        trend(O): 감시항목 통계 데이터 보관 기간(일)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 주기 변경 결과(True/False)
    """
    try:
        body = { 'hostname': hostName, 'key': key }
        if period != None :     body['period'] = str(period)
        if history != None :    body['history'] = str(history)
        if trend != None :      body['trend'] = str(trend)
        logger.info( 'Modify Item Instacne, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ModItemInst']), METHOD, body, 5 )
        return getResponse( logger, response, 'Modify ItemInstance' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def setItemPeriodTemplate(logger, template_name, key, period, _ip=DEF_HOST, _port=DEF_PORT):
    """템플릿에 속한 아이템의 감시주기 변경 요청
    """
    try:
        body = { 'template_name': template_name, 'key': key }
        if period != None :     body['period'] = str(period)
        logger.info( 'Modify Item Template, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ModItemInst']), METHOD, body, 5 )

        return getResponse( logger, response, 'Modify Template Item Period' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    return False

def modItemProtoInst( logger, hostName, iKey, dKey, period=None, history=None, trend=None, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 Discovery 감시항목 주기 설정 변경 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        iKey(M): Discovery 감시항목 구분 Key(zabbix의 ItemProto Key)
        dKey(M): Discovery 구분 Key(zabbix의 Discovery Key)
        period(O): Discovery 감시항목의 감시 주기(초)
        history(O): Discovery 감시항목 측정 데이터 history 보관 기간(일)
        trend(O): Discovery 감시항목 통계 데이터 보관 기간(일)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : Discovery 감시항목 주기 변경 결과(True/False)
    """
    try:
        body={ 'hostname':hostName, 'discovery_key': dKey, 'item_prototype': {'key':iKey} }
        if period != None :     body['item_prototype']['period'] = str(period)
        if history != None :    body['item_prototype']['history'] = str(history)
        if trend != None :      body['item_prototype']['trend'] = str(trend)
        logger.info( 'Modify ItemProto Instacne, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ModItemProtoInst']), METHOD, body, 5 )
        return getResponse( logger, response, 'Modify ItemProtoInst' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def modDiscoveryInst( logger, hostName, dKey, period=None, remain=None, desc=None, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 Discovery 주기 설정 변경 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        dKey(M): Discovery 구분 Key(zabbix의 Discovery Key)
        period(O): Discovery 갱신 주기(초)
        remain(O): Discovery 탐색 데이터 보관 기간(일)
        desc(O): Discovery 설명
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : Discovery 주기 변경 결과(True/False)
    """
    try:
        body={ 'hostname':hostName, 'key': dKey }
        if period != None :     body['period'] = str(period)
        if remain != None :     body['remain'] = str(remain)
        if desc != None :       body['desc'] = str(desc)
        logger.info( 'Modify Discovery Instacne, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['ModDiscoveryInst']), METHOD, body, 5 )
        return getResponse( logger, response, 'Modify DiscoveryInst' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False


def setItemMonStatus( logger, hostName, iKey, isOff, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 감시항목 감시 On/Off 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix의 호스트 ID)
        iKey(M): 감시항목 구분 Key(zabbix의 Item Key)
        isOff(M): 감시항목 감시 On/Off 값(true, false)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 감시 On/Off 변경 결과(True/False)
    """
    try:
        body={ 'hostname':hostName, 'key': iKey, 'disable':str(isOff).lower() }
        logger.info( 'Set Item MonStatus, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, ZBM_URL['SetItemMonStatus']), METHOD, body, 5 )
        return getResponse( logger, response, 'Set Item MonStatus' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def _addTrigger( logger, isHost, target, iKey, tKey, triggerName, grade, conditions, dKey=None, dParam=None, _ip=DEF_HOST, _port=DEF_PORT, op_type=None, start_value=None, repeat=None):
    """
    - FUNC: zbms 로 One-Box 별로, 또는 템플릿 별로 감시항목에 임계치를 추가 요청
    - INPUT
        logger(M): 로그 기록 객체
        isHost(M): 추가할 임계치가 One-Box 별로인지, 템플릿  별로인지 구분(True/False)
        target(M): 임계치 추가할 One-Box 또는 템플릿 ID
        iKey(M): 임계치 추가할 감시항목 구분 Key(zabbix의 Item Key)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        triggerName(M): 장애 상세에 표시할 데이터(zabbix의 Trigger Name)
        grade(M): 임계치 등급(zabbix의 Trigger Grade)
        conditions(M): 임계치 조건문(zbms Trigger Condition)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        dParam(O): Discovery 감시항목일 경우 탐색 항목(object)을 Item 이름에 표시하기 위한 macro 입력(zabbix의 Discovery Macro)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 추가 결과(True/False)
    """
    try:
        if isHost:
            body = { 'hostname': target }
        else:
            body = { 'template_name': target }
        url = ''
        if dKey == None:
            body['key'] = iKey
            body['trigger_name'] = triggerName
            body['conditions'] = conditions
            body['repeat'] = str(repeat)
            body['op_type'] = op_type
            body['start_value'] = start_value
            body['grade'] = grade
            body['comments'] = tKey
            url = ZBM_URL['AddTrigger']
        else:
            body['discovery_key'] = dKey
            body['item_prototype'] = {
                                      'key':iKey,
                                      'trigger':{
                                                 'comments': tKey,
                                                 'grade': grade,
                                                 'conditions': conditions,
                                                 'repeat': str(repeat),
                                                 'op_type': op_type,
                                                 'start_value': start_value,
                                                 'name': triggerName + ' - ' + dParam
                                                 }
                                      }
            url = ZBM_URL['AddTriggerProto']
        
#         if isHost:  logger.info( 'Add Host Trigger, info=%s'%str(body) )
#         else:       logger.info( 'Add Template Trigger, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        if isHost:  return getResponse( logger, response, 'Add Host Trigger' )
        else:       return getResponse( logger, response, 'Add Template Trigger' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def addTrigger( logger, isHost, target, iKey, tKey, triggerName, grade, conditions, repeat, dKey=None, dParam=None, _ip=DEF_HOST, _port=DEF_PORT, op_type=None, start_value=None ):
    """
    - FUNC: zbms 로 One-Box 별로, 또는 템플릿 별로 감시항목에 임계치를 추가 요청(zbms 용 장애등급 및 임계치로 변경)
    - INPUT
        logger(M): 로그 기록 객체
        isHost(M): 추가할 임계치가 One-Box 별로인지, 템플릿  별로인지 구분(True/False)
        target(M): 임계치 추가할 One-Box 또는 템플릿 ID
        iKey(M): 임계치 추가할 감시항목 구분 Key(zabbix의 Item Key)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        triggerName(M): 장애 상세에 표시할 데이터(zabbix의 Trigger Name)
        grade(M): 임계치 등급(warning, minor, major, critical)
        conditions(M): 임계치 조건문(zbms 용 parameter로 변경)
        repeat(M): 장애 발생하기 위한 임계치 위반 반복수(zbms 용 parameter로 변경)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        dParam(O): Discovery 감시항목일 경우 탐색 항목(object)을 Item 이름에 표시하기 위한 macro 입력(zabbix의 Discovery Macro)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 추가 결과(True/False)
    """
    return _addTrigger(logger, isHost, target, iKey, tKey, triggerName, alertGradeToZB(grade), makeZbCondition( conditions), dKey, dParam, _ip, _port, op_type=op_type, start_value=start_value, repeat=repeat)

def addTemplateTrigger( logger, targetSeq, iKey, tKey, triggerName, grade, conditions, repeat, dKey=None, dParam=None, _ip=DEF_HOST, _port=DEF_PORT, op_type=None, start_value=None):
    """
    - FUNC: zbms 로 템플릿 별로 감시항목에 임계치를 추가 요청
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 임계치 추가할 감시대상 Sequence(zabbix 템플릿 ID)
        iKey(M): 임계치 추가할 감시항목 구분 Key(zabbix의 Item Key)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        triggerName(M): 장애 상세에 표시할 데이터(zabbix의 Trigger Name)
        grade(M): 임계치 등급(warning, minor, major, critical)
        conditions(M): 임계치 조건문(Trigger 구분 Key로 사용)
        repeat(M): 장애 발생하기 위한 임계치 위반 반복수(Trigger 구분 Key로 사용)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        dParam(O): Discovery 감시항목일 경우 탐색 항목(object)을 Item 이름에 표시하기 위한 macro 입력(zabbix의 Discovery Macro)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 추가 결과(True/False)
    """
    return addTrigger(logger, False, targetSeq, iKey, tKey, triggerName, grade, conditions, repeat, dKey, dParam, _ip, _port, op_type=op_type, start_value=start_value)

def addHostTrigger( logger, hostName, iKey, tKey, triggerName, grade, conditions, repeat, dKey=None, dParam=None, _ip=DEF_HOST, _port=DEF_PORT, op_type=None, start_value=None):
    """
    - FUNC: zbms 로 One-Box 별로 감시항목에 임계치를 추가 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): 임계치 추가할 One-Box ID(zabbix host ID)
        iKey(M): 임계치 추가할 감시항목 구분 Key(zabbix의 Item Key)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        triggerName(M): 장애 상세에 표시할 데이터(zabbix의 Trigger Name)
        grade(M): 임계치 등급(warning, minor, major, critical)
        conditions(M): 임계치 조건문(Trigger 구분 Key로 사용)
        repeat(M): 장애 발생하기 위한 임계치 위반 반복수(Trigger 구분 Key로 사용)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        dParam(O): Discovery 감시항목일 경우 탐색 항목(object)을 Item 이름에 표시하기 위한 macro 입력(zabbix의 Discovery Macro)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 추가 결과(True/False)
    """
    return addTrigger(logger, True, hostName, iKey, tKey, triggerName, grade, conditions, repeat, dKey, dParam, _ip, _port, op_type=op_type, start_value=start_value)

def delHostTrigger( logger, hostName, tKey, iKey, dKey=None, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box 별로 감시항목에 임계치 제거 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): 임계치 제거할 One-Box ID(zabbix host ID)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        iKey(M): 임계치 제거할 감시항목 구분 Key(zabbix의 Item Key)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 제거 결과(True/False)
    """
    try:
        body = { 'hostname': hostName }
        url = ''
        if dKey == None:
            body['key'] = iKey
            body['comments'] = tKey
            url = ZBM_URL['DelTrigger']
        else:
            body['discovery_key'] = dKey
            body['item_prototype'] = {
                                      'key':iKey,
                                      'trigger':{ 'comments': tKey }
                                      }
            url = ZBM_URL['DelTriggerProto']
        
#         logger.info( 'Del HostTrigger, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        return getResponse( logger, response, 'Del HostTrigger' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def modHostTrigger( logger, hostName, tKey, iKey, newConditions, newRepeat, grade, dKey=None, _ip=DEF_HOST, _port=DEF_PORT, op_type=None, start_value=None):
    """
    - FUNC: zbms 로 One-Box 별로 감시항목에 임계치 변경 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): 임계치 변경할 One-Box ID(zabbix host ID)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        iKey(M): 임계치 변경할 감시항목 구분 Key(zabbix의 Item Key)
        newConditions(M): 변경할 임계치 데이터(zabbix의 Trigger Condition)
        newRepeat(M): 변경할 임계치 반복수(zabbix의 Trigger repeat)
        grade(M): 변경되는 임계치 등급(zabbix의 Trigger Grade)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 변경 결과(True/False)
    """
    try :
        body = { 'hostname':hostName }
        url = ''
        if dKey == None:
            body['key'] = iKey
            body['comments'] = tKey
            body['repeat'] = str(newRepeat)
            body['op_type']= op_type
            body['start_value'] = start_value
            body['conditions'] = makeZbCondition(newConditions)
            body['grade'] = alertGradeToZB(grade)
            url = ZBM_URL['ModTrigger']
        else:
            body['discovery_key'] = dKey
            body['item_prototype'] = {
                                      'key':iKey,
                                      'trigger':{ 'comments': tKey,
                                                  'grade': alertGradeToZB(grade),
                                                  'repeat': str(newRepeat),
                                                  'op_type': op_type,
                                                  'start_value': start_value,
                                                  'conditions': makeZbCondition(newConditions)}
                                      }
            url = ZBM_URL['ModTriggerProto']
            
        logger.info( 'Mod HostTrigger, info=%s'%str(body) )
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        return getResponse( logger, response, 'Mod HostTrigger' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
    
    return False

def setTemplateTriggerStatus( logger, hostName, tKey, iKey, isOn, grade, dKey=None, dList=None, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box 별로 템플릿에 의해 기본으로 감시되는 임계치 상태(On/Off) 변경
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): 임계치 변경할 One-Box ID(zabbix host ID)
        tKey(M): 임계치 구분할 ID 성 데이터(zabbix의 Trigger Comments)
        iKey(M): 임계치 변경할 감시항목 구분 Key(zabbix의 Item Key)
        isOn(M): 임계치 사용 여부(True/False)
        grade(M): 변경되는 임계치 등급(zabbix의 Trigger Grade)
        dKey(O): Discovery 감시항목일 경우 Discovery Key 입력(zabbix의 Discovery Key)
        dList(O): Discovery 감시항목일 경우 Discovery 탐색(object) 리스트 입력(zabbix의 Discovery ItemProto key 생성에 사용)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 임계치 상태 변경 결과(True/False)
    """
    try :
        body = { 'hostname':hostName  }
        url = ''
        if dKey == None:
            body['key'] = iKey
            body['comments'] = tKey
            body['is_enable'] = str(isOn).lower()
            body['grade'] = alertGradeToZB(grade)
            url = ZBM_URL['ModTrigger']
            
            logger.info( 'Set TriggerInst, info=%s'%str(body) )
            response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
            return getResponse( logger, response, 'Set TriggerInst' )
        else:
            body['discovery_key'] = dKey
            body['item_prototype'] = {
                                      'key':iKey,
                                      'trigger':{ 'comments': tKey,
                                                  'grade': alertGradeToZB(grade),
                                                  'is_enable': str(isOn).lower()}
                                      }
            url = ZBM_URL['ModTriggerProto']
            
            logger.info( 'Set TriggerInst, info=%s'%str(body) )
            response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
            if getResponse( logger, response, 'Set TriggerInst' ) != True :
                return False
            else:
                if dList == None or len(dList) < 1:
                    dList = []
                
                for info in dList:
                    body = { 'hostname':hostName  }
                    body['key'] = str(iKey).split('[')[0] + '[%s]'%str(info)
                    body['comments'] = tKey
                    body['is_enable'] = str(isOn).lower()
                    body['grade'] = alertGradeToZB(grade)
                    url = ZBM_URL['ModTrigger']
                    
                    logger.info( 'Set TriggerInst, info=%s'%str(body) )
                    response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
#                     if getResponse( logger, response, 'Set TriggerInst' ) != True:
#                         return False
                return True
                
    except Exception, e:
        logger.fatal(e)
    
    return False

def delTemplateItem( logger, targetSeq, iKey, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 감시대상(템플릿) 별로 감시항목 제거 요청
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 제거할 감시대상(zabbix 템플릿 ID)
        iKey(M): 감시항목 구분 Key(zabbix의 Item Key)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 제거 결과(True/False)
    """
    try:
        body = { 'template_name': str(targetSeq),
                 'key': iKey }
        url = ZBM_URL['DelTemplateItem']
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        return getResponse( logger, response, 'Del ZB Template Item' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
        return False

def addTemplateItem( logger, targetSeq, itemInfo, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 감시대상(템플릿) 별로 감시항목 추가 요청
    - INPUT
        logger(M): 로그 기록 객체
        targetSeq(M): 추가할 감시대상(zabbix 템플릿 ID)
        itemInfo(M): 감시항목 데이터(zabbix의 Item)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 추가 결과(True/False)
    """
    iKey = None
    try:
        ## Item 추가
        body = itemInfo
        body['template_name'] = str(targetSeq)
        url = ZBM_URL['AddTemplateItem']
        
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        ret = getResponse( logger, response, 'Add ZB Template Item' )
        if not ret:
            return ret
        iKey = itemInfo['key']
        logger.info( 'Add ZB Template Item, info=%s'%str(body) )
        
        ## Tigger 추가
        trgList = itemInfo['trigger']
        for trgInfo in trgList:
            ret = _addTrigger(logger, False, targetSeq, itemInfo['key'], trgInfo['comments'], 
                              trgInfo['name'], trgInfo['grade'], trgInfo['conditions'])
            if not ret:
                delTemplateItem( logger, targetSeq, itemInfo['key'] )
                return ret
        
        logger.info( 'succ: ADD ZB Template Item, info=%s'%str(body) )
        return True
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        if iKey != None :
            delTemplateItem( logger, targetSeq, iKey )
        logger.fatal(e)
        return False

def delHostItem( logger, hostName, iKey, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box 별로 감시항목 제거 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix 호스트 ID)
        iKey(M): 감시항목 Key(zabbix의 Item Key)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 감시항목 제거 결과(True/False)
    """
    try:
        body = { 'hostname': str(hostName),
                 'key': iKey }
        url = ZBM_URL['DelHostItem']
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        return getResponse( logger, response, 'Del ZB Host Item' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
        return False
    
def delHostDiscovery( logger, hostName, dKey, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: zbms 로 One-Box 별로 Discovery 제거 요청
    - INPUT
        logger(M): 로그 기록 객체
        hostName(M): One-Box ID(zabbix 호스트 ID)
        dKey(M): Discovery Key(zabbix의 Discovery Key)
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : Discovery 제거 결과(True/False)
    """
    try:
        body = { 'hostname': str(hostName),
                 'key': dKey }
        url = ZBM_URL['DelHostDisc']
        response = rest_api.sendReq( HEADER, 'http://%s:%s%s'%(_ip, _port, url), METHOD, body, 5 )
        return getResponse( logger, response, 'Del ZB Host Discovery' )
    except SockErr, e:
        handleSock(logger, e)
        return False
    except Exception, e:
        logger.fatal(e)
        return False




def faultParsing( _body, dbm, logger ):
    """
    - FUNC: Zabbix 장애 메시지를 Orch-M에 필요한 정보로 가공
    - INPUT
        _body(M): Zabbix 로부터 받은 장애 Noti 메시지(zb 서버에 alertScript로 등록되어 있음)
        dbm(M): DB Connection 객체
        logger(M): 로그 기록 객체
    - OUTPUT : Orch-M에 필요한 장애 데이터로 가공(itemSeq, itemVal, alertGrade, isAlert, trig_name, dttm)
    """
    svrOBID = itemSeq = itemVal = alertGrade = itemStatus = trig_name = dttm = None
    ret = {}
    
    try:
        body = dict( _body )

        svrOBID = body['body']['host']['name']
        alertGrade = int(body['body']['trigger']['grade_code'])
        itemStatus = body['body']['trigger']['status_code']
        strDate = body['body']['event']['date'] + " " + body['body']['event']['time']
        trig_name = body['body']['trigger']['name']
        dttm = datetime.strptime(strDate, "%Y.%m.%d %H:%M:%S")

        isLineStatus = False
        if body['body'].has_key( 'isLineStatus' ) :
            isLineStatus = body['body']['isLineStatus']
        
        item = body['body']['item'][0]
        itemKey = item['key']
        # 21. 4.26 - lsh
        # RTT 관련 가상 Item 추가.
        # 가상 Item 을 RTT Item 인것처렴 변경, 예) 9.linux.net.ping.calc
        itemKey = itemKey.replace('.calc', '')

        # fortinet 설치 후, 첫 장애 알람은 오지 않게 하자
        # wan total, active 수집 시간차에 따른 알람이 오는 경우
        if itemKey.find('wanactive.sh') > -1 :
            import redis
            redis = redis.Redis(host=cfg['zb_ip'], port=6379, db=2)
            redisVal = redis.get('%s.event' % str(svrOBID))

            # logger.debug("redisVal = %s" %str(redisVal))

            if redisVal > 0:
                redis.delete('%s.event' % str(svrOBID))

                redis.close()
                return True, None

            redis.close()

        instItemSeq_Query = db_sql.GET_ITEMINSTANCE_SEQ_BY_HOST_KEY(svrOBID, itemKey)
        
        dic = dbm.select(instItemSeq_Query)
#         logger.debug(dic)
        
        if len(dic) > 1 :
#             logger.error(instItemSeq_Query)
            logger.error( "ZBM_API: Duplicated Item Key, ob=%s, key=%s"%(svrOBID, itemKey) )
            return False, None
        
        if len(dic) < 1 :
#             logger.warning(instItemSeq_Query)
            logger.warning( "ZBM_API: No Item Key, ob=%s, key=%s"%(svrOBID, itemKey) )
            return True, None
        
        itemSeq = dic[0]['itemseq']
        itemMonitorYN = str(dic[0]['monitoryn']).lower()
        itemDisplayYN = str(dic[0]['displayyn']).lower()
        itemValue = item['value']
        
        if itemMonitorYN == 'n' or itemDisplayYN == 'n':
            logger.warning( 'ZBM_API: Ignored Item, key=%s, monitoring=%s, display=%s'%( itemKey, itemMonitorYN, itemDisplayYN ) )
            return True, None
        
        try:
            itemVals = str(itemValue).split(' ')
            # itemVal = float(itemVals[0])
            # 2017.04.13 itemVal 처리 수정요청 김승주전임
            itemVal = str(itemVals[0]).strip()
        except Exception, e:
            logger.error( "ZBM_API: Invalid Data, item key=%s, Value=%s"%(itemKey, str(itemValue)) )
            logger.fatal(e)
            return False, None
        
    except Exception, e:
        logger.fatal(e)
        return False, None
    
    isAlert = True
    if int(itemStatus) == 0 :
        isAlert = False
    
    ret['itemSeq'] = itemSeq
    ret['itemVal'] = itemVal
    ret['alertGrade'] = alertGrade
    ret['isAlert'] = isAlert
    ret['trig_name'] = trig_name
    ret['dttm'] = dttm
    ret['isLineStatus'] = isLineStatus
#     logger.debug(ret)
    return True, ret



def reqPerfHistPerPeriod( dataType, hostName, stime, etime, key, period, unit, zbDbm, logger ):
    """
    - FUNC: Zabbix DB에서 요청한 시간동안의 데이터를 특정 주기로 평균내서 반환
    - INPUT
        dataType(M): AVG/MAX
        hostName(M): 성능 조회할 One-Box ID(zabbix 호스트 ID)
        stime(M): 성능 조회 Start 시간(DTTM)
        etime(M): 성능 조회 End 시간(DTTM)
        period(M): 평균내기 위한 시간간격(초)
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
    - OUTPUT : 성능 데이터 리스트 반환(평균 값, 시간)
    """
    res = {}
    if unit == '' :
        unit = None
    res['unit'] = unit
    
    result = []
    
    if dataType == 'AVG' :
        # getHistSql = db_sql.GET_ZBHIST_AVG_PER_PERIOD( hostName, key, period, stime, etime )
        getHistSql = db_sql.GET_ZBHIST_PER_PERIOD_2( hostName, key, period, stime, etime )
        zbPerfs = zbDbm.select( getHistSql )
        
        for zbPerf in zbPerfs:
            clock = zbPerf['clk']
            # value = zbPerf['val']
            # result.append({'value':str(value), 'clock':str(clock)})
            day = zbPerf['day']
            max_value = zbPerf['max_val']
            avg_value = zbPerf['avg_val']
            result.append({'day':day, 'max_value':str(max_value), 'avg_value':str(avg_value), 'clock':str(clock)})


    elif dataType in [ 'DETAIL', 'TRENDS' ] :
        if dataType == 'DETAIL' :
            getHistSql = db_sql.GET_ZBHIST_PER_PERIOD_DETAIL( hostName, key, period, stime, etime )
        else :
            getHistSql = db_sql.GET_ZBHIST_PER_PERIOD_TRENDS( hostName, key, period, stime, etime )    
        zbPerfs = zbDbm.select( getHistSql )
        for zbPerf in zbPerfs:
            clock = datetime.fromtimestamp(zbPerf['clk']).strftime('%Y-%m-%d %H:%M:%S')
            # clock = zbPerf['clk']

            # 2019.10.25 - KT 요구사항, 네트워크 트래픽은 Mbps 로 표현. (소수 2째자리)
            # Zabbix Key 에 RX, TX 가 있으면 네트워크 트래픽이라 조건걸음
            
            # fortinet 관련 RX, TX 대문자 비교 추가
            key = key.upper()
            if key.find ('TX') > 0 or key.find ('RX') > 0 :
                max_value = round ( zbPerf['max_val'] / 1024 / 1024, 2 )
                avg_value = round ( zbPerf['avg_val'] / 1024 / 1024, 2 )
                min_value = round ( zbPerf['min_val'] / 1024 / 1024, 2 )
            else :                    
                max_value = zbPerf['max_val']
                avg_value = zbPerf['avg_val']
                min_value = zbPerf['min_val']
            result.append({'max_value':str(max_value), 'avg_value':str(avg_value), 'min_value':str(min_value), 'clock':str(clock)})


    #elif dataType == 'MAX' :
    #    getHistSql = db_sql.GET_ZBHIST_MAX_PER_PERIOD( hostName, key, period, stime, etime )

    else:
        return False, 'Unknown Perf Data Type, type=%s'%str(dataType)
    
        

    res['perf_list'] = result
    return True, res


def _reqPerfHist( dataType, svrUuid, itemSeq, sTime, eTime, period, dbm, zbDbm, logger ):
    try:
        instItemSeq_Query = db_sql.GET_ITEMINSTANCE_KEY_BY_HOST_ITEM(svrUuid, str(itemSeq) )
        
        dic = dbm.select(instItemSeq_Query)
        if len(dic) < 1:
            logger.error("No Key(host=%s, item=%s)"%(svrUuid, str(itemSeq)))
            return False, 'No ItemInst Key, svr=%s, itemSeq=%s'%(svrUuid, str(itemSeq))
        
        key = dic[0]['itemkey']
        unit = dic[0]['unit']
        svrOBID = dic[0]['onebox_id']
        
        if dataType in [ 'AVG', 'DETAIL', 'TRENDS' ] :
            isSucc, ret = reqPerfHistPerPeriod( dataType, svrOBID, sTime, eTime, key, period, unit, zbDbm, logger )
            if not isSucc :
                return False, ret
            
            return True, ret
        elif dataType == 'MAX':
            isSucc, ret = reqPerfHistPerPeriod( dataType, svrOBID, sTime, eTime, key, period, unit, zbDbm, logger )
            if not isSucc :
                return False, ret
            
            return True, ret
        else:
            return False, 'Unknown Perf Data Type, type=%s'%str(dataType)
    except SockErr, e:
        handleSock(logger, e)
        return False, 'SockException, e=%s'%str(e)
    except Exception, e:
        logger.fatal(e)
        return False, 'Exception, e=%s'%str(e)
    

def reqPerfData( req, period, dbm, zbDbm, logger, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: Zabbix의 성능 데이터 요청(그래프->URL, 데이터->DB)
    - INPUT
        req(M): 요청 Parameter(svr_uuid, itemseq, datatype, stime, etime)
        period(M): 평균내기 위한 시간간격(초)
        dbm(M): DB Connection 객체
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 성능 조회 결과 반환(그래프 파일, 데이터 리스트)
    """
    try:
        instItemSeq_Query = db_sql.GET_ITEMINSTANCE_KEY_BY_HOST_ITEM(req['svr_uuid'], str(req['itemseq']) )
        
        dic = dbm.select(instItemSeq_Query)
        if len(dic) < 1:
            logger.error("No Key(host=%s, item=%s)"%(req['svr_uuid'], str(req['itemseq'])))
            return False, 'No ItemInst Key, svr=%s, itemSeq=%s'%(req['svr_uuid'], str(req['itemseq']))
        
        key = dic[0]['itemkey']
        svrOBID = dic[0]['onebox_id']
        data_type = str(req['datatype']).upper()

        if data_type == "GRAPH":
            sTime = int( time.mktime( datetime.strptime(req["stime"], "%Y-%m-%d %H:%M:%S").timetuple() ) )*1000
            eTime = int( time.mktime( datetime.strptime(req["etime"], "%Y-%m-%d %H:%M:%S").timetuple() ) )*1000
            
            body = { "hostname":svrOBID, "key": key, "stime":str(sTime), "etime":str(eTime) }
            
            zbmUrl = "http://%s:%s/GraphService/getGraph"%(_ip, _port)
            response = rest_api.sendReq( HEADER, zbmUrl, METHOD, body, 5 )
            
            logger.debug(response)
            if response != None and response.code == 200:
                return True, response.buffer.read()
            else:
                return False, 'HTTP Error, err=%s'%str(response)

        elif data_type in [ "DETAIL", "TRENDS" ] : 
            return _reqPerfHist(data_type,  req["svr_uuid"], req['itemseq'], req["stime"], req["etime"], period, dbm, zbDbm, logger)

        else:
            return _reqPerfHist('AVG', req["svr_uuid"], req['itemseq'], req["stime"], req["etime"], period, dbm, zbDbm, logger)
    except SockErr, e:
        handleSock(logger, e)
        return False, 'SockException, e=%s'%str(e)
    except Exception, e:
        logger.fatal(e)
        return False, 'Exception, e=%s'%str(e)

def reqPerfMaxData( req, period, dbm, zbDbm, logger ):
    return _reqPerfHist('MAX', req["svr_uuid"], req['itemseq'], req["stime"], req["etime"], period, dbm, zbDbm, logger)

    
def reqCurrData( period, expirePeriod, zbDbConn, dbConn, logger ):
    """
    - FUNC: Zabbix로부터 최신 데이터를 조회하고 DB저장
    - INPUT
        period(M): 최신 데이터 조건(ZB DB 조회 시 period + 감시항목 감시 주기 내에 있는 데이터만 조회)
        expirePeriod(M): 만료 처리 주기(활성화 결정)
        dbConn(M): DB Connection 객체
        zbDbConn(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
    - OUTPUT : 성공일 경우 최신데이터 업데이트 개수를 반환하고, 실패일 경우 에러 반환
    """
    try :

        ## 감시 중인 서버 정보 조회
        # 속도 측정용
        logger.info ( " reqCurrData Start ===> %s " % datetime.now().strftime("%Y.%m.%d %H:%M:%S.%f") )

        # 2021. 6. 8 - lsh
        # 장비별 실시간 값을 조회하던것을, 모든 장비의 실시간 값 가져오는것으로 변경.
        keyListSql = db_sql.GET_ITEM_KEY_ALL()

        cur = dbConn.cursor()
        cur.execute( keyListSql )
        selectedNum = 0
            
        zbCur = zbDbConn.cursor()

        ## Item 주기 및 Key 정보 조회
        # logger.info("%s : GET_ITEMKEY_LIST_BY_SERVER : %s " % ( datetime.now().strftime("%H:%M:%S"), str(svrSeq) ) )

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        if len(rows) < 1 :
            logger.debug( "RealTimePerf: No Server Info" )
            cur.close()
            return True, selectedNum

        ## Item 주기 별 성능 정보 조회를 위한 dict 생성
        itemPeriodKey = {}

        for row in rows:
            d = dict(zip(columns, row))
            if not itemPeriodKey.has_key( d['period']) :
                itemPeriodKey[d['period']] = []
            itemPeriodKey[d['period']].append(d['item_key'])
        
        if len(itemPeriodKey) < 1:
            logger.error( "RealTimePerf Fail: No Item Key Info" )
            return True, selectedNum

        ## 감시 주기 별 zabbix 성능 조회
        columns = None
        rows = []
        for _period in itemPeriodKey.keys():
            _icmp = False

            # icmpping[] 이 통째로 조회되어 주기가 다른 장비일 경우 상황판에 한번에 사라졌다가 나타났다 반복함
            # 하단에 주기값을 조건으로 쿼리를 추가하기 위해 icmppingp[] 을 일단 itemPeriodKey 목록에서 제거
            if 'icmpping[]' in itemPeriodKey[_period]:
                itemPeriodKey[_period].remove('icmpping[]')
                _icmp = True

            itemKeyList = ''
            if len(itemPeriodKey[_period]) > 1 :
                itemKeyList = str( tuple(itemPeriodKey[_period]) )
            elif len(itemPeriodKey[_period]) == 1:
                itemKeyList = """('%s')"""%str(itemPeriodKey[_period][0])
            else :
                continue

            # ZB에서 모니터값 가져오기
            # 2017. 11.15 - lsh
            # 쿼리 성능개선을 위해 UNIX TIME 을 계산해서 인자로 던진다.
            utime=int(time.time()) - ( int(period)+int(_period) )
            getHistSql = db_sql.GET_ZBDB_CURR_HIST( itemKeyList, str(utime ))
            # logger.info("getHistSql = %s" %str(getHistSql))

            # 2019. 3.28 - lsh, 쿼리에 None list 가 들어간다.
            # INFO:orchm:itemKeyList : (None, '90.UTM.vnet.ConnTrack', '90.UTM.vnet.VPNCount', '90.UTM.vnet.VPN_TotalTunnel', '90.UTM.vnet.VPN_ActiveTunnel', '90.UTM.vnet.Rx_Rate[eth0]', '90.UTM.vnet.Tx_Rate[eth0]', '90.UTM.vnet.Rx_Rate[eth1]', '90.UTM.vnet.Tx_Rate[eth1]')
            # getHistSql = getHistSql.replace ('None,', '')

            zbCur.execute( getHistSql )
            columns = [desc[0] for desc in zbCur.description]
            rows += zbCur.fetchall()

            # 주기 값에 따른 icmpping 을 별도로 조회하여 rows 에 추가한다
            if _icmp:
                itemKeyList = "('icmpping[]')"
                getHistSql = db_sql.GET_ZBDB_CURR_HIST_ICMPPING(itemKeyList, str(utime), str(_period))
                # logger.info("getHistSql = %s" % str(getHistSql))
                zbCur.execute(getHistSql)
                rows += zbCur.fetchall()

        selectedNum = len( rows )

        #logger.info ( " columns : %s ", str(columns)  )
        #logger.info ( " rows : %s ", str(rows)  )

        ## 조회한 성능 데이터를 저장하고 만료 기간이 넘어간 것은 비활성화로 변경
        i = 0
        union_count = 0
        sub_query = ''
        # 18.01.29 - lsh
        # Zabbix 모니터값을 여러번 insert 하던것을 한번에 하도록 수정.
        for row in rows:
            d = dict(zip(columns, row))
            sub_query += "SELECT '%s'::text AS host_name, '%s'::text AS item_key , %s AS clock, '%s'::text AS val \n" % (  d['host_name'], d['item_key'] , str(d['clock']), str(d['value']) )

            i += 1
            union_count += 1

            # 상용에 한방에 UNION 은 부담스럽다. 100개씩 나누어 Insert ...
            if union_count == 100 :
                strsql = db_sql.UPDATE_REALTIMEPERF_NEW( str(expirePeriod), sub_query)
                #logger.info ( " UPDATE_REALTIMEPERF_NEW strsql  ===> %s  %s " % ( datetime.now().strftime("%Y.%m.%d %H:%M:%S"), strsql) )
                cur.execute( strsql )
                sub_query = ''                
                union_count = 0
            elif i < len(rows) :
                sub_query += " UNION \n"


        if  sub_query <> '' :
            # UNION 으로 조립된 쿼리 실행
            strsql = db_sql.UPDATE_REALTIMEPERF_NEW( str(expirePeriod), sub_query)
            #logger.info ( " UPDATE_REALTIMEPERF_NEW strsql  ===> %s  %s " % ( datetime.now().strftime("%Y.%m.%d %H:%M:%S"), strsql) )
            cur.execute( strsql )

        logger.info(" reqCurrData End ===> %s " % datetime.now().strftime("%Y.%m.%d %H:%M:%S.%f"))

        ## 만료된 항목 비활성화로 변경
        # logger.info ( "UPDATE_REALTIMEPERF_FOR_EXPIRE : %s " % str(expirePeriod) )

        # 2022. 2.14 - lsh 
        # 삭제시간이 너무 빨라, 상황판에 안보이는 경우 발생 60초 여유 줌
        updateStateSql = db_sql.UPDATE_REALTIMEPERF_FOR_EXPIRE(str(60+expirePeriod))
        # logger.info("expirePeriod = %s" % str(60+expirePeriod))
        # logger.info("updateStateSql = %s" % str(updateStateSql))
        cur.execute(updateStateSql)

        ## 사용하지 않는 감시 항목 제거
        remSql = db_sql.REMOVE_REALTIME_ITEM_UNUSED()
        cur.execute(remSql)

        cur.close()
        zbCur.close()
        
    except psycopg2.DatabaseError, e:
        logger.fatal(e)
        zbCur.close()
        cur.close()
        return False, 'DB Exception, e=%s'%str(e)
    
    return True, selectedNum

def getAlarmList(zbDbm, logger):
    """
    - FUNC: Zabbix로부터 장애 발생 중인 항목 리스트 가져옴
    - INPUT
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
    - OUTPUT : 성공일 경우 장애 데이터를 반환하고, 실패일 경우 에러 반환
    """
    try:
        ret = zbDbm.select( db_sql.GET_ZB_ALARM() )
        if ret == None :
            logger.error('DB Fail to Get ZB Alarm List')
            return False, 'DB Fail to Get ZB Alarm'
        
        return True, ret
    except Exception, e:
        logger.fatal(e)
        return False, 'Exception, e=%s'%str(e)


class PerfHistCollector(threading.Thread):
    """
    - FUNC: 주기적으로 Zabbix로부터 최신 데이터를 조회하고 DB저장하는 thread 생성
    - INPUT
        cfg(M): zabbix와 orch-M DB 연결 정보, 성능 조회 주기, 성능 데이터 만료 기간 정보
            zb_perfhist_period, zb_perfhist_expire,
            zb_db_name, zb_db_user, zb_db_passwd, zb_db_addr, zb_db_port,
            db_name, db_user, db_passwd, db_addr, db_port
        logger(M): 로그 기록 객체
    - OUTPUT : 
    """
    def __init__(self, cfg, logger ):
        threading.Thread.__init__(self)
        self.logger = logger
        self.cfg = cfg
        self.period = cfg['zb_perfhist_period']
        self.expire = cfg['zb_perfhist_expire']
        self.dbConn = db_mng.makeDbConn(cfg)
        self.zbDbConn = db_mng.makeZbDbConn(cfg)
    
    def run(self):
        """
        - FUNC: 주기적으로 Zabbix로부터 최신 데이터를 조회하고 DB저장
        """
        self.logger.info('ZB Performance History Collector Run.')
        
        while True:
            try:
                
                if self.zbDbConn.closed :
                    self.zbDbConn = db_mng.makeZbDbConn( self.cfg )
                    
                if self.dbConn.closed :
                    self.dbConn = db_mng.makeDbConn( self.cfg )
                
                reqCurrData( self.period, self.expire, self.zbDbConn, self.dbConn, self.logger )
                sleep(self.period)
            except Exception, e:
                sleep(self.period)
                self.logger.warn("ZB Performance History Collector: Exception Occur.")
                self.logger.fatal(e)
        
        self.logger.error('ZB Performance History Collector Stop!!!')


class ZBMConnThread(threading.Thread):
    """
    - FUNC: 주기적으로 zbms 연결 상태 확인 및 재연결하는 클래스
    - INPUT
        cfg(M): orch-m 공동 공유 파일, zbms 인증/연결확인 url, 연결확인 주기, 재연결 주기, zabbix 계정정보, zabbix url
        logger(M): 로그 기록 객체
    - OUTPUT : zbms 연결관리 객체
    """
    
    isConn = False
    conn_data_chk_period = 5
    
    def __init__(self, cfg, logger ):
        threading.Thread.__init__(self)
        self.zbmAuthUrl = "http://" + cfg['zbm_ip'] + ":" + str(cfg['zbm_port']) + cfg['zbm_url']['auth']
        self.zbmChkUrl = "http://" + cfg['zbm_ip'] + ":" + str(cfg['zbm_port']) + cfg['zbm_url']['chk']
        self.conn_chk_period = cfg['zbm_conn_chk_period']
        self.reconn_period = cfg['zbm_reconn_period']
        self.id = cfg['zb_id']
        self.passwd = cfg['zb_passwd']
        self.jsonUrl = cfg['zb_jsonurl']
        self.graphUrl = cfg['zb_graphurl']
        self.logger = logger
        logger.info('ZBMConnMng : ZBMAuthUrl=%s, ZBMChkUrl=%s, ZBM_ConnChk_Period=%s, ZB_ID=%s, ZB_JsonUrl=%s, ZB_GraphUrl=%s'
                %(cfg['zbm_url']['auth'], cfg['zbm_url']['chk'], str(cfg['zbm_conn_chk_period']), cfg['zb_id'], cfg['zb_jsonurl'], cfg['zb_graphurl']) )

    
    def run(self):
        """
        - FUNC: 주기적으로 zbms 연결 상태를 확인하고 끊겼을 경우 재연결 요청
        """
        self.logger.info( "Zabbix ConnectionManager Thread Start" )
        self.connZbm(self.reconn_period)
        while True :
            try:
                self.checkConn(self.conn_chk_period)
                
                if self.isConn == False:
                    self.logger.info("trying to reconnect ZBM:" + self.zbmAuthUrl )
                    self.connZbm(self.reconn_period)
                    sleep(2)
                else:
                    sleep(2)
            except Exception, e:
                self.logger.error('Zabbix ConnectionManager Exception')
                self.logger.fatal(e)
                sleep(self.reconn_period)
            
        self.logger.error( "Zabbix Connecti:qonManager Thread Destroy!!!" )
    
    def connZbm(self, retryPeriod):
        """
        - FUNC: zbms과 연결을 시도하며 실패 시 성공될 때까지 주기적으로 재시도
        - INPUT
            retryPeriod(M): 연결 실패 시 재시도하는 주기
        """
        while True :
            try:
                
                body = {"zabbix_user":self.id, "zabbix_pwd": self.passwd, "jsonurl":self.jsonUrl, "graphurl": self.graphUrl}

                self.logger.info ( 'BODY : %s' % body)

                response = rest_api.sendReq( HEADER, self.zbmAuthUrl, METHOD, body, 5 )
                if response == None or response.body == None:
                    self.logger.error("ZBM Connection Fail: %s"%str(response))
                    web_api.notiWeb("ZBM Connection Fail", "No Response Body")
                    self.isConn = False
                    gVar.locked_write_param(GVAR_RELEASE, 'y')
                    sleep(retryPeriod)
                else:
                    _body = json.loads(response.body)
                    if _body.has_key('result') :
                        self.isConn = True
                        gVar.locked_write_param(GVAR_RELEASE, 'n')
                        # self.logger.info("ZBM Connected: %s"%str(response.body))
                        return
                    else:
                        self.logger.error("ZBM Connection Fail: %s"%str(response.body))
                        web_api.notiWeb("ZBM Connection Fail", _body)
                        gVar.locked_write_param(GVAR_RELEASE, 'y')
                        self.isConn = False
                        sleep(retryPeriod)
            except Exception, e:
                self.logger.error("ZBM Connection Fail: Exception")
                self.logger.fatal(e)
                self.isConn = False
                gVar.locked_write_param(GVAR_RELEASE, 'y')
                sleep(retryPeriod)
    
    def checkConn(self, connChkPeriod):
        """
        - FUNC: zbms과 API 연결 상태를 확인하고 확인하고 5초단위로 연결상태 데이터를 조회하여 연결상태 결정
        - INPUT
            connChkPeriod(M): API 연결 상태 확인 주기
        """
        try:
            body = {"chk":"chk"}
            response = rest_api.sendReq( HEADER, self.zbmChkUrl, METHOD, body, 5 )
            
            if response != None and response.body != None :
                _body = json.loads(response.body)
                if _body.has_key('error') and _body['error']['message'] != None :
                    self.isConn = True
                    self.logger.debug("ZBM Connection Check OK")
                    
                    duration = connChkPeriod
                    while True:
                        sleep(self.conn_data_chk_period)
                        duration = duration - self.conn_data_chk_period
                        if duration < 0 :
                            break
                        
                        isRelease = gVar.locked_read_param(GVAR_RELEASE)
                        if str(isRelease).lower() == 'y' :
                            self.logger.error( "ZBM Connection Check: ZBM Conn Release!!" )
                            gVar.locked_write_param(GVAR_RELEASE, 'y')
                            self.isConn = False
                            break
                        
                    return
            
            self.isConn = False
            gVar.locked_write_param(GVAR_RELEASE, 'y')
            self.logger.error("ZBM Connection Check Fail: %s"%str(response))
            web_api.notiWeb("ZBM Connection Check Fail", str(response))
        except Exception, e:
            self.isConn = False
            gVar.locked_write_param(GVAR_RELEASE, 'y')
            self.logger.fatal(e)
            web_api.notiWeb("ZBM Connection Check Exception", str(e))

class zbItemStateChecker(threading.Thread):
    """
    - FUNC: Zabbix Item State Checker
    - INPUT
        cfg(M): Orch-M 설정 정보
    """
    
    def __init__( self, cfg, logger ):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.logger = logger
        self.zbIP = cfg['zb_ip']
        self.zbPort = cfg['zb_port']
        self.zbSender = cfg['zb_sender']
        self.zbItemStateKey = cfg['zb_item_state_key']
        self.itemChkPeriod = cfg['zb_item_state_period']
        
    
    def run(self):
        import subprocess
        sleep(10)
        
        cur = None
        while True:
            try:
                zbDbConn = db_mng.makeZbDbConn(self.cfg)
                cur = zbDbConn.cursor()
                
                getItemState = db_sql.GET_ZB_ITEM_STATE(self.zbItemStateKey)
                cur.execute( getItemState )
                
                dic = []
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                for row in rows:
                    d = dict(zip(columns, row))
                    dic.append(d)
                
                cur.close()
                
                for itemState in dic:
                    _cmd = """ %s -z %s -p %s -s %s -k %s -o %s | grep processed """%(self.zbSender, str(self.zbIP), 
                        str(self.zbPort), str(itemState['host']), str(self.zbItemStateKey), str(itemState['perc']) )
                    output = subprocess.check_output(_cmd, shell=True)
                    
                    try:
                        _chk = str(output).split('"')[1]
                        _chk = str(_chk).split(';')[0]
                        chk = int(str(_chk).split(':')[1].strip())
                        if chk < 1 :
                            self.logger.error( 'Fail to Send ZB Item State, cmd=%s, output=%s'%(_cmd, str(output)) )
                    except Exception, e:
                        self.logger.error( 'Fail to Send ZB Item State, cmd=%s, output=%s'%(_cmd, str(output)) )
                        self.logger.fatal(e)
                
            except Exception, e:
                self.logger.error( 'Fail to Send ZB Item State, cmd=%s, excp=%s'%(_cmd, str(e)) )
                self.logger.fatal(e)
            finally:
                if cur != None:
                    cur.close()
            
            sleep(self.itemChkPeriod)
     

def reqRtt_top( req, dbm, zbDbm, logger, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: Zabbix의 RTT 정보 RANK 10 가져온다. 
    - INPUT
        req(M): 요청 Parameter( customerseq )
        dbm(M): DB Connection 객체
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 조회 결과 반환
    """
    try:
        logger.error("reqRtt_top : %s" % req )

        result = dbm.select(db_sql.GET_ONEBOX_ID_IN_GROUP(req['groupseq']))
        if len(result) < 1:
            logger.error("No Data ( seq=%s )" % req['groupseq'] )
            return False, "No Data ( seq=%s )" % req['groupseq']

        # 결과 Dict 에 저장.
        # lst_servername = [list(r['servername']) for r in result]

        lst_onebox_id = []
        dict_oneboxinfo = {}
        for r in result :
            lst_onebox_id.append( r['onebox_id']) 
            dict_oneboxinfo[r['onebox_id']] = {"orgnamescode" : r['orgnamescode'], "customername" : r['customername'], "group_name" : r['group_name'] } 

        strSql = db_sql.GET_ZB_RTT_TOP (lst_onebox_id, req['start_dttm'], req['end_dttm'], req['count'])

        # logger.info (' GET_ZB_RTT_TOP : ' + strSql )

        ret = zbDbm.select(strSql)

        if len(ret) < 1:
            logger.error("No Data, Group Seq : %s" % req['groupseq'] )
            return False, "No Data, Group Seq : %s " % req['groupseq']

        lst_rank = []
        for r in ret :
            info = dict_oneboxinfo[r['onebox_id']]
            orgnamescode = info['orgnamescode']
            customer_name = info['customername']
            group_name = info['group_name']
            lst_rank.append ( {'onebox_id' : r['onebox_id'], "orgnamescode" : orgnamescode, "customer_name" : customer_name, "group_name" : group_name, 
                                "rank" : r['rank'], "max" : str(r['max']), "avg" : str(r['avg']),"min" : str(r['min'])}  )

        # res = {}
        # res = lst_rank
        return True, lst_rank
    except Exception, e:
        logger.error( ' reqRtt_top , excp=%s'%(str(e)) )
        logger.fatal(e)


def reqRtt_data( req, dbm, zbDbm, logger, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: Zabbix의 RTT 상세 Data 를 가져온다. Chart 그리기용. 
    - INPUT
        req(M): 요청 Parameter( customerseq )
        dbm(M): DB Connection 객체
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 조회 결과 반환
    """
    try:

        logger.info("reqRtt_data : %s" % req )

        result = dbm.select(db_sql.GET_PING_ZBKEY(req['onebox_id']))
        if len(result) < 1:
            logger.error("GET_SVRPING_ZBKEY No Data ( seq=%s )" % req['onebox_id'] )
            return False, "GET_SVRPING_ZBKEY No Data ( seq=%s )" % req['onebox_id']

        item_key = result[0]['monitemkey']

        if req['data_type'] == 'DETAIL' :
            strSql = db_sql.GET_ZB_RTT_DATA_DETAIL(req['onebox_id'], item_key, req['start_dttm'], req['end_dttm'])
        else :
            strSql = db_sql.GET_ZB_RTT_DATA_TRENDS(req['onebox_id'], item_key, req['start_dttm'], req['end_dttm'])

        logger.info (' GET_ZB_RTT_DATA : ' + strSql )

        ret = zbDbm.select(strSql)

        if len(ret) < 1:
            logger.error("No Data, OneBox ID : %s " % req['onebox_id'] )
            return False, "No Data, OneBox ID : %s " % req['onebox_id'] 

        lst_result = []
        for r in ret :
            clock = datetime.fromtimestamp(r['clk']).strftime('%Y-%m-%d %H:%M:%S')
            lst_result.append ( {"clock" : clock, "min" : str(r['min_val']), "avg" : str(r['avg_val']), "max" : str(r['max_val']) }  )
        return True, lst_result
    except Exception, e:
        logger.error( ' reqRtt_data , excp=%s'%(str(e)) )
        logger.fatal(e)



def reqNetwork_top( req, dbm, zbDbm, logger, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: Zabbix의 고객사 장비 RANK 5 가져온다. 
    - INPUT
        req(M): 요청 Parameter( customerseq )
        dbm(M): DB Connection 객체
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 조회 결과 반환
    """
    try:
        dic = dbm.select(db_sql.GET_NETWORK_TRAFFIC_TOP(req['customerseq'], req['rank_mode'], req['rank_count'] ))
        if len(dic) < 1:
            logger.error("No Data ( seq=%s )" % req['customerseq'] )
            return False, "No Data ( seq=%s )" % req['customerseq']
        
        rankSql = ''

        for r in dic :
            host = r['servername']
            orgnamescode = r['orgnamescode']
            rank = r['rank']
            rx_key = r['rx_key']
            tx_key = r['tx_key']

            rankSql += '' if rankSql == '' else ' UNION ALL '
            rankSql += db_sql.GET_ZB_NETWORK_TRAFFIC_TOP (host, orgnamescode, rank, rx_key,  tx_key)

        rankSql = 'SELECT * FROM ( ' + rankSql +  ' ) A ORDER BY rank, host, datetime'

        # logger.info("GET_ZB_NETWORK_TRAFFIC_TOP SQL : %s " % rankSql )

        ret = zbDbm.select(rankSql)

        if len(ret) < 1:
            logger.error("No Host " % req['customerseq'] )
            return False, "No Host " % req['customerseq']

        result = []
        lst_sub = []        

        old_host = ''
        for r in ret :
            host = r['host']
            if old_host == '' :
                old_host = host
            elif old_host <> host : 
                
                result.append({'host':old_host, 'orgnamescode':orgnamescode, 'rank':rank, 'value':copy.deepcopy(lst_sub)})
                old_host = host
                del lst_sub[:]

            orgnamescode = r['orgnamescode']
            rank = r['rank']
            dt = r['datetime']
            rx = r['rx']
            tx = r['tx']
            lst_sub.append({'datetime':str(dt), 'rx':str(rx), 'tx':str(tx)})

        result.append({'host':host, 'orgnamescode':orgnamescode, 'rank':rank, 'value':lst_sub})

        logger.info ( "result : %s " % str(result))

        res = {}
        res['rank_list'] = result
        return True, res
    except Exception, e:
        logger.error( ' reqNetwork_top , excp=%s'%(str(e)) )
        logger.fatal(e)


def reqOneboxNetwork_24h( req, dbm, zbDbm, logger, _ip=DEF_HOST, _port=DEF_PORT ):
    """
    - FUNC: Zabbix의에서 원박스의 24시간 네트워크 사용량을 가져 온다. 
    - INPUT
        req(M): 요청 Parameter( customerseq )
        dbm(M): DB Connection 객체
        zbDbm(M): ZB DB Connection 객체
        logger(M): 로그 기록 객체
        _ip(O): zbms IP
        _port(O): zbms Port
    - OUTPUT : 조회 결과 반환
    """
    try:
        ret = zbDbm.select(db_sql.GET_ZB_ONEBOX_NETWORK_TRAFFIC_24HOUR(req['onebox_id']))
        if len(ret) < 1:
            logger.error("No Onebox ID ( Onebox ID=%s)" % req['onebox_id'] )
            return False, "No Onebox ID ( Onebox ID=%s)" % req['onebox_id']

        # logger.info ( "result : %s " % str(ret))

        result = []
        lst_sub = []        
        old_eth = ''

        for r in ret :
            eth = r['ethname']
            if old_eth == '' :
                old_eth = eth
            elif old_eth <> eth : 
                result.append({'ethname':old_eth, 'value':copy.deepcopy(lst_sub)})
                old_eth = eth
                del lst_sub[:]

            lst_sub.append( {'datetime':str(r['datetime']), 'ethmode': r['ethmode'], 'value':str(r['value'])} )

        result.append({'ethname':eth, 'value':lst_sub})

        res = {'host':req['onebox_id'], 'traffic':result}
        return True, res


    except Exception, e:
        logger.error( ' reqOneboxNetwork_24h , excp=%s'%(str(e)) )
        logger.fatal(e)
