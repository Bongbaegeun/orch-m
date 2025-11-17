#-*- coding: utf-8 -*-
from util import rest_api
import os, json
import errno

TITLE = 'orchm'
import logging
logger = logging.getLogger(TITLE)

from handler import rrl_handler as rrl


HEADER={"content-type":"application/json-rpc"}
METHOD="POST"
URL_PFX = 'https://%s:%s'

OBA_URL = {
           'plugin': '/plugin',
           'file_put': '/file/put',
           'file_del' : '/file/del',
           'file_del_exclude' : '/file/del/exclude',
           'plugin_check' : '/zba/status/mon_file',
           'zba_restart': '/zba/restart'
           }

def getResponse( funcName, ret, _param ):
    """
    - FUNC: OBAgent로부터 받은 응답 결과 반환
    - INPUT
        funcName(M): 로그 기록 타이틀
        ret(M): OBAgent 요청 결과
        _param(M): 요청명령의 파라미터 
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    if ret == None :
        rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, None, None, _param)
        logger.error( rres.lF(funcName) )
        return rres
    
    res = None
    try:
        res = json.loads( ret.body )
    except Exception:
        rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Result Json Parsing Error', ret, _param)
        logger.error( rres.lF(funcName) )
        return rres
    
    if res.has_key('result') and res['result'] == 'SC':
        rres = rrl.rSc(None, res, _param)
        return rres
    elif res.has_key('error') :
        rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, res['error'], res, _param)
        logger.error( rres.lF(funcName) )
        return rres
    else:
        rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'No Key(result, error)', res, _param)
        logger.error( rres.lF(funcName) )
        return rres


def plugin_check( ip, port ):
    """
    - FUNC: OBAgent를 통해 Plugin 파일을 체크 한다.
    - INPUT
        ip(M): OBAgent IP
        port(M): OBAgent Port
    - OUTPUT
        RETURN : 성공 시 원박스에 전송된 각 템플릿 번호 반환
        에러 : {u'result': u'FA', u'error': {u'message': u'No ZB-Key-Directory, dir=/etc/zabbix/zabbix_agentd.conf.da', u'name': u'No Data'}}
        성공 : {u'template_list': [10, 11, 9], u'zba_key_list': [10, 9]}
    """
    FNAME = 'Plugin Check'
    url = URL_PFX%( ip, str(port) ) + OBA_URL['plugin_check']
    _param = {'url':url}

    try:
        body = {}

        ret = rest_api.sendReq( HEADER, url, METHOD, body, 300 )
        return ret.body
    except Exception, e:
        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, _param)
        logger.error( rres.lF(FNAME) )
        return rres

def restartZBA( ip, port ):
    """
    - FUNC: OBAgent를 통해 Zabbix Agent를 재기동한다.
    - INPUT
        ip(M): OBAgent IP
        port(M): OBAgent Port
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Restart ZBAgent'
    url = URL_PFX%( ip, str(port) ) + OBA_URL['zba_restart']
    _param = {'url':url}
    try:
        body = {}
        
        ret = rest_api.sendReq( HEADER, url, METHOD, body, 100 )
        return getResponse( FNAME, ret, _param )
    except Exception, e:
        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, _param)
        logger.error( rres.lF(FNAME) )
        return rres


def _delPath( fType, absPathList, ip, port, backupDir=None ):
    """
    - FUNC: OBAgent를 통해 대상을 파일시스템에서 제거한다.
    - INPUT
        type(M): 제거할 대상이 파일인지 디렉토리인지 설정
        absPathList(M): 제거할 대상의 절대 경로 리스트
        ip(M): OBAgent IP
        port(M): OBAgent Port
        backupDir(O): 제거 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Delete OBA File'
    url = URL_PFX%( ip, str(port) ) + OBA_URL['file_del']
    _param = {'url':url}
    try:
        body = { 'type': fType, 'targets': absPathList }
        if backupDir != None and backupDir != '':
            body['backup_dir'] = backupDir

        logger.info( "file_del - url : %s \n body : %s " % ( url, body ))        

        ret = rest_api.sendReq( HEADER, url, METHOD, body, 10 )
        return getResponse( FNAME, ret, _param )
    except Exception, e:
        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, _param)
        logger.error( rres.lF(FNAME) )
        return rres

def delFile( absPathList, ip, port, backupDir=None ):
    """
    - FUNC: OBAgent를 통해 파일을 제거한다.
    - INPUT
        absPathList(M): 제거할 파일의 절대 경로 리스트
        ip(M): OBAgent IP
        port(M): OBAgent Port
        backupDir(O): 제거 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    return _delPath( 'file', absPathList, ip, port, backupDir)

def delDir( absPathList, ip, port, backupDir=None ):
    """
    - FUNC: OBAgent를 통해 디렉토리를 제거한다.
    - INPUT
        absPathList(M): 제거할 디렉토리의 절대 경로 리스트
        ip(M): OBAgent IP
        port(M): OBAgent Port
        backupDir(O): 제거 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    return _delPath( 'dir', absPathList, ip, port, backupDir)

def deleteFileAtDir_Exclude( targetDir, excludeList, ip, port, backupDir=None ):
    """
    - FUNC: OBAgent를 통해 특정 파일을 제회하고 디렉토리 안의 모든 파일을 제거한다.
    - INPUT
        targetDir(M): 제거할 디렉토리
        excludeList(M): 제거 대상에서 제외할 항목 리스트
        ip(M): OBAgent IP
        port(M): OBAgent Port
        backupDir(O): 제거 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Delete OBA File'
    url = URL_PFX%( ip, str(port) ) + OBA_URL['file_del_exclude']
    _param = {'url':url}
    try:
        body = { 'target_dir': targetDir, 'exclude_file': excludeList }
        if backupDir != None and backupDir != '':
            body['backup_dir'] = backupDir

        ret = rest_api.sendReq( HEADER, url, METHOD, body, 10 )
        return getResponse( FNAME, ret, _param )
    except Exception, e:
        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, _param)
        logger.error( rres.lF(FNAME) )
        return rres


def _sendFileToSvr( url, name, data, backupDir=None ):
    """
    - FUNC: OBAgent를 통해 OB에 데이터를 전송하고 파일로 저장한다.
    - INPUT
        url(M): OBAgent에서 파일전송을 위해 열어놓은 URL
        name(M): 저장할 파일이름(절대경로)
        data(M): 저장할 데이터(텍스트)
        backupDir(O): 이전 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Send OBA File'
    _param = {'url':url}
    try:
        body = {
                'name' : name,
                'data' : data
                }
        
        if backupDir != None and backupDir != '':
            body['backup_dir'] = backupDir

        # logger.info( "file_put - url : %s \n body : %s " % ( url, body ))

        ret = rest_api.sendReq( HEADER, url, METHOD, body, 300 )
        return getResponse( FNAME, ret, _param )

    except Exception, e:
        # TODO :  if e.errno == errno.ECONNREFUSED:
        # logger.info ( "Connection Refused" ) connect 에러는 예외처리 해야하나?

        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'url':url})
        logger.error( rres.lF(FNAME) )
        return rres


def sendFile( orgName, dstName, ip, port, backup_dir=None ):
    """
    - FUNC: OBAgent를 통해 파일 전송 
    - INPUT
        orgName(M): 원본 데이터 파일 이름(로컬)
        dstName(M): 저장할 파일 이름(리모트)
        ip(M): OBAgent IP
        port(M): OBAgent Port
        backupDir(O): 제거 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    try:
        fd = os.open( orgName, os.O_RDWR )
        fileobj = os.fdopen( fd, 'r+b' )
        
        data = fileobj.read()
        
        fileobj.flush()
        fileobj.close()

        url = URL_PFX%( ip, str(port) ) + OBA_URL['file_put']

        return _sendFileToSvr( url, dstName, data, backup_dir )
    except Exception, e:
        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'ip':ip, 'port':port})
        logger.error( rres.lF('Send OBA File') )
        return rres
    

def sendData( data, dstName, ip, port, backup_dir=None ):
    """
    - FUNC: OBAgent를 통해 특정 파일을 제회하고 디렉토리 안의 모든 파일을 제거한다.
    - INPUT
        data(M): 원본 데이터 내용(텍스트)
        dstName(M): 저장할 파일 이름(리모트)
        ip(M): OBAgent IP
        port(M): OBAgent Port
        backupDir(O): 제거 대상의 백업 위치 설정, None일 경우 백업하지 않는다.
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    try:

        url = URL_PFX%( ip, str(port) ) + OBA_URL['file_put']

        return _sendFileToSvr( url, dstName, data, backup_dir )
    except Exception, e:
        logger.fatal( e )
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'ip':ip, 'port':port})
        logger.error( rres.lF('Send OBA Data') )
        return rres
