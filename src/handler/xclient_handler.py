#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''

from util import db_sql
from api import oba_api
from handler import rrl_handler as rrl
from msg import mon_msg

import json, os


TITLE = 'orchm'

import logging
logger = logging.getLogger(TITLE)

PNF_ZBA_CFG_DIR = ''
PNF_ZBA_LOG = '/mnt/flash/data/onebox/zabbix/log/'


def _createCfg( logName, key, pluginPath, params, paramNum ):
    """
    - FUNC: 모니터링 Agent(Zabbix)의 감시항목 설정 파일 내용 생성
    - INPUT
        logName(M): Log 파일 이름
        key(M): Zabbix의 아이템 Key 값
        pluginPath(M): PlugIn 절대 경로
        params(M): PlugIn에 사용할 파라미터
        paramNum(M): PlugIn의 총 파라미터 개수(유동적으로 입력이 필요한 PlugIn을 위해 필요, monitorobject 입력받음)
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    cfgParams = ""
    paramCnt = 0
    if params != None :
        try:
            _params = json.loads( params )
            paramCnt = len( _params )
            for param in _params:
                cfgParams += ( " \"" + str(param) + "\"" )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, params)
            logger.error(rres.lL('Create ZBConfig'))
            logger.fatal(e)
            return rres
    
    for i in range( int(paramNum) - int(paramCnt) ):
        cfgParams += ( " $%s"%str(i+1) )

    # PNF 인가?
    if pluginPath.find ('/data/onebox/zabbix/') > -1 :
        cfgParams += " 2>> /mnt/flash/data/onebox/zabbix/log/%s.log"%str(logName)
    else :
        cfgParams += " 2>> /var/log/zabbix-agent/plugin/%s.log"%str(logName)
    
    ret = 'UserParameter=' + key + ',' + pluginPath + cfgParams + "\n"
    return rrl.rSc(None, ret, params)

def settingMonAgent( dbm, oba_port, zbaCfgDir, _monInfo ):
    """
    - FUNC: 모니터링 Agent(Zabbix)의 설정파일 생성 및 전송, 적용
    - INPUT
        dbm(M): DB 연결 객체
        oba_port(M): OBAgent 포트
        zbaCfgDir(M): ZBAgent의 설정 파일 경로
        _monInfo(M): 요청 파라미터
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    logger.info( 'Setting One-Box Monitoring Agent' )
    
    FNAME = 'Setting OB MoitoringAgent'
    
    monInfo = mon_msg.MonInfo
    if _monInfo != None :
        monInfo = _monInfo
    else:
        rres = rrl.rFa(None, rrl.RS_NO_PARAM, None, None, None)
        logger.error( rres.lF(FNAME) )
        return rres
    try:
        svrSeq = monInfo.svrInfo.svrSeq
        ip = monInfo.svrInfo.svrIP
        for targetInfo in monInfo.targetList: 
            targetSeq = targetInfo.targetSeq
            
            # 설정파일 이름 생성
            ret = dbm.select( db_sql.GET_ZBCFG_NAME( targetSeq ) )
            if ret == None or len(ret) < 1:
                if ret == None:
                    rs = rrl.RS_FAIL_DB
                else:
                    rs = rrl.RS_NO_DATA
                rres = rrl.rFa(None, rs, None, ret, {'target_seq':targetSeq})
                logger.error( rres.lF(FNAME) )
                return rres

            if ( targetInfo.targetCode == 'pnf' and targetInfo.targetVendor == 'axgate' ) or monInfo.svrInfo.onebox_type == 'KtPnf' :
                zbaCfgDir = PNF_ZBA_CFG_DIR


            zbCfgName = os.path.join( zbaCfgDir, os.path.basename(ret[0]['cfgname']) )
            
            # 설정  내용 생성
            zbCfg = ""
            ret = dbm.select( db_sql.GET_ZBCFG_INFO( svrSeq, targetSeq ) )
            for cfgInfo in ret :
                rres = _createCfg( cfgInfo['log_name'], cfgInfo['key'], cfgInfo['p_path'], cfgInfo['param'], cfgInfo['p_num'])
                if rres.isFail() :
                    return rres
                zbCfg += rres.ret()
            
            # 설정 내용 전송
       
            rres = oba_api.sendData( zbCfg, zbCfgName, ip, oba_port, './backup' )
            if rres.isFail() :
                rres.setParam({'zb_cfg_name':zbCfgName, 'ob_ip':ip})
                logger.error( rres.lF('Send MonAgentConfig') )
                return rres
            
            sql = db_sql.INSERT_ZBA_CFG( svrSeq, targetSeq, zbCfgName )
            dbm.execute(sql)
            
        sql = db_sql.GET_ZBA_CFG_LIST( svrSeq )
        cfgList = dbm.select(sql, 'cfgname')
        rres = oba_api.deleteFileAtDir_Exclude( zbaCfgDir, cfgList, ip, oba_port, './backup' )
        if rres.isFail() :
            rres.setParam({'zba_cfg_dir': zbaCfgDir, 'exclude':cfgList})
            logger.error( rres.lF('Delete(Backup) Previous Cfg') )
            return rres
        
        rres = oba_api.restartZBA( ip, oba_port )
        if rres.isFail() :
            logger.error(rres.lF('Restart ZBA'))
            return rres
    
        return rrl.rSc(None, None, monInfo)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, monInfo)
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres


def settingMonAgent_first_notify(dbm, oba_ip, oba_port, svrSeq, targetSeq):
    """
    - FUNC: OB에서 first_notify 이벤트시
                모니터링 Agent(Zabbix)의 설정파일 생성 및 전송, 적용
    - INPUT
        dbm(M): DB 연결 객체
        oba_port(M): OBAgent 포트
        _monInfo(M): 요청 파라미터
    - OUTPUT
        result: rrl_handler._ReqResult
    """

    FNAME='Setting OB MoitoringAgent - First Notify'
    logger.info(FNAME)

    try:

        logger.info ( "GET_ZBCONFIG_INST_CFGNAME : %s " % svrSeq )

        # ZB 설정파일 이름 가져오기
        ret =dbm.select(db_sql.GET_ZBCONFIG_INST_CFGNAME(svrSeq, targetSeq))

        if ret == None or len(ret) < 1:
            if ret == None:
                rs=rrl.RS_FAIL_DB
            else:
                rs=rrl.RS_NO_DATA
            rres=rrl.rFa(None, rs, None, ret, {'target_seq': targetSeq})
            logger.error(rres.lF(FNAME))
            return rres

        zbCfgNameStr = ret[0]['cfgname']

        # 설정  내용 생성
        zbCfg=""
        sql = db_sql.GET_ZBCFG_INFO(svrSeq, targetSeq)
        ret=dbm.select(sql)
        for cfgInfo in ret:
            rres=_createCfg(cfgInfo['log_name'], cfgInfo['key'], cfgInfo['p_path'], cfgInfo['param'],
                            cfgInfo['p_num'])
            if rres.isFail():
                return rres
            zbCfg+=rres.ret()

        # 설정 내용 전송
        rres=oba_api.sendData(zbCfg, zbCfgNameStr, oba_ip, oba_port, './backup')
        if rres.isFail():
            rres.setParam({'zb_cfg_name': zbCfgNameStr, 'ob_ip': oba_ip})
            logger.error(rres.lF('Send MonAgentConfig'))
            return rres

    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres



