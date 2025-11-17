# -*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
from time import sleep
import json, threading, copy
import random

from api import zbm_api, orchf_api, oba_api, web_api
from handler import plugin_handler, xclient_handler, req_handler, item_handler, rrl_handler as rrl
from msg import mon_msg
from util import db_sql, e2e_logger, rest_api

from api import zabbix_api

import util.str_api as sa

TITLE='orchm'

from util.ko_logger import ko_logger

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

logger = ko_logger(tag=TITLE, logdir="./log/", loglevel="debug", logConsole=False).get_instance()

#import logging
#logger=logging.getLogger(TITLE)

# 개발시 로그표시 유무.
DEBUG_LOG_YN='y'

## Item 상태 체크 회수
CHK_PEPEAT=30

HEADER={"content-type":"application/json-rpc"}
METHOD="POST"

def setArg(arg, argName, noneType=None):
    return (lambda x: x[argName] if x.has_key(argName) else noneType)(arg)

def globalSetting(OrchmPort, obaPort, zbmPort, zbCfg_dir, pnf_zbCfg_dir, backup_dir, pluginPath, pnf_pluginPath, _gVar):
    """
    - FUNC: mon_handler 모듈에서 사용하는 전역 변수 설정
    - INPUT
        obaPort(M): OBAgent TCP 포트 번호
        zbmPort(M): ZB Server Manager TCP 포트 번호
        zbCfg_dir(M): ZB 설정파일 디렉토리
        backup_dir(M): 기본 백업 디렉토리
        pluginPath(M): 기본 PlugIn 설치 디렉토리
        pnf_pluginPath(M): pnf형 기본 PlugIn 설치 디렉토리
        _gVar(M): Orch-M의 공통 전역 변수 관리
    """
    global orchm_port, oba_port, zba_port, zbaCfgDir, _backupDir, defaultPluginPath, gVar

    orchm_port=OrchmPort
    oba_port=obaPort
    zba_port=zbmPort
    zbaCfgDir=zbCfg_dir
    _backupDir=backup_dir
    defaultPluginPath=pluginPath
    gVar=_gVar

    # PNF 형 Plugin 경로 orchf 에 할당.
    orchf_api.PNF_PLUGIN_PATH=pnf_pluginPath

    # PNF 형 Zabbix conf 경로 
    xclient_handler.PNF_ZBA_CFG_DIR=pnf_zbCfg_dir

class ItemChecker(threading.Thread):
    """
    - FUNC: 모니터링 시작 후 감시 항목의 상태를 체크하기 위한 Thread
    - INPUT
        svr_seq(M): One-Box 서버 Sequence
        svrOBID(M): One-Box 서버 OB ID
        dbm(M): DB 연결 객체
        tid(M): 서비스 요청 TID
        isStartOn(O): 프로그램 시작 시 미완료된 감시항목 상태 체크 진행에 의한 쓰레드 시작 여부
    - OUTPUT: 모니터링 감시 항목 정상 동작 확인 Thread
    """

    STATUS_ITEM_CHK_ON='item_checking'
    STATUS_ITEM_CHK_REFRESH='item_check_refresh'
    STATUS_ITEM_CHK_FAIL='item_check_fail'

    def __init__(self, svr_seq, svrOBID, dbm, tid, isStartOn=False):
        threading.Thread.__init__(self)
        self.svrSeq=svr_seq
        self.svrOBID=svrOBID
        self.dbm=dbm
        self.tid=tid
        self.isStartOn=isStartOn

    def run(self):
        FNAME='Item Status Check'
        ## 이미 서버에 대한 감시항목 상태 체크가 진행 중이면 refresh로 변경하고 체크 수행하지 않음
        status=gVar.locked_read_param(self.svrOBID)
        if not self.isStartOn:
            if status == None or status == self.STATUS_ITEM_CHK_FAIL:
                gVar.locked_write_param(self.svrOBID, self.STATUS_ITEM_CHK_ON)
            else:
                gVar.locked_write_param(self.svrOBID, self.STATUS_ITEM_CHK_REFRESH)
                return
        else:
            if status != None:
                gVar.locked_write_param(self.svrOBID, self.STATUS_ITEM_CHK_ON)
            else:
                return
        ## 5초에 한번씩 감시항목의 상태체크를 수행(총 CHK_REPEAT 회수 만큼 수행)
        chk_period=5
        repeatCnt=CHK_PEPEAT
        i=0
        while True:
            i+=1
            if i > repeatCnt:
                break
            sleep(chk_period)

            status=gVar.locked_read_param(self.svrOBID)
            if status == None or status == self.STATUS_ITEM_CHK_FAIL:
                gVar.locked_write_param(self.svrOBID, self.STATUS_ITEM_CHK_ON)
            elif status == self.STATUS_ITEM_CHK_REFRESH:
                i=0
                gVar.locked_write_param(self.svrOBID, self.STATUS_ITEM_CHK_ON)

            ## ZB 감시 항목 상태 정보 GET
            zbRet=zbm_api.chkItemStatus(logger, self.svrOBID)
            if zbRet == None:
                icRes=rrl.rFa(self.tid, rrl.RS_NO_DATA, 'Item Status Info Error', None, {'chk_cnt': i})
                logger.warning(icRes.lF(FNAME))
            else:
                try:
                    keyList=self.dbm.select(db_sql.GET_KEY_LIST_BY_SERVER(self.svrSeq), 'key')
                    disabledList=[]
                    notSupportedList=[]
                    noKeyList=[]

                    for key in keyList:

                        isChked=False
                        for zbKey in zbRet:

                            if zbKey['key'] == key:
                                if zbKey['status'] == 1:
                                    disabledList.append(key)
                                elif zbKey['status'] == 3:
                                    notSupportedList.append(key)

                                isChked=True
                                break

                        if not isChked:
                            noKeyList.append(key)

                    cmpRet={'disable': disabledList, 'not_support': notSupportedList, 'no_key': noKeyList}
                    if len(cmpRet['disable']) > 0 or len(cmpRet['not_support']) > 0 or len(cmpRet['no_key']) > 0:
                        ret={'disable': len(cmpRet['disable']), 'not_support': len(cmpRet['not_support']),
                             'no_key': len(cmpRet['no_key']), 'delay': i * chk_period}
                        icRes=rrl.rFa(self.tid, rrl.RS_IN_PROGRESS, 'Item Status Checking', cmpRet,
                                      {'svr_seq': self.svrSeq})
                        # logger.debug( icRes.lL(FNAME) )
                        icRes=rrl.rFa(self.tid, rrl.RS_IN_PROGRESS, 'Item Status Checking', ret,
                                      {'svr_seq': self.svrSeq})
                        logger.warning(icRes.lL(FNAME))
                    else:
                        icRes=rrl.rSc(self.tid, {'op_time(sec)': i * chk_period}, None)
                        logger.info(icRes.lS(FNAME))
                        gVar.locked_write_param(self.svrOBID, None)
                        return True
                except Exception, e:
                    icRes=rrl.rFa(self.tid, rrl.RS_EXCP, e, None, {'svr_seq': self.svrSeq})
                    logger.warning(icRes.lF(FNAME))
                    logger.fatal(e)
                    continue

        gVar.locked_write_param(self.svrOBID, self.STATUS_ITEM_CHK_FAIL)
        return False


def _delRowNoUse(tableName, referColumn, dbm, val=None):
    """
    - FUNC: 테이블의 사용하지 않는(참조하고 있지 않고 삭제 처리된 것) 데이터 삭제
    - INPUT
        tableName(M): 테이블 이름
        referColumn(M): 테이블의 참조 컬럼 이름
        dbm(M): DB 연결 객체
        val(O): 지울 참조 컬럼의 값
    - OUTPUT: SQL 실행 결과(삭제 개수)
    """
    getTableSql=db_sql.GET_TABLE_INFO_USING_FKEY(tableName, referColumn)
    tableList=dbm.select(getTableSql)
    if tableList == None or len(tableList) < 1:
        delSql=db_sql.REMOVE_ROW_NOUSE(tableName, referColumn, val)
        return dbm.execute(delSql)
    else:
        delSql=db_sql.REMOVE_ROW_NOUSE_FK(tableName, referColumn, tableList, val)
        return dbm.execute(delSql)


def _chkKeyDuplicated(dbm, svrSeq, targetInfoList):
    """
    - FUNC: 감시항목의 Key 값 중복 체크
    - INPUT
        dbm(M): DB 연결 객체
        svrSeq(M): One-Box 서버 Sequence
        targetInfoList(M): 감시 대상 리스트
    - OUTPUT: Key 중복 체크 결과(중복 시 Key 정보 반환)
        rrl_handler._ReqResult
    """
    FNAME='Check Key Duplicated'
    _param={'svr_seq': svrSeq, 'target_info': targetInfoList}
    targetList=[]

    try:
        ## 사용 중인 target 가져오기
        ret=dbm.select(db_sql.GET_TARGET_BY_SVR(svrSeq), 'target_seq')
        for targetSeq in ret:
            targetList.append(int(targetSeq))

        ## targetInfo에서 target 가져오기
        for targetInfo in targetInfoList:
            tSeq=targetInfo.targetSeq
            if tSeq != None:
                if not int(tSeq) in targetList:
                    targetList.append(int(tSeq))

        target_list=''
        if len(targetList) > 1:
            target_list=str(tuple(targetList))
        elif len(targetList) == 1:
            target_list='(%s)' % targetList[0]
        else:
            kdRes=rrl.rFa(None, rrl.RS_NO_DATA, 'No Target Seq', targetList, _param)
            logger.error(kdRes.lF(FNAME))
            return kdRes

        getKeyListSql=db_sql.GET_KEYCAT_LIST_BY_TARGET(target_list)
        ret=dbm.select(getKeyListSql)

        for key in ret:
            if int(key['cnt']) > 1:
                duplicated=dbm.select(db_sql.GET_KEY_INFO_BY_KEY(key['key']))
                kdRes=rrl.rFa(None, rrl.RS_DUPLICATE_DATA, 'Key In-Use, num=%s' % str(key['cnt']), duplicated, _param)
                logger.error(kdRes.lF(FNAME))
                return kdRes

        return rrl.rSc(None, None, None)
    except Exception, e:
        kdRes=rrl.rFa(None, rrl.RS_EXCP, e, None, _param)
        logger.error(kdRes.lF(FNAME))
        logger.fatal(e)
        return kdRes


def _getDefaultDiscInput(discParam=None):
    """
    - FUNC: ZB Discovery 시 넘겨줄 기본 항목 설정
    - INPUT
        discParam(O): 기본 discovery 항목 리스트 정보
    - OUTPUT: 기본 Discovery 항목 리스트
    """
    df={'vnet_list': ['global_mgmt_net', 'public_net', 'net_office', 'net_internet', 'net_server'],
        'vrouter_list': ["global_mgmt_router"]}
    if discParam == None:
        return df

    _list=[]

    if str(discParam).lower() == 'vnet_list':
        _list=df['vnet_list']
    elif str(discParam).lower() == 'vrouter_list':
        _list=df['vrouter_list']

    return _list


def _removeTarget(tid, targetSeq, dbm):
    """
    - FUNC: 감시 대상 제거
    - INPUT
        targetSeq(M): 감시 대상 Sequence
        dbm(M): DB 연결 객체
    """
    _param={'target_seq': targetSeq}

    ### ZBS에서 제거
    ret=zbm_api.delTemplate(logger, targetSeq)
    if ret:
        logger.info(rrl.rSc(tid, None, _param).lS('Remove ZB Template'))
    else:
        logger.error(rrl.rFa(tid, rrl.RS_API_ZBS_ERR, ret, None, _param).lF('Remove ZB Template'))

    ### DB 에서 제거

    # zbKey 제거
    cntUZbKey=dbm.execute(db_sql.DEL_KEY(targetSeq))
    # threshold 제거
    cntUThr=dbm.execute(db_sql.DEL_THRESHOLD(targetSeq))
    # discovery 제거
    cntUDisc=dbm.execute(db_sql.DEL_DISCOVERY(targetSeq))
    # Item 제거
    cntUItem=dbm.execute(db_sql.DEL_ITEM(targetSeq))
    # 장애 guide 제거
    cntUGuide=dbm.execute(db_sql.DEL_GUIDE(targetSeq))
    # PlugIn 제거
    cntUPlugin=dbm.execute(db_sql.DEL_PLUGIN(targetSeq))
    # Group 제거
    cntUGroup=dbm.execute(db_sql.DEL_GROUP(targetSeq))
    # Target 제거
    cntUTarget=dbm.execute(db_sql.DEL_TARGET(targetSeq))

    # zbKey 제거
    cntDZbKey=_delRowNoUse('tb_zbkeycatalog', 'zbkeycatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUZbKey, 'remove': cntDZbKey}, _param).lS('Delete ZBKey'))

    # threshold 제거
    cntDThr=_delRowNoUse('tb_monthresholdcatalog', 'monthresholdcatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUThr, 'remove': cntDThr}, _param).lS('Delete Threshold'))

    # discovery map 제거
    cntDMap=dbm.execute(db_sql.REMOVE_DISCOVERY_MAP(targetSeq))
    logger.info(rrl.rSc(tid, {'remove': cntDMap}, _param).lS('Delete DiscoveryMap'))

    # Item 제거
    cntDItem=_delRowNoUse('tb_monitemcatalog', 'monitemcatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUItem, 'remove': cntDItem}, _param).lS('Delete Item'))

    # 장애 guide 제거
    cntDGuide=_delRowNoUse('tb_monalarmguide', 'monalarmguideseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUGuide, 'remove': cntDGuide}, _param).lS('Delete AlarmGuide'))

    # discovery 제거
    cntDDisc=_delRowNoUse('tb_zbdiscoverycatalog', 'zbdiscoverycatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUDisc, 'remove': cntDDisc}, _param).lS('Delete Discovery'))

    # PlugIn 제거
    cntDPlugin=_delRowNoUse('tb_monplugincatalog', 'monplugincatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUPlugin, 'remove': cntDPlugin}, _param).lS('Delete PlugIn'))

    # Group 제거
    cntDGroup=_delRowNoUse('tb_mongroupcatalog', 'mongroupcatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUGroup, 'remove': cntDGroup}, _param).lS('Delete Group'))

    # Target 제거
    cntDTarget=_delRowNoUse('tb_montargetcatalog', 'montargetcatseq', dbm)
    logger.info(rrl.rSc(tid, {'update': cntUTarget, 'remove': cntDTarget}, _param).lS('Delete Target'))


def removeTarget(tid, params, dbm):
    """
    - FUNC: 감시 대상 정보 제거
    - INPUT
        tid(M): 요청 TID
        params(M): 감시 대상 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 대상 제거 결과
        rrl_handler._ReqResult
    """
    try:
        targetSeq=str(params['target_seq'])

        ## 사용 중인지 체크
        ret=dbm.select(db_sql.GET_TARGET_FOR_CHK_USED(targetSeq))
        if len(ret) > 0:
            rtRes=rrl.rFa(tid, rrl.RS_INUSE_DATA, 'In-Use Target', ret, params)
            logger.error(rtRes.lF('Remove Target'))
            return rtRes

        _removeTarget(tid, targetSeq, dbm)

        rtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(rtRes.lS('Remove Target'))
        return rtRes
    except Exception, e:
        rtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(rtRes.lF('Remove Target'))
        logger.fatal(e)
        return rtRes


def createTarget(src, tid, params, dbm):
    """
    - FUNC: 감시 대상 생성
    - INPUT
        src(M): 요청 호스트 주소
        tid(M): 요청 TID
        params(M): 감시 대상 정보
        dbm(M): DB 연결 객체
    """
    FNAME='Create Target'

    ## Orch-M 용 파라미터로 변경
    req_handler.saveRequestStatus(dbm, src, tid, 'READY', 'CONVERT_PARAM', 1)
    ctRes=orchf_api.convertTemplateAddParam(params)
    if ctRes.isFail():
        logger.error(ctRes.setErr('Convert Parameters Error').ltF(FNAME))
        req_handler.saveRequestFail(dbm, src, tid, ctRes.errStr())
        return

    params=ctRes.ret()
    rbDB=dbm.getRollBackDB()

    try:
        ### 파라미터 파싱
        req_handler.saveRequestState(dbm, src, tid, 'PARSE_PARAM', 5)
        targetInfo=params['target_info']

        targetCode=targetInfo['code']
        targetType=targetInfo['type']
        targetName=targetInfo['name']
        targetVName=targetInfo['visible']
        targetModel=targetInfo['model']
        targetVer=targetInfo['version']
        targetDesc=targetInfo['description']
        vendorCode=targetInfo['vendor_code']

        targetFor=vdudSeq=vdudVer=None
        if targetInfo.has_key('vdud_seq'): vdudSeq=str(targetInfo['vdud_seq'])
        if targetInfo.has_key('vdud_version'): vdudVer=str(targetInfo['vdud_version'])
        if targetInfo.has_key('target_for'): targetFor=str(targetInfo['target_for'])
        logger.info(rrl.rSc(tid, None, {'target_name': targetName}, _msg='Monitoring TargetInfo Parsing').lS(FNAME))

        ### 유효성 체크: tb_vdu, tb_vendor, tb_nfcatalog, tb_montargetcatalog
        req_handler.saveRequestState(dbm, src, tid, 'CHECK_PARAM', 10)
        ctRes=item_handler.chkForCreateTarget(rbDB, targetCode, targetType, targetVer, vendorCode, targetModel, vdudSeq,
                                              targetFor)
        if ctRes.isFail():
            rbDB.rollback()
            logger.error(ctRes.setErr('Check Parameters Error').ltF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, ctRes.errStr())
            return
        logger.info(rrl.rSc(tid, None, None, _msg='Monitoring Target Validation Check').lS(FNAME))

        ### Target 생성
        req_handler.saveRequestStatus(dbm, src, tid, 'READY_TARGET', 'CREATE_TARGET', 15)
        ctRes=item_handler.createTarget(targetCode, targetType, vendorCode, targetModel, targetDesc, targetName,
                                        targetVName, targetVer, vdudSeq, targetFor, vdudVer, rbDB)
        if ctRes.isFail():
            rbDB.rollback()
            logger.error(ctRes.setErr('Create Target Error').ltF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, ctRes.errStr())
            return
        ret=ctRes.ret()

        targetSeq=ret['targetSeq']
        logger.info(rrl.rSc(tid, ret, None, _msg='Create Monitoring Target').lS(FNAME))

        ### Orch-M DB 저장
        req_handler.saveRequestStatus(dbm, src, tid, 'DB OP', 'CREATE_ITEM', 30)
        if params.has_key('group'):
            tot=len(params['group'])
            num=1
            for grp in params['group']:
                ## GROUP 생성
                ctRes=item_handler.createGroup(targetSeq, grp, rbDB)
                if ctRes.isFail():
                    rbDB.rollback()
                    logger.error(ctRes.setErr('Create Group Error').ltF(FNAME))
                    req_handler.saveRequestFail(dbm, src, tid, ctRes.err())
                    return
                ret=ctRes.ret()

                gSeq=ret['groupSeq']
                gName=grp['name']
                logger.info(rrl.rSc(tid, ret, {'group_name': gName}, _msg='Create Monitoring Group').lS(FNAME))

                ## Item 생성
                if grp.has_key('item'):
                    ctRes=item_handler.createItem(targetSeq, gSeq, grp['item'], rbDB)
                    if ctRes.isFail():
                        rbDB.rollback()
                        logger.error(ctRes.setErr('Create Item Error').ltF(FNAME))
                        req_handler.saveRequestFail(dbm, src, tid, ctRes.err())
                        return
                    ret=ctRes.ret()

                    # {'Item':, 'PlugIn':, 'AlarmGuide':, 'Threshold':, 'Key':}
                    logger.info(rrl.rSc(tid, None, None, _msg='Create Items').lS(FNAME))
                    logger.info(rrl.rSc(tid, ret, None, _msg='Created Items Size').lS(FNAME))

                ## Discovery 생성
                if grp.has_key('discovery'):
                    ctRes=item_handler.createDiscovery(targetSeq, gSeq, grp['discovery'], rbDB)
                    if ctRes.isFail():
                        rbDB.rollback()
                        logger.error(ctRes.setErr('Create Disc Error').ltF(FNAME))
                        req_handler.saveRequestFail(dbm, src, tid, ctRes.err())
                        return
                    ret=ctRes.ret()
                    logger.info(rrl.rSc(tid, None, None, _msg='Create Discovery').lS(FNAME))
                    # {'Discovery':0, 'DiscoveryPlugIn':0, 'Item':0, 'PlugIn':0, 'Key':0, 'Threshold':0, 'AlarmGuide':0 }
                    logger.info(rrl.rSc(tid, ret, None, _msg='Created Discovery Size').lS(FNAME))

                req_handler.saveRequestProg(dbm, src, tid, float(num) / float(tot) * 50 + 30)
                num+=1
        logger.info(rrl.rSc(tid, None, {'target_name': targetName}, _msg='Insert TargetInfo Into DB').lS(FNAME))

        ### ZBM 파라미터로 변환
        req_handler.saveRequestStatus(dbm, src, tid, 'READY_ZBPARAM', 'CONVERT_ZBPARAM', 80)
        itemList=[]
        discoveryList=[]
        keyList=[]

        if params.has_key('group'):
            for grp in params['group']:
                if grp.has_key('item'):
                    isSucc, ret=zbm_api.convertItem(logger, targetSeq, grp['name'], grp['item'], keyList)
                    if not isSucc:
                        rbDB.rollback()
                        ctRes=rrl.rFa(tid, rrl.RS_FAIL_ZB_OP, ret, None, {'target_seq': targetSeq})
                        ctRes.lF('ZB Convert Item')
                        logger.error(ctRes.setErr('Convert ZB Item Error').ltF(FNAME))
                        req_handler.saveRequestFail(dbm, src, tid, ctRes.errStr())
                        return
                    else:
                        itemList+=ret['item']
                        keyList+=ret['key']

                if grp.has_key('discovery'):
                    isSucc, ret=zbm_api.convertDiscovery(logger, targetSeq, targetType, grp['name'], grp['discovery'],
                                                         keyList)
                    if not isSucc:
                        rbDB.rollback()
                        ctRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, ret, None, {'target_seq': targetSeq})
                        ctRes.lF('ZB Convert Discovery')
                        logger.error(ctRes.setErr('Convert ZB Disc Error').ltF(FNAME))
                        req_handler.saveRequestFail(dbm, src, tid, ctRes.errStr())
                        return
                    else:
                        discoveryList+=ret['discovery']
                        keyList+=ret['key']
        logger.info(rrl.rSc(tid, {'item_size': len(itemList), 'discovery_size': len(discoveryList)}, None,
                            _msg='Convert Into Zabbix TemplateInfo').lS(FNAME))

        ### ZBM에 전송
        req_handler.saveRequestStatus(dbm, src, tid, 'ZB OP', 'CREATE_ZB_TEMPLATE', 90)
        ret=zbm_api.addTemplate(logger, targetSeq, targetName, targetVer, targetDesc, itemList, discoveryList)
        if ret == False:
            rbDB.rollback()
            ctRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Create ZB Template Error', None, {'target_name': targetName})
            logger.error(ctRes.lF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, ctRes.errStr())
            return
        logger.info(rrl.rSc(tid, None, {'target_name': targetName}, _msg='Create Zabbix TemplateInfo').lS(FNAME))

        rbDB.commit()
        logger.info(rrl.rSc(tid, {'target_name': targetName, 'target_seq': targetSeq}, None, _msg='Complate').lS(FNAME))
        req_handler.saveRequestComplete(dbm, src, tid)
    except Exception, e:
        rbDB.rollback()
        logger.error(rrl.rFa(tid, rrl.RS_EXCP, e, None, None).lF(FNAME))
        logger.fatal(e)
        req_handler.saveRequestFail(dbm, src, tid, e)
    finally:
        rbDB.close()
    return


def delItemInst(tid, dbm, itemCatSeq):
    """
    - FUNC: DB에서 감시 항목 인스턴스 삭제
    - INPUT
        tid(M): 요청 TID
        dbm(M): DB 연결 객체
        itemCatSeq(M): 감시 항목 카탈로그 시퀀스
    """
    FNAME='Delete Item Catalog DB'
    ### Orch-M DB에서 제거
    ## curr/hist 알람 장애 미조치 내역 내용 변경 -> 서비스 해지
    ret=dbm.execute(db_sql.UPDATE_CURR_ALARM_FOR_DEL_ITEMCAT(itemCatSeq, '감시항목 삭제'))
    logger.info(rrl.rSc(tid, {'Update': ret}, {'item_cat_seq': itemCatSeq}, _msg='Current Alarm').lS(FNAME))
    ret=dbm.execute(db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE())
    logger.info(rrl.rSc(tid, {'Update': ret}, {'item_cat_seq': itemCatSeq}, _msg='History Alarm').lS(FNAME))

    # Threshold Instance 제거
    ret=dbm.execute(db_sql.REMOVE_THRESHOLD_INST_FOR_DEL_ITEMCAT(itemCatSeq))
    logger.info(rrl.rSc(tid, {'Remove': ret}, {'item_cat_seq': itemCatSeq}, _msg='Threshold Instance').lS(FNAME))

    # Key Instance 제거
    ret=dbm.execute(db_sql.REMOVE_KEYINSTANCE_FOR_DEL_ITEMCAT(itemCatSeq))
    logger.info(rrl.rSc(tid, {'Remove': ret}, {'item_cat_seq': itemCatSeq}, _msg='ZBKey Instance').lS(FNAME))

    # Item Instance 제거
    ret=dbm.execute(db_sql.DEL_ITEMINSTANCE_FOR_DEL_ITEMCAT(itemCatSeq))
    logger.info(rrl.rSc(tid, {'Update': ret}, {'item_cat_seq': itemCatSeq}, _msg='Item Instance').lS(FNAME))

    # RealTime 성능 제거
    ret=dbm.execute(db_sql.REMOVE_REALTIMEPERF_FOR_DEL_ITEMCAT(itemCatSeq))
    logger.info(rrl.rSc(tid, {'Remove': ret}, {'item_cat_seq': itemCatSeq}, _msg='RealTime PerfData').lS(FNAME))

    # 안쓰는 RealTime Item 제거
    ret=dbm.execute(db_sql.REMOVE_REALTIME_ITEM_UNUSED())
    logger.info(rrl.rSc(tid, {'Remove': ret}, None, _msg='Unused RealTime PerfData').lS(FNAME))

    # 안쓰는 Item Instance 제거
    ret=_delRowNoUse('tb_moniteminstance', 'moniteminstanceseq', dbm)
    logger.info(rrl.rSc(tid, {'Remove': ret}, None, _msg='Unused Item Instance').lS(FNAME))

    # 안쓰는 PlugIn Instance 제거
    ret=_delRowNoUse('tb_monplugininstance', 'monplugininstanceseq', dbm)
    logger.info(rrl.rSc(tid, {'Remove': ret}, None, _msg='Unused Plugin Instance').lS(FNAME))


#
#############
def delTargetItem(tid, params, dbm):
    """
    - FUNC: 감시 대상 카탈로그 삭제
    - INPUT
        tid(M): 요청 TID
        params(M): 감시 항목 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 대상 제거 결과
        rrl_handler._ReqResult
    """
    FNAME='Delete Item Catalog'
    rbDB=dbm.getRollBackDB()
    try:
        itemCatSeq=str(params['item_cat_seq'])
        logPara={'item_cat_seq': itemCatSeq}
        apply_yn=(lambda x: True if x.has_key('apply_yn') and str(x['apply_yn']).lower() == 'y' else False)(params)

        ret=rbDB.select(db_sql.GET_ITEM_INFO_FOR_DELITEM(itemCatSeq))
        if ret == None or len(ret) != 1:
            rbDB.rollback()
            if ret == None:
                rsc=rrl.RS_FAIL_DB
            else:
                rsc=rrl.RS_INVALID_DATA
            dtRes=rrl.rFa(tid, rsc, 'Item Info Error', ret, logPara)
            logger.error(dtRes.lF(FNAME))
            return dtRes

        targetSeq=str(ret[0]['montargetcatseq'])
        itemKey=str(ret[0]['key'])
        ## 사용 중인지 체크
        ret=rbDB.select(db_sql.GET_ITEM_INST_FOR_DELITEM(itemCatSeq))
        if ret == None:
            rbDB.rollback()
            dtRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Item In-Use Check Error', None, logPara)
            logger.error(dtRes.lF(FNAME))
            return dtRes
        elif not apply_yn and len(ret) > 0:
            rbDB.rollback()
            dtRes=rrl.rFa(tid, rrl.RS_INUSE_DATA, 'Item In-Use', ret, logPara)
            logger.error(dtRes)
            return dtRes

        ## INST DB 제거
        delItemInst(tid, rbDB, itemCatSeq)

        ## ITEM DB 제거
        dtRes=item_handler.removeItem([itemCatSeq], rbDB)
        if dtRes.isFail():
            rbDB.rollback()
            logger.error(dtRes.ltF(FNAME))
            return dtRes

        ## zb에서 제거
        ret=zbm_api.delTemplateItem(logger, targetSeq, itemKey)
        if not ret:
            rbDB.rollback()
            dtRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Delete Item Error', None,
                          {'template': targetSeq, 'item_key': itemKey})
            logger.error(dtRes.lF(FNAME))
            return dtRes

        rbDB.commit()
        dtRes=rrl.rSc(tid, {'tid': tid}, logPara)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


#
#############
def modTargetItemThresheld(tid, params, dbm):
    """
    - FUNC: 감시 대상 카탈로그 수정
    - INPUT
        tid(M): 요청 TID
        params(M): 감시 항목 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 대상 수정 결과
        rrl_handler._ReqResult
    """
    FNAME='Modify Item Catalog'
    rbDB=dbm.getRollBackDB()

    # 임계치 변환

    soRes=web_api.convertThreshold(params, dbm, True)
    if soRes.isFail():
        logger.error(soRes.lF(FNAME))
        return soRes
    thresholdParams=soRes.ret()

    item_seq=params['item_seq']

    try:
        # 임계치 변경은 값이 전달된 경우에만 적용
        for threshold in thresholdParams['threshold']:
            qry=db_sql.UPDATE_TEMPLATE_THRESHOLD(item_seq, json.dumps(threshold['conditions'], encoding='utf-8'),
                                                 threshold['operator'], threshold['repeat'], threshold['grade'])
            dbm.execute(qry)

        dtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


def modTargetItemName(tid, params, dbm):
    """템플릿 감시항목의 감시명 변경
    """
    FNAME='Modify Item Catalog - Name'
    rbDB=dbm.getRollBackDB()

    montargetcatseq=params['montargetcatseq']
    item_seq=params['item_seq']
    item_new_name=params['item_new_name']

    try:
        dbm.execute(db_sql.UPDATE_TEMPLATE_NAME(item_seq, item_new_name))

        dtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


def modTargetItemPeriod(tid, params, dbm):
    """템플릿 감시항목의 감시주기 변경
    """
    FNAME='Modify Item Catalog - Name'
    rbDB=dbm.getRollBackDB()

    item_seq=params['item_seq']
    period=params['new_period']

    try:
        # Zabbix API를 호출하여 템플릿에 속한 아이템의 감시주기 변경
        tmp=(dbm.select(db_sql.GET_TEMPLATE_NAME_BY_SEQ(item_seq)))[0]
        template_name=str(tmp['montargetcatseq'])  # 자빅스에 등록된 템플릿 키는 montargetcatseq 만 등록되어 있다.
        tmp=(dbm.select(db_sql.GET_ITEM_KEY_BY_SEQ(item_seq)))[0]
        key=tmp['key']

        ret=zbm_api.setItemPeriodTemplate(logger, template_name, key, period)

        # 템플릿 아이템의 감시주기 변경
        dbm.execute(db_sql.UPDATE_TEMPLATE_PERIOD(item_seq, period))  # 템플릿에 속한 아이템의 감시주기 갱신

        dbm.execute(db_sql.UPDATE_TEMPLATE_ITEM_PERIOD(item_seq, period))  # 현재 감시중인 아이템의 감시주기 갱신

        dtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


def modTargetItemRealtime(tid, params, dbm):
    """템플릿 감시항목의 실시간감시 상태 변경
    """
    FNAME='Modify Item Catalog - Realtime'
    rbDB=dbm.getRollBackDB()

    item_seq=params['item_seq']
    realtime_yn=params['realtime_yn']

    try:
        qry=db_sql.UPDATE_TEMPLATE_REALTIME(item_seq, realtime_yn)
        dbm.execute(qry)

        dtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


def modTargetItemStatistics(tid, params, dbm):
    """템플릿 감시항목의 통계생성 상태 변경
    """
    FNAME='Modify Item Catalog - Statistics'
    rbDB=dbm.getRollBackDB()

    item_seq=params['item_seq']
    statistics_yn=params['statistics_yn']

    try:
        qry=db_sql.UPDATE_TEMPLATE_STATISTICS(item_seq, statistics_yn)
        dbm.execute(qry)

        dtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


def modTargetItemGuide(tid, params, dbm):
    """템플릿 감시항목의 알람 가이드 상태 변경
    """
    FNAME='Modify Item Catalog - Guide'
    rbDB=dbm.getRollBackDB()

    item_seq=params['item_seq']
    guide=params['guide']

    try:
        qry=db_sql.UPDATE_TEMPLATE_GUIDE(item_seq, guide)
        dbm.execute(qry)

        dtRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(dtRes.lS(FNAME))
        return dtRes
    except Exception, e:
        rbDB.rollback()
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        return dtRes
    finally:
        rbDB.close()


########
def addTargetItem(tid, params, dbm):
    """
    - FUNC: 감시 대상에 감시 항목 추가(감시 중인 서버에 instance가 추가되지는 않음, discovery 항목 같은 경우 서버 별로 object 설정 필요하여 새로 모니터링 시작 필요)
    - INPUT
        tid(M): 요청 TID
        params(M): 감시 항목 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 항목 추가 결과
        rrl_handler._ReqResult
    """
    FNAME='Add ItemCatalog'

    rbDB=dbm.getRollBackDB()
    targetSeq=str(params['target_seq'])
    itemInfo=params['item']

    ## 그룹 정보 설정
    if params.has_key('group_seq'):
        groupSeq=str(params['group_seq'])
    elif params.has_key('group_info'):
        atRes=item_handler.createGroup(targetSeq, params['group_info'], rbDB)
        if atRes.isFail():
            logger.error(atRes.ltF(FNAME))
            return atRes
        groupSeq=atRes.ret()['groupSeq']
    else:
        atRes=rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Group Info', None, params)
        logger.error(atRes.lF(FNAME))
        return atRes

    # monitorYN = ( lambda x: True if x.has_key('monitor_yn') and str(x).lower() == 'y' else False)(params)

    try:
        ## Item DB 적용
        atRes=item_handler.createItem(targetSeq, groupSeq, [itemInfo], rbDB)
        if atRes.isFail():
            rbDB.rollback()
            logger.error(atRes.ltF(FNAME))
            return atRes

        logger.info(rrl.rSc(tid, atRes.ret(), itemInfo, _msg="Add ItemInfo into DB"))

        ## INST 생성 및 OB 배포(X)

        ## zabbix 적용
        ret=rbDB.select(db_sql.GET_GROUP_FOR_ADDITEM(groupSeq))
        if ret == None or len(ret) != 1:
            rbDB.rollback()
            if ret == None:
                resCode=rrl.RS_FAIL_DB
            else:
                resCode=rrl.RS_INVALID_DATA
            atRes=rrl.rFa(tid, resCode, 'Get Group Data Error', ret, {'group_seq': groupSeq})
            logger.error(atRes.lF(FNAME))
            return atRes

        KeyList = []
        isSucc, ret=zbm_api.convertItem(logger, targetSeq, ret[0]['groupname'], [itemInfo], KeyList)
        if not isSucc:
            rbDB.rollback()
            atRes=rrl.rFa(tid, rrl.RS_FAIL_ZB_OP, 'Convert ItemInfo Error', ret, itemInfo)
            logger.error(atRes.lF(FNAME))
            return atRes
        zbItemInfo=ret['item'][0]

        ret=zbm_api.addTemplateItem(logger, targetSeq, zbItemInfo)
        if not ret:
            rbDB.rollback()
            atRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Add ZBTemplateItem Error', ret,
                          {'target_seq': targetSeq, 'item_info': zbItemInfo})
            logger.error(atRes.lF(FNAME))
            return atRes

        rbDB.commit()
        atRes=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(atRes.lS(FNAME))
        return atRes
    except Exception, e:
        rbDB.rollback()
        atRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(atRes.lF(FNAME))
        logger.fatal(e)
        return atRes
    finally:
        rbDB.close()


def getTargetInfo(tid, params, dbm):
    """
    기능 변경으로 인해서 더 이상 사용하지 않는다.
    기존에는 오케스트레이터-F에서 onboarding 시 VNF의 이름과 버전 정보를 전달하여 Template의 ID를 매핑했으나,
    기능 변경으로 인해서 Template의 ID 전달하는 방식으로 변경되었다.
    본 코드는 참조용으로 그냥 남겨둔다.

    - FUNC: 모니터링 템플릿 정보 조회
    - INPUT
        tid(M): 요청 TID
        params(M): 모니터링 템플릿 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 모니터링 템플릿 리스트
        rrl_handler._ReqResult
    """
    FNAME='Get TargetInfo'
    rbDB=dbm.getRollBackDB()
    try:
        vdudList=params['vdud_list']
        targetList=[]
        for vdudInfo in vdudList:
            vdudSeq=vdudInfo['vdud_seq']
            vdudType=vdudInfo['vdud_type']
            vdudVendor=vdudInfo['vdud_vendor']
            vdudVer=vdudInfo['vdud_version']
            isTest=(lambda x: True if x.has_key('test_yn') and str(x['test_yn']).upper() == 'Y' else False)(vdudInfo)
            ret=rbDB.select(db_sql.GET_TARGET_SEQ_BY_VDUD(vdudType, vdudVendor, vdudVer, isTest))
            if ret == None or len(ret) < 1:
                rbDB.rollback()
                if ret == None:
                    resCode=rrl.RS_FAIL_DB
                else:
                    resCode=rrl.RS_NO_DATA
                gtRes=rrl.rFa(tid, resCode, 'Get Target(VDUD) Error', ret, vdudInfo)
                logger.error(gtRes.lF(FNAME))
                return gtRes
            elif len(ret) != 1:
                #                 rbDB.rollback()
                gtRes=rrl.rFa(tid, rrl.RS_DUPLICATE_DATA, 'Duplicated TargetInfo', ret, vdudInfo)
                logger.warning(gtRes.lL(FNAME))
            # return gtRes

            targetSeq=ret[0]['montargetcatseq']
            ret=rbDB.execute(db_sql.UPDATE_TARGET_VDUDSEQ(targetSeq, vdudSeq))
            if ret == None:
                rbDB.rollback()
                gtRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Target VDUD Seq Error', ret,
                              {'target_seq': targetSeq, 'vdud_seq': vdudSeq})
                logger.error(gtRes.lF(FNAME))
                return gtRes

            targetList.append({'vdud_seq': vdudSeq, 'target_seq': targetSeq})

        rbDB.commit()
        gtRes=rrl.rSc(tid, {'tid': tid, 'target_list': targetList}, params)
        logger.info(gtRes.lS(FNAME))
        return gtRes
    except Exception, e:
        rbDB.rollback()
        gtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, params)
        logger.error(gtRes.lF(FNAME))
        logger.fatal(e)
        return gtRes
    finally:
        rbDB.close()


def extractTarget(tid, targetSeq, dbm):
    """
    - FUNC: 모니터링 템플릿 추출 후 json으로 변경
    - INPUT
        tid(M): 요청 TID
        targetSeq(M): 모니터링 템플릿 시퀀스
        dbm(M): DB 연결 객체
    - OUTPUT: 모니터링 템플릿 추출 결과
        rrl_handler._ReqResult
    """
    FNAME='Target Extract'
    param={'target_seq': targetSeq}

    try:
        def _res(_bool, _ret, _resCode, _name, _param):
            if _bool:
                if _ret == None:
                    rc=rrl.RS_FAIL_DB
                else:
                    rc=_resCode
                rres=rrl.rFa(tid, rc, _name, _ret, _param)
                logger.error(rres.lF(FNAME))
                return rres
            else:
                return None

        def _set(dic, field, value, isJson=False):
            if isJson and value != None:
                dic[field]=json.loads(value, encoding='utf-8')
            elif not isJson and value != None:
                dic[field]=value

        ### Target 정보
        _ret=dbm.select(db_sql.GET_TARGET_INFO(targetSeq))
        ret=_res((_ret == None or len(_ret) < 1), _ret, rrl.RS_NO_DATA, 'Get Target Info Error', param)
        if ret != None: return ret

        _retT=_ret[0]
        targetInfo={}
        _set(targetInfo, 'code', _retT['targetcode'])
        _set(targetInfo, 'type', _retT['targettype'])
        _set(targetInfo, "name", _retT['targetname'])
        _set(targetInfo, 'visible', _retT['visiblename'])
        _set(targetInfo, 'model', _retT['targetmodel'])
        _set(targetInfo, 'vdud_version', _retT['vdudversion'])
        _set(targetInfo, 'vendor_code', _retT['vendorcode'])
        _set(targetInfo, 'description', _retT['description'])
        _set(targetInfo, 'version', _retT['targetversion'])
        _set(targetInfo, 'target_for', _retT['targetfor'])

        ### 그룹 정보
        _ret=dbm.select(db_sql.GET_GROUP_INFO(targetSeq))
        ret=_res((_ret == None), _ret, rrl.RS_FAIL_DB, 'Get Group Info Error', param)
        if ret != None: return ret

        groupList=[]
        for ret in _ret:
            grpSeq=ret['mongroupcatseq']
            tmpGrp={}
            _set(tmpGrp, 'name', ret['groupname'])
            _set(tmpGrp, 'visible', ret['visiblename'])
            _set(tmpGrp, 'description', ret['description'])

            ### 일반 Item
            ## Item 정보
            iList=dbm.select(db_sql.GET_ITEM_INFO_FOR_EXTRACT(grpSeq))
            ret=_res((iList == None), iList, rrl.RS_FAIL_DB, 'Get Item Info Error', {'group_seq': grpSeq})
            if ret != None: return ret

            if len(iList) > 0:
                itemList=[]
                for _item in iList:
                    item={}
                    _set(item, 'name', _item['monitoritem'])
                    _set(item, 'visible', _item['visiblename'])
                    _set(item, 'type', _item['monitortype'])
                    _set(item, 'period', _item['period'])
                    _set(item, 'history', _item['hist_save_month'])
                    _set(item, 'statistic', _item['stat_save_month'])
                    _set(item, 'monitor_method', _item['monitor_method'])
                    _set(item, 'data_type', _item['data_type'])
                    _set(item, 'value_type', _item['value_type'])
                    _set(item, 'unit', _item['unit'])
                    _set(item, 'graph_yn', _item['graphyn'])
                    _set(item, 'realtime_yn', _item['realtimeyn'])
                    _set(item, 'description', _item['description'])

                    ## PlugIn 정보
                    if _item['monplugincatseq'] != None:
                        plugIn={}
                        _set(plugIn, 'name', _item['pc_name'])
                        _set(plugIn, 'type', _item['pc_type'])
                        _set(plugIn, 'script', _item['pc_script'])
                        _set(plugIn, 'param_num', _item['pc_parameter_num'])
                        _set(plugIn, 'plugin_param', _item['pc_plugin_params'], True)
                        _set(plugIn, 'description', _item['pc_description'])
                        _set(plugIn, 'lib_type', _item['pc_libtype'])
                        _set(plugIn, 'lib_script', _item['pc_libscript'])
                        _set(plugIn, 'lib_name', _item['pc_libname'])
                        _set(plugIn, 'lib_path', _item['pc_libpath'])
                        _set(plugIn, 'cfg_name', _item['pc_cfgname'])
                        _set(plugIn, 'cfg_path', _item['pc_cfgpath'])
                        _set(plugIn, 'cfg_input', _item['pc_cfg_input'], True)
                        item['plugin']=plugIn
                    ## ZB Key 사용 정보
                    elif _item['plugintype'] == 'zabbix':
                        _set(item, 'zb_type', _item['km_type'])

                    ## 장애 Guide 정보
                    if _item['monalarmguideseq'] != None:
                        alarmGuide={}
                        _set(alarmGuide, 'name', _item['ag_name'])
                        _set(alarmGuide, 'guide', _item['ag_guide'])
                        item['alarm_guide']=alarmGuide

                    ## 임계치 정보
                    tList=dbm.select(db_sql.GET_THRES_CAT(_item['monitemcatseq']))
                    ret=_res((tList == None), tList, rrl.RS_FAIL_DB, 'Get Threshold Info Error',
                             {'item_cat_seq': _item['monitemcatseq']})
                    if len(tList) > 0:
                        thrList=[]
                        for _thr in tList:
                            thr={}
                            _set(thr, 'name', _thr['threshold_name'])
                            _set(thr, 'grade', _thr['fault_grade'])
                            _set(thr, 'description', _thr['description'])
                            _set(thr, 'repeat', _thr['repeat'])
                            _set(thr, 'conditions', _thr['condition'], True)
                            thrList.append(thr)

                        item["threshold"]=thrList

                    itemList.append(item)

                tmpGrp['item']=itemList

            ### discovery item
            ## Discovery 정보
            dList=dbm.select(db_sql.GET_DISC_INFO_FOR_EXTRACT(grpSeq))
            ret=_res((dList == None), dList, rrl.RS_FAIL_DB, 'Get Disc Info Error', {'group_seq': grpSeq})
            if ret != None: return ret

            if len(dList) > 0:
                discList=[]
                for _disc in dList:
                    dSeq=_disc['zbdiscoverycatseq']
                    disc={}
                    _set(disc, 'name', _disc['name'])
                    _set(disc, 'period', _disc['period'])
                    _set(disc, 'remain', _disc['hist_save_day'])
                    _set(disc, 'description', _disc['description'])
                    _set(disc, 'return_field', _disc['return_field'])
                    _set(disc, 'monitor_method', _disc['monitor_method'])

                    ## Discovery PlugIn 정보
                    if _disc['monplugincatseq'] != None:
                        plugIn={}
                        _set(plugIn, 'name', _disc['pc_name'])
                        _set(plugIn, 'type', _disc['pc_type'])
                        _set(plugIn, 'script', _disc['pc_script'])
                        _set(plugIn, 'param_num', _disc['pc_parameter_num'])
                        _set(plugIn, 'plugin_param', _disc['pc_plugin_params'], True)
                        _set(plugIn, 'description', _disc['pc_description'])
                        _set(plugIn, 'lib_type', _disc['pc_libtype'])
                        _set(plugIn, 'lib_script', _disc['pc_libscript'])
                        _set(plugIn, 'lib_name', _disc['pc_libname'])
                        _set(plugIn, 'lib_path', _disc['pc_libpath'])
                        _set(plugIn, 'cfg_name', _disc['pc_cfgname'])
                        _set(plugIn, 'cfg_path', _disc['pc_cfgpath'])
                        _set(plugIn, 'cfg_input', _disc['pc_cfg_input'], True)
                        _set(plugIn, 'discovery_input', _disc['pc_discovery_cfg_input'])
                        disc['plugin']=plugIn
                    ## Discovery ZB Key 사용 정보
                    elif _disc['plugintype'] == 'zabbix':
                        _set(disc, 'zb_type', _disc['km_type'])

                    ## Disc Item 정보
                    diList=dbm.select(db_sql.GET_D_ITEM_INFO_FOR_EXTRACT(dSeq))
                    ret=_res((diList == None), diList, rrl.RS_FAIL_DB, 'Get Disc Item Info Error', {'disc_seq': dSeq})
                    if ret != None: return ret

                    if len(diList) > 0:
                        dItemList=[]
                        for _dItem in diList:
                            dItem={}
                            _set(dItem, 'name', _dItem['monitoritem'])
                            _set(dItem, 'visible', _dItem['visiblename'])
                            _set(dItem, 'type', _dItem['monitortype'])
                            _set(dItem, 'period', _dItem['period'])
                            _set(dItem, 'history', _dItem['hist_save_month'])
                            _set(dItem, 'statistic', _dItem['stat_save_month'])
                            _set(dItem, 'monitor_method', _dItem['monitor_method'])
                            _set(dItem, 'data_type', _dItem['data_type'])
                            _set(dItem, 'value_type', _dItem['value_type'])
                            _set(dItem, 'unit', _dItem['unit'])
                            _set(dItem, 'graph_yn', _dItem['graphyn'])
                            _set(dItem, 'realtime_yn', _dItem['realtimeyn'])
                            _set(dItem, 'description', _dItem['description'])

                            ## Disc Item PlugIn 정보
                            if _dItem['monplugincatseq'] != None:
                                plugIn={}
                                _set(plugIn, 'name', _dItem['pc_name'])
                                _set(plugIn, 'type', _dItem['pc_type'])
                                _set(plugIn, 'script', _dItem['pc_script'])
                                _set(plugIn, 'param_num', _dItem['pc_parameter_num'])
                                _set(plugIn, 'plugin_param', _dItem['pc_plugin_params'], True)
                                _set(plugIn, 'description', _dItem['pc_description'])
                                _set(plugIn, 'lib_type', _dItem['pc_libtype'])
                                _set(plugIn, 'lib_script', _dItem['pc_libscript'])
                                _set(plugIn, 'lib_name', _dItem['pc_libname'])
                                _set(plugIn, 'lib_path', _dItem['pc_libpath'])
                                _set(plugIn, 'cfg_name', _dItem['pc_cfgname'])
                                _set(plugIn, 'cfg_path', _dItem['pc_cfgpath'])
                                _set(plugIn, 'cfg_input', _dItem['pc_cfg_input'], True)
                                dItem['plugin']=plugIn
                            ## ZB Key 사용 정보
                            elif _dItem['plugintype'] == 'zabbix':
                                _set(dItem, 'zb_type', _dItem['km_type'])

                            ## 장애 Guide 정보
                            if _dItem['monalarmguideseq'] != None:
                                alarmGuide={}
                                _set(alarmGuide, 'name', _dItem['ag_name'])
                                _set(alarmGuide, 'guide', _dItem['ag_guide'])
                                dItem['alarm_guide']=alarmGuide

                            ## 임계치 정보
                            tList=dbm.select(db_sql.GET_THRES_CAT(_dItem['monitemcatseq']))
                            ret=_res((tList == None), tList, rrl.RS_FAIL_DB, 'Get Threshold Info Error',
                                     {'item_cat_seq': _dItem['monitemcatseq']})
                            if len(tList) > 0:
                                thrList=[]
                                for _thr in tList:
                                    thr={}
                                    _set(thr, 'name', _thr['threshold_name'])
                                    _set(thr, 'grade', _thr['fault_grade'])
                                    _set(thr, 'description', _thr['description'])
                                    _set(thr, 'repeat', _thr['repeat'])
                                    _set(thr, 'conditions', _thr['condition'], True)
                                    thrList.append(thr)

                                dItem["threshold"]=thrList

                            dItemList.append(dItem)

                        disc['item']=dItemList

                    discList.append(disc)

                tmpGrp['discovery']=discList

            groupList.append(tmpGrp)

        res={'target_info': targetInfo, 'group': groupList}
        etRes=rrl.rSc(tid, res, param)
        logger.info(etRes.lS(FNAME))
        return etRes
    except Exception, e:
        etRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, param)
        logger.error(etRes.lF(FNAME))
        logger.fatal(e)
        return etRes


def _delTemplateInfo(tid, e2e, svr_seq, svr_obid, ob_ip, dbm, remainList=None, target_list=None):
    """
    - FUNC: 모니터링 해제
    - INPUT
        tid(M): 요청 TID
        e2e(O): E2E log 객체
        svr_seq(M): 서버 시퀀스
        svr_obid(M): 서버 OB ID
        ob_ip(M): 서버 OBAgent IP
        dbm(M): DB 연결 객체
        remainList(O): 남겨둘 모니터링 템플릿(None일 경우 서버 제거로 인지)
        target_list(O): 제거할 모니터링 템플릿
    """
    FNAME='Delete TargetInfo'

    ret=None

    ## zabbix에서 제거
    if remainList == None:
        ret=zbm_api.delHost(logger, svr_obid)
        if ret:
            logger.info(rrl.rSc(tid, None, {'host': svr_obid}, _msg='Delete Zabbix Host').lS(FNAME))
            if e2e != None:
                e2e.job('서버 제거 완료(zabbix)', e2e_logger.CONST_TRESULT_SUCC)
        else:
            logger.error(
                rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Delete Zabbix Host Error', None, {'host': svr_obid}).lF(FNAME))
            if e2e != None:
                e2e.job('서버 제거 실패(zabbix)', e2e_logger.CONST_TRESULT_FAIL)

    else:
        ret=zbm_api.modHost(logger, svr_obid, remainList)
        if ret:
            logger.info(
                rrl.rSc(tid, None, {'host': svr_obid, 'remain_template': remainList}, _msg='Modify Zabbix Template').lS(
                    FNAME))
            if e2e != None:
                e2e.job('서버 탬플릿 변경 완료(zabbix)', e2e_logger.CONST_TRESULT_SUCC)
        else:
            logger.error(rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Modify Zabbix Template Error', None,
                                 {'host': svr_obid, 'remain_template': remainList}).lF(FNAME))
            if e2e != None:
                e2e.job('서버 탬플릿 변경 실패(zabbix)', e2e_logger.CONST_TRESULT_FAIL)

    ## zabbix Item 삭제
    if target_list != None:
        ## Item 제거
        iKeyList=dbm.select(db_sql.GET_KEY_INST_BY_TEMP(svr_seq, target_list), 'monitemkey')
        undelIKey=[]
        for iKey in iKeyList:
            ret=zbm_api.delHostItem(logger, svr_obid, iKey)
            if not ret:
                logger.error(rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Remove Zabbix HostItem Error', None,
                                     {'host': svr_obid, 'item_key': iKey}).lL(FNAME))
                undelIKey.append(iKey)

        if e2e != None:
            if len(undelIKey) > 0:
                e2e.job('서버 감시항목 제거 실패(zabbix), 실패항목:%s' % str(undelIKey), e2e_logger.CONST_TRESULT_FAIL)
            else:
                e2e.job('서버 감시항목 제거 성공(zabbix)', e2e_logger.CONST_TRESULT_SUCC)

        ## Discovery 제거
        dKeyList=dbm.select(db_sql.GET_DISC_KEY(target_list), 'zbkey')
        undelDKey=[]
        for dKey in dKeyList:
            ret=zbm_api.delHostDiscovery(logger, svr_obid, dKey)
            if not ret:
                logger.error(rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Remove Zabbix HostDiscovery Error', None,
                                     {'host': svr_obid, 'disc_key': dKey}).lL(FNAME))
                undelDKey.append(dKey)

        if e2e != None:
            if len(undelDKey) > 0:
                e2e.job('서버 탐색항목 제거 실패(zabbix), 실패항목:%s' % str(undelDKey), e2e_logger.CONST_TRESULT_FAIL)
            else:
                e2e.job('서버 탐색항목 제거 성공(zabbix)', e2e_logger.CONST_TRESULT_SUCC)

    ## One-Box에서 파일 제거
    delFileList=[]
    delFileList+=dbm.select(db_sql.GET_PLUGIN_INST(svr_seq, target_list), 'del_file')
    delFileList+=dbm.select(db_sql.GET_PLUGIN_INST_LIB(svr_seq, target_list), 'del_file')
    delFileList+=dbm.select(db_sql.GET_PLUGIN_INST_CFG(svr_seq, target_list), 'del_file')
    delFileList+=dbm.select(db_sql.GET_ZBACONFIG_CFG(svr_seq, target_list), 'del_file')
    logger.info(rrl.rSc(tid, None, {'del_file': delFileList}, _msg='Delete One-Box File').lL(FNAME))
    dtRes=oba_api.delFile(delFileList, ob_ip, oba_port, _backupDir)
    if dtRes.isSucc():
        logger.info(dtRes.setMsg('Delete One-Box File').lS(FNAME))
        if e2e != None:
            e2e.job('서버 감시 관련 파일 제거 완료', e2e_logger.CONST_TRESULT_SUCC)
    else:
        logger.error(dtRes.ltF(FNAME))
        if e2e != None:
            e2e.job('서버 감시 관련 파일 제거 실패', e2e_logger.CONST_TRESULT_FAIL)

    ## zabbix Agent restart
    dtRes=oba_api.restartZBA(ob_ip, oba_port)
    if dtRes.isSucc():
        logger.info(dtRes.setMsg('Restart Zabbix Agent').lS(FNAME))
        if e2e != None:
            e2e.job('서버 Zabbix Agent 재기동 완료', e2e_logger.CONST_TRESULT_SUCC)
    else:
        logger.error(dtRes.ltF(FNAME))
        if e2e != None:
            e2e.job('서버 Zabbix Agent 재기동 실패', e2e_logger.CONST_TRESULT_FAIL)

    ### Orch-M DB에서 제거
    def _log(_ret, _name, _e2eName, _param):
        if _ret == None:
            logger.error(rrl.rFa(tid, rrl.RS_FAIL_DB, _name + ' Error', None, _param).lF(FNAME))
            if e2e != None and _e2eName != None:
                e2e.job(_e2eName + ' 실패', e2e_logger.CONST_TRESULT_FAIL)
        else:
            logger.info(rrl.rSc(tid, {'cnt': ret}, _param, _msg=_name).lS(FNAME))
            if e2e != None and _e2eName != None:
                e2e.job(_e2eName + ' 완료', e2e_logger.CONST_TRESULT_SUCC)

    ## curr/hist 알람 장애 미조치 내역 내용 변경 -> 서비스 해지
    ret=dbm.execute(db_sql.UPDATE_CURR_ALARM_FOR_DEL_SVR(svr_obid, target_list, '서비스 해지'))
    _log(ret, 'Update Current Alarm', '최근 장애 데이터 서비스 해지 처리', {'svr_obid': svr_obid, 'target_list': target_list})
    ret=dbm.execute(db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE())
    _log(ret, 'Update History Alarm', '장애 이력 데이터 동기화', None)

    # Threshold Instance 제거
    ret=dbm.execute(db_sql.REMOVE_THRESHOLD_INST(svr_seq, target_list))
    _log(ret, 'Remove Threshold Instance', '장애 임계치 데이터 제거', {'svr_seq': svr_seq, 'target_list': target_list})

    # Key Instance 제거
    ret=dbm.execute(db_sql.REMOVE_KEYINSTANCE(svr_seq, target_list))
    _log(ret, 'Remove Zabbix Key Instance', '감시 항목 Key 데이터 제거', {'svr_seq': svr_seq, 'target_list': target_list})

    # Item Instance 제거
    ret=dbm.execute(db_sql.DEL_ITEMINSTANCE(svr_seq, target_list))
    _log(ret, 'Delete Item Instance', '감시 항목 데이터 제거', {'svr_seq': svr_seq, 'target_list': target_list})

    # RealTime 성능 제거
    ret=dbm.execute(db_sql.REMOVE_REALTIMEPERF(svr_seq, target_list))
    _log(ret, 'Remove RealTime PerfData', '실시간 성능 데이터 제거', {'svr_seq': svr_seq, 'target_list': target_list})

    ## WEB Mapping 정보 삭제
    if remainList == None:
        ret=dbm.execute(db_sql.REMOVE_WEB_MAPPING(svr_seq))
        _log(ret, 'Remove WebMapping Info', '종합상황판 Mapping 데이터 서버 제거', {'svr_seq': svr_seq})
    else:
        ret=dbm.execute(db_sql.DEL_VIEW_INST_SEQ(svr_seq))
        _log(ret, 'Delete WebMapping Info', '종합상황판 Mapping 데이터 항목 제거', {'svr_seq': svr_seq})

    # Host Instance 제거
    if remainList == None:
        ret=dbm.execute(db_sql.REMOVE_HOSTINSTANCE_BY_SERVER(svr_seq))
        _log(ret, 'Remove Host Instance', '감시 대상 서버 데이터 제거', {'svr_seq': svr_seq})

    # Zabbix Config 제거
    ret=dbm.execute(db_sql.REMOVE_ZBACONFIGINSTANCE(svr_seq, target_list))
    _log(ret, 'Remove ZBAgent Config', 'zabbix agent 설정 데이터 제거', {'svr_seq': svr_seq, 'target_list': target_list})

    # PlugIn Instance 제거
    ret=dbm.execute(db_sql.DEL_PLUGININSTANCE(svr_seq, target_list))
    _log(ret, 'Delete PlugIn Instance', '감시 PlugIn 데이터 제거', {'svr_seq': svr_seq, 'target_list': target_list})

    # 17.10.25 - tb_smsschedule 에서 삭제
    ret=dbm.execute(db_sql.DEL_SMSSCHEDULE (svr_seq))
    _log(ret, 'Delete smsschedule ', 'SMS 스케쥴 서버 제거', {'svr_seq': svr_seq})

    # 안쓰는 RealTime Item 제거
    ret=dbm.execute(db_sql.REMOVE_REALTIME_ITEM_UNUSED())
    _log(ret, 'Remove Unused RealTime PerfData', None, None)

    # 안쓰는 Item Instance 제거
    ret=_delRowNoUse('tb_moniteminstance', 'moniteminstanceseq', dbm)
    _log(ret, 'Remove Unused Item Instance', None, None)

    # 안쓰는 PlugIn Instance 제거
    _delRowNoUse('tb_monplugininstance', 'monplugininstanceseq', dbm)
    _log(ret, 'Remove Unused PlugIn Instance', None, None)

    return


def _delTarget(tid, de2e, svr_seq, svr_obid, ob_ip, targetList, dbm):
    """
    - FUNC: 모니터링 템플릿 해제
    - INPUT
        tid(M): 요청 TID
        de2e(O): E2E 로그 객체
        svr_seq(M): 서버 시퀀스
        svr_obid(M): 서버 OB ID
        ob_ip(M): 서버 OBAgent IP
        target_list(M): 제거할 모니터링 템플릿
        dbm(M): DB 연결 객체
    - OUTPUT: 템플릿 해제 결과
        rrl_handler._ReqResult
    """
    FNAME='Release Target'

    target_list=None
    if len(targetList) > 1:
        target_list=str(tuple(targetList))
    elif len(targetList) == 1:
        target_list='(%s)' % targetList[0]
    else:
        dtRes=rrl.rFa(tid, rrl.RS_NO_PARAM, 'No TargetSeq', None, targetList)
        logger.error(dtRes.lF(FNAME))
        if de2e != None:
            de2e.job('감시 템플릿 정보 오류', e2e_logger.CONST_TRESULT_FAIL, '감시 템플릿 정보 없음')
        return dtRes

    getTargetSql=db_sql.GET_TARGET_BY_SVR(svr_seq)
    ret=dbm.select(getTargetSql, 'target_seq')
    remainList=[]
    for target in ret:
        tarSeq=str(target)
        if not tarSeq in targetList:
            remainList.append(tarSeq)

    _delTemplateInfo(tid, de2e, svr_seq, svr_obid, ob_ip, dbm, remainList, target_list)
    dtRes=rrl.rSc(tid, None, targetList)
    logger.info(dtRes.lS(FNAME))
    return dtRes


def delServer(tid, tPath, e2eUrl, _svrInfo, dbm):
    """
    - FUNC: 서버 모니터링 해제
    - INPUT
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        _svrInfo(M): 서버 시퀀스, 서버 OB ID, 서버 IP
        dbm(M): DB 연결 객체
    - OUTPUT: 서버 모니터링 해제 결과
        rrl_handler._ReqResult
    """
    e2e=None
    if tPath != None:
        e2e=e2e_logger.e2elogger('서버 주소 변경', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    try:
        svrInfo=mon_msg.SvrInfo
        if _svrInfo != None: svrInfo=_svrInfo
        _delTemplateInfo(tid, e2e, svrInfo.svrSeq, svrInfo.svrObid, svrInfo.svrIP, dbm)
        dsRes=rrl.rSc(tid, {'tid': tid}, {'svr_seq': svrInfo.svrSeq})
        logger.info(dsRes.lS('Delete Server'))
        sleep(3)
        return dsRes
    except Exception, e:
        dsRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, {'svr_seq': svrInfo.svrSeq})
        logger.error(dsRes.lF('Delete Server'))
        logger.fatal(e)
        if e2e != None:
            e2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, str(e))
        return dsRes


def modServer(tid, tPath, e2eUrl, _svrModInfo, dbm):
    """
    - FUNC: 서버 모니터링 해제
    - INPUT
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        _svrModInfo(M): 서버 시퀀스, 변경된 서버 IP, 변경 사유
        dbm(M): DB 연결 객체
    - OUTPUT: 서버 모니터링 해제 결과
        rrl_handler._ReqResult
    """
    FNAME='Modify Server'

    e2e=None
    if tPath != None:
        e2e=e2e_logger.e2elogger('서버 주소 변경', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    svrModInfo=mon_msg.SvrModInfo
    if _svrModInfo != None:
        svrModInfo=_svrModInfo

    try:
        ret=dbm.select(db_sql.GET_SERVER_INFO(svrModInfo.svrSeq))
        if ret == None:
            mdRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Get Server Info Error', None, svrModInfo)
            logger.error(mdRes.lF(FNAME))
            if e2e != None:
                e2e.job('서버 정보 조회 실패', e2e_logger.CONST_TRESULT_FAIL, '서버 정보 조회 DB 오류')
            return mdRes
        if len(ret) != 1:
            mdRes=rrl.rFa(tid, rrl.RS_INVALID_DATA, 'Get Server Info Error', ret, svrModInfo)
            logger.error(mdRes.lF(FNAME))
            if e2e != None:
                e2e.job('서버 정보 조회 실패', e2e_logger.CONST_TRESULT_FAIL, '유효하지 않은 서버 정보(없는 정보이거나 중복된 정보)')
            return mdRes
        svrInfo=ret[0]
        if e2e != None:
            e2e.job('서버 정보 조회 완료', e2e_logger.CONST_TRESULT_SUCC)

        rbDB=dbm.getRollBackDB()
        ret=rbDB.execute(db_sql.UPDATE_SERVER_ADDR(svrModInfo.svrSeq, svrModInfo.svrNewIP, svrModInfo.svrModDesc))
        if ret == None:
            mdRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Server IP Error', None, svrModInfo)
            logger.error(mdRes.lF(FNAME))
            if e2e != None:
                e2e.job('서버 주소 업데이트 실패', e2e_logger.CONST_TRESULT_FAIL, '서버 주소 DB 업데이트 실패')
            return mdRes
        if e2e != None:
            e2e.job('서버 주소 업데이트 완료', e2e_logger.CONST_TRESULT_SUCC)

        ret=zbm_api.modHostAddr(logger, svrInfo['onebox_id'], svrInfo['mgmtip'], svrModInfo.svrNewIP, str(svrInfo['zbaport']))

        if not ret:
            rbDB.rollback()
            mdRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Modify ZB Server Info Error', ret,
                          {'host': svrInfo['onebox_id'], 'host_prev_ip': svrInfo['mgmtip'],
                           'host_new_ip': svrModInfo.svrNewIP})
            logger.error(mdRes.lF(FNAME))
            if e2e != None:
                e2e.job('서버 주소 변경 실패(zabbix)', e2e_logger.CONST_TRESULT_FAIL, 'zabbix 시스템의 서버 주소 변경 실패')
            return mdRes
        if e2e != None:
            e2e.job('서버 주소 변경 완료(zabbix)', e2e_logger.CONST_TRESULT_SUCC)

        rbDB.commit()
        mdRes=rrl.rSc(tid, {'tid': tid}, svrModInfo)
        logger.info(mdRes.lS(FNAME))
        sleep(3)
        return mdRes
    except Exception, e:
        mdRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, svrModInfo)
        logger.error(mdRes.lF(FNAME))
        logger.fatal(e)
        if e2e != None:
            e2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, str(e))

        return mdRes


def addServer(src, tid, tPath, e2eUrl, _monInfo, dbm):
    """
    - FUNC: 서버 모니터링 시작
    - INPUT
        src(M): 요청 서버 IP
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        _monInfo(M): 서버와 모니터링할 템플릿 정보
        dbm(M): DB 연결 객체
    """
    FNAME='Add Server'

    e2e=None
    if tPath != None:
        e2e=e2e_logger.e2elogger('서버 모니터링 시작', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    monInfo=mon_msg.MonInfo
    req_handler.saveRequestStatus(dbm, src, tid, 'READY', 'CONVERT_PARAM', 1)
    adRes=orchf_api.convertOneTouchParam(_monInfo)
    if adRes.isFail():
        logger.error(adRes.setErr('Convert Parameters Error').ltF(FNAME))
        req_handler.saveRequestFail(dbm, src, tid, adRes.errStr())
        if e2e != None:
            e2e.job('파라미터 변환 실패', e2e_logger.CONST_TRESULT_FAIL, adRes.errStr(), None, '모니터링 시스템 파라미터로 변환')
        return
    else:
        monInfo=adRes.ret()

    req_handler.saveRequestState(dbm, src, tid, 'PARSE_PARAM_2', 5)
    svrInfo=monInfo.svrInfo
    svr_seq=svrInfo.svrSeq
    svrUuid=svrInfo.svrUuid
    svrIP=svrInfo.svrIP
    svrOBID=svrInfo.svrObid


    if e2e != None:
        e2e.job('파라미터 변환 완료', e2e_logger.CONST_TRESULT_SUCC, None, None, '모니터링 시스템 파라미터로 변환')

    rbDB=dbm.getRollBackDB()
    try:
        def _res(_bool, _ret, _resCode, _name, _reqRes, _param):

            if _bool:
                rbDB.rollback()
                if _ret == None:
                    rc=rrl.RS_FAIL_DB
                else:
                    rc=_resCode
                _asRes=rrl.rFa(tid, rc, _name, _ret, _param)
                logger.error(_asRes.lF(FNAME))
                req_handler.saveRequestFail(dbm, src, tid, _reqRes)
                return False
            else:
                return True

        ## 이미 있는 서버인지 체크
        svrExistSql=db_sql.GET_SERVER_CNT_BY_SEQ(svr_seq)
        ret=rbDB.select(svrExistSql)
        if not _res((ret == None or len(ret) > 0), ret, rrl.RS_ALREADY_EXIST, 'Check Server Error',
                    'Already Existed Server', {'svr_seq': svr_seq}):
            if e2e != None:
                e2e.job('서버 데이터 유효성 점검 실패', e2e_logger.CONST_TRESULT_FAIL, '서버 데이터 중복 또는 조회 실패', None, '중복된 서버 데이터 체크')
            return

        ## 요청 서버에 대한 감시되는 아이템이 기존에 있는지 확인
        svrItemExistSql=db_sql.GET_ITEM_CNT_BY_SERVER(svr_seq)
        ret=rbDB.select(svrItemExistSql)
        if not _res((ret == None or len(ret) > 0), ret, rrl.RS_ALREADY_EXIST, 'Check HostItem Error',
                    'Already Existed HostItem', {'svr_seq': svr_seq}):
            if e2e != None:
                e2e.job('감시 항목 데이터 유효성 점검 실패', e2e_logger.CONST_TRESULT_FAIL, '감시 항목 데이터 중복 또는 조회 실패', None,
                        '중복된 감시 항목 데이터 체크')
            return

        ## 요청 서버에 대한 사용중인 Key 정보가 있는지 확인
        svrKeyExistSql=db_sql.GET_KEY_CNT_BY_SERVER(svr_seq)
        ret=rbDB.select(svrKeyExistSql)
        if not _res((ret == None or len(ret) > 0), ret, rrl.RS_ALREADY_EXIST, 'Check HostItem Key Error',
                    'Already Existed HostItem Key', {'svr_seq': svr_seq}):
            if e2e != None:
                e2e.job('감시 항목 Key 데이터 유효성 점검 실패', e2e_logger.CONST_TRESULT_FAIL, '감시 항목 Key 데이터 중복 또는 조회 실패', None,
                        '중복된 감시 항목 Key 데이터 체크')
            return

        if e2e != None:
            e2e.job('데이터 유효성 점검 완료', e2e_logger.CONST_TRESULT_SUCC, None, None, '데이터 중복 체크')

        ## 서버 Inst 추가
        req_handler.saveRequestStatus(dbm, src, tid, 'ADD SVR', 'REGISTER_SERVER', 15)
        zbaPort=zba_port
        if svrInfo.svrZbaPort != None:
            zbaPort=svrInfo.svrZbaPort

        logger.info( '===== INSERT SERVER : %s =====' % svr_seq )

        addHostSql=db_sql.INSERT_SERVER(svr_seq, svrUuid, svrOBID, svrIP, zbaPort)
        ret=rbDB.execute(addHostSql)
        if not _res((ret == None or ret < 1), ret, rrl.RS_FAIL_DB, 'Insert ServerInfo Error', 'ServerInfo Insert Error',
                    {'svr_seq': svr_seq, 'svr_uuid': svrUuid, 'svr_obid': svrOBID, 'svr_ip': svrIP,
                     'zba_port': zbaPort}):
            if e2e != None:
                e2e.job('서버 데이터 추가 실패', e2e_logger.CONST_TRESULT_FAIL, '서버 데이터 추가 실패 또는 DB 오류', None, '서버 데이터 추가')
            return

        if e2e != None:
            e2e.job('서버 데이터 추가 완료', e2e_logger.CONST_TRESULT_SUCC, None, None, '서버 데이터 추가')

        ## 서버 타입 GET
        req_handler.saveRequestStatus(dbm, src, tid, 'ADD SVR', 'REGISTER_WEB_MAPING_INFO', 17)
        ret=rbDB.select(db_sql.GET_SERVER_TYPE(svr_seq), 'svr_type')
        if not _res((ret == None or len(ret) != 1), ret, rrl.RS_INVALID_DATA, 'Invalid Server Infor',
                    'Server Type Error', {'svr_seq': svr_seq}):
            if e2e != None:
                e2e.job('서버 타입 조회 실패', e2e_logger.CONST_TRESULT_FAIL, '유효하지 않은 서버 타입 데이터 또는 조회 실패', None,
                        '종합상황판 표시를 위한 서버 타입 조회')
            return

        ## 성능 모니터링 매핑 정보 초기화
        svrType=ret[0]
        logger.info( '===== svrType %s =====' % svrType )
        if str(svrType).lower() in [ 'one-box', 'ktpnf', 'ktarm' ]:

            ret=rbDB.execute(db_sql.INSERT_VIEW_INST_INIT(svr_seq))

            if not _res((ret == None or ret < 1), ret, rrl.RS_INVALID_DATA, 'WEB Mapping Info Init Error',
                        'WEB Mapping Info Init Error', {'svr_seq': svr_seq}):
                if e2e != None:
                    e2e.job('종합상황판  Mapping 데이터 추가 실패', e2e_logger.CONST_TRESULT_FAIL,
                            '종합상황판 Mapping 데이터 추가 실패 또는 DB 오류', None, '종합상황판  Mapping 데이터 추가')
                return

        if e2e != None:
            e2e.job('종합상황판 Mapping 데이터 추가 완료', e2e_logger.CONST_TRESULT_SUCC, None, None,
                    '종합상황판  표시를 위한 Mapping 데이터 추가')

        ## zabbix 서버로 요청

        req_handler.saveRequestState(dbm, src, tid, 'ZBSERVER_SETTING', 20)
        svrDesc=svrInfo.svrDesc
        ret=zbm_api.addHost(logger, svrOBID, svrInfo.svrName, svrIP, [], svrDesc)
        if ret == False:
            rbDB.rollback()
            asRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Add ZB Host Error', None, {'host': svrOBID})
            logger.error(asRes.lF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, 'Add ZB Server Error')
            if e2e != None:
                e2e.job('서버 추가 실패(zabbix)', e2e_logger.CONST_TRESULT_FAIL, 'zabbix 시스템에 서버 추가 실패', None,
                        'zabbix 시스템에 모니터링할 서버 정보 추가')
            return

        if e2e != None:
            e2e.job('서버 추가 완료(zabbix)', e2e_logger.CONST_TRESULT_SUCC, None, None, 'zabbix 시스템에 모니터링할 서버 정보 추가')

        rbDB.commit()

        if e2e != None:
            e2e.job('감시 템플릿 설정', e2e_logger.CONST_TRESULT_NONE)
        if tPath == None:
            tTargetPath=None
        else:
            tTargetPath=tPath + '/AddTemplate'

        if DEBUG_LOG_YN == 'y': logger.info(
            '[addServer_1] ==========> src : %s, tid : %s, monInfo : %s' % (str(src), str(tid), str(monInfo)))

        asRes=addTargetToSvr(src, tid, tTargetPath, e2eUrl, monInfo, dbm, True, 20)

        if asRes.isFail():
            logger.error(asRes.setErr('Add Server Target Error').ltF(FNAME))
            if e2e != None:
                e2e.job('감시 템플릿 설정', e2e_logger.CONST_TRESULT_FAIL)
                e2e.job('요청 서버 정보 제거', e2e_logger.CONST_TRESULT_NONE)
            tDelPath=''
            if tPath == None:
                tDelPath=None
            else:
                tTargetPath=tDelPath + '/DelServer'
            delServer(tid, tDelPath, e2eUrl, svrInfo, dbm)
            if e2e != None:
                e2e.job('요청 서버 정보 제거', e2e_logger.CONST_TRESULT_FAIL)
            return

        if e2e != None:
            e2e.job('감시 템플릿 설정', e2e_logger.CONST_TRESULT_SUCC)

        logger.info(rrl.rSc(tid, None, None).lS(FNAME))

        return
    except Exception, e:
        rbDB.rollback()
        asRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, monInfo)
        logger.error(asRes.lF(FNAME))
        logger.fatal(e)
        req_handler.saveRequestFail(dbm, src, tid, e)
        if e2e != None:
            e2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, str(e))
    finally:
        rbDB.close()

    return


## addList: svr_id, t_key, i_key, d_key
## modList: svr_id, t_key, i_key, conditions, repeat, grade, d_key
## delList: svr_id, t_key, i_key, name, grade, conditions, repeat, d_key
## tmpList: svr_id, t_key, i_key, status, grade, d_key
def _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList):
    """
    - FUNC: Threshold 데이터 롤백
    - INPUT
        tid(M): 요청 TID
        rbDB(M): DB 연결 객체
        addList(M): 추가한 데이터
        modList(M): 변경한 데이터의 원본
        delList(M): 지운 데이터
        tmpList(M): 템플릿의 트리거 정보
    - OUTPUT: Threshold 데이터 롤백 결과
        rrl_handler._ReqResult
    """
    try:
        rbDB.rollback()

        if addList != None and len(addList) > 0:
            for addInfo in addList:
                zbm_api.delHostTrigger(logger, addInfo['svr_id'], addInfo['t_key'], addInfo['i_key'], addInfo['d_key'])
        if modList != None and len(modList) > 0:
            for modInfo in modList:
                zbm_api.modHostTrigger(logger, modInfo['svr_id'], modInfo['t_key'], modInfo['i_key'],
                                       modInfo['conditions'], modInfo['repeat'], modInfo['grade'], modInfo['d_key'],
                                       op_type=op_type, start_value=start_value)
        if delList != None and len(delList) > 0:
            for delInfo in delList:
                zbm_api.addHostTrigger(logger, delInfo['svr_id'], delInfo['i_key'], delInfo['t_key'], delInfo['name'],
                                       delInfo['grade'], delInfo['conditions'], delInfo['repeat'], delInfo['d_key'],
                                       delInfo['d_param'], op_type=op_type, start_value=start_value)
        if tmpList != None and len(tmpList) > 0:
            for tmpInfo in tmpList:
                zbm_api.setTemplateTriggerStatus(logger, tmpInfo['svr_id'], tmpInfo['t_key'], tmpInfo['i_key'],
                                                 tmpInfo['status'], tmpInfo['grade'], tmpInfo['d_key'],
                                                 tmpInfo['d_list'])
        return True
    except Exception, e:
        rbRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rbRes.lF('RollBack Threshold Data'))
        logger.fatal(e)
        return False


## item_seq, threshold
## threshold: grade, conditions, repeat
def setOBThreshold(tid, _params, dbm, convert=True, isMass=False):
    """
    - FUNC: Host Threshold 설정
    - INPUT
        tid(M): 요청 TID
        _params(M): Threshold 정보
        dbm(M): DB 연결 객체
        convert(O): 입력 파라미터의 Orch-M 형식 변환 여부
        isMass(O): 일괄 데이터 변경인지 여부에 따라 로그 형식 다름
    - OUTPUT: Threshold 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Set Host Threshold'

    if convert:
        soRes=web_api.convertThreshold(_params, dbm)
        if soRes.isFail():
            logger.error(soRes.lF(FNAME))
            return soRes
        params=soRes.ret()
    else:
        params=_params

    ## rollback 위한 기존데이터 저장
    modList=[]
    addList=[]
    delList=[]
    tmpList=[]

    rbDB=dbm.getRollBackDB()

    try:
        def _res(_bool, _ret, _resCode, _name, _param):

            if _bool:
                rbDB.rollback()
                if _ret == None:
                    rc=rrl.RS_FAIL_DB
                else:
                    rc=_resCode
                soRes=rrl.rFa(tid, rc, _name, _ret, _param)
                logger.error(soRes.lF(FNAME))
                return soRes
            else:
                return None

        def _resR(_bool, _ret, _resCode, _name, _param):

            if _bool:
                if _ret == None:
                    rc=rrl.RS_FAIL_DB
                else:
                    rc=_resCode
                soRes=rrl.rFa(tid, rc, _name, _ret, _param)
                logger.error(soRes.lF(FNAME))
                _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
                return soRes
            else:
                return None

        itemSeq=str(params['item_seq'])
        ## 아이템 정보
        itemInfo=rbDB.select(db_sql.GET_ITEM_INST_FOR_THRES(itemSeq))
        soRes=_res((itemInfo == None or len(itemInfo) < 1), itemInfo, rrl.RS_NO_DATA, 'Get Item Inst Info Error',
                   {'item_seq': itemSeq})
        if soRes != None: return soRes

        svrOBID=itemInfo[0]['onebox_id']
        iKey=itemInfo[0]['key']
        dKey=itemInfo[0]['d_key']
        dParam=itemInfo[0]['d_param']
        svrSeq=itemInfo[0]['serverseq']

        dList=rbDB.select(db_sql.GET_ITEM_INST_OBJLIST(itemSeq), 'monitorobject')
        soRes=_res((dList == None), dList, rrl.RS_FAIL_OP, 'Get Item Object Error', {'item_seq': itemSeq})
        if soRes != None: return soRes

        ## 기존 서버 별 설정
        prevThresInst=rbDB.select(db_sql.GET_THRES_INST(itemSeq))
        soRes=_res((prevThresInst == None), prevThresInst, rrl.RS_FAIL_OP, 'Get Threshold Inst Error',
                   {'item_seq': itemSeq})
        if soRes != None: return soRes

        ## 변경할 항목에 기존 해결하지 못한 장애가 있는지 확인 -> 장애 있어도 변경
        #         ret = rbDB.select( db_sql.GET_CURR_ALARM_FOR_ADD_THRESHOLD( itemSeq ) )
        #         soRes = _res((ret != None and len(ret) > 0), ret, rrl.RS_INUSE_DATA, 'In-Used Data(Curalarm) Check Error', {'item_seq':itemSeq})
        #         if soRes != None: return soRes

        if params.has_key('threshold'):

            thrList=params['threshold']

            for thr in thrList:
                grade=thr['grade']
                thrName=thr['name']
                conditions=thr['conditions']
                cType=thr['operator']
                start_value=thr['start_value']
                repeat=1 if thr['repeat'] == '' else thr['repeat']
                desc=thr['description']

                ## 변경할 등급에 기존 해결하지 못한 장애가 있는지 확인 -> 장애 있어도 변경
                #                 ret = rbDB.select( db_sql.GET_CURR_ALARM_FOR_ADD_THRESHOLD( itemSeq, grade ) )
                #                 soRes = _res((ret != None and len(ret) > 0), ret, rrl.RS_INUSE_DATA, 'In-Used Data(Curalarm) Check Error', {'item_seq':itemSeq, 'fault_grade':grade})
                #                 if soRes != None: return soRes

                # 이전에 저장된 값에서 start_value 값 추출 -> zbm_api.modHostTrigger 를 사용하여 기존값을 수정하기 위해서 이전 start_value 를 추출
                tmp_min_max=[]
                prev_start_value=None
                _condition_type=None
                for prevThres in prevThresInst:
                    prev_condition=json.loads(prevThres['condition'])

                    if type(prev_condition) is list:

                        for pc in prev_condition:
                            if type(pc) is dict:
                                tmp_min_max.append(pc['value'])
                            else:
                                continue
                                # 2017.04.04 str_api.py 사용
                                # tmp_min_max = sa.dictValuesinList(prev_condition, tmp_min_max, 'value')

                    else:
                        tmp_min_max.append(prev_condition['value'])

                    _condition_type=prevThres['condition_type'].upper()
                if prevThresInst != None:
                    if _condition_type == "GE":  # 이상
                        prev_start_value=min(tmp_min_max)
                    elif _condition_type == "LE":  # 이하
                        prev_start_value=max(tmp_min_max)

                ## 수정
                isModified=False
                for prevThres in prevThresInst:
                    if prevThres['fault_grade'] == str(grade).lower():
                        if json.dumps(conditions, encoding='utf-8') != prevThres['condition'] or repeat != prevThres[
                            'repeat']:
                            ret=zbm_api.modHostTrigger(logger, svrOBID, prevThres['t_key'], iKey, conditions, repeat,
                                                       grade, dKey, op_type=cType, start_value=start_value)
                            if ret == False:
                                soRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Modify Host Trigger Error', None,
                                              {'trigger': thr})
                                logger.error(soRes.lF(FNAME))
                                _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
                                return soRes
                            modList.append({'svr_id': svrOBID, 't_key': prevThres['t_key'], 'i_key': iKey,
                                            'conditions': json.loads(prevThres['condition']),
                                            'repeat': prevThres['repeat'], 'grade': grade, 'd_key': dKey,
                                            'op_type': prevThres['condition_type'], 'start_value': prev_start_value})

                            ret=rbDB.execute(
                                db_sql.UPDATE_THRES_INST(prevThres['t_key'], json.dumps(conditions, encoding='utf-8'),
                                                         cType, repeat))
                            soRes=_resR((ret == None or ret < 1), ret, rrl.RS_INVALID_PARAM,
                                        'Modify Host Trigger Data Error', {'t_key': prevThres['t_key'], 'tigger': thr})
                            if soRes != None: return soRes

                        else:
                            logger.debug(rrl.rSc(tid, None, prevThres, _msg='Same Host Threshold Info').lL(FNAME))

                        isModified=True
                        prevThresInst.remove(prevThres)
                        logger.info(rrl.rSc(tid, None, {'threshold': thr}, _msg='Modify Host Threshold Inst').lS(FNAME))
                        break

                if isModified: continue

                ## 추가
                ## DB 저장
                cdt=json.dumps(conditions, encoding='utf-8')
                comments=item_handler.makeThresholdKey(grade)
                ret=rbDB.execute(db_sql.INSERT_THRES_INST(itemSeq, thrName, grade, cdt, cType, repeat, comments, desc))
                soRes=_resR((ret == None or ret < 1), ret, rrl.RS_FAIL_DB, 'Insert Host Trigger Data Error',
                            {'item_seq': itemSeq, 'tigger': thr})
                if soRes != None: return soRes
                if not isMass:
                    logger.info(rrl.rSc(tid, None, {'threshold': thr}, _msg='Insert Host Threshold Data').lS(FNAME))
                ## zb host trigger 전송
                ret=zbm_api.addHostTrigger(logger, svrOBID, iKey, comments, thrName, grade, conditions, repeat, dKey,
                                           dParam, op_type=cType, start_value=start_value)
                if ret == False:
                    soRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Add ZB Host Trigger Error', None,
                                  {'host': svrOBID, 'item_key': iKey, 'disc_key': dKey, 'disc_param': dParam,
                                   'trigger': thr})
                    logger.error(soRes.lF(FNAME))
                    _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
                    return soRes
                addList.append({'svr_id': svrOBID, 't_key': comments, 'i_key': iKey, 'd_key': dKey})

                ## 템플릿 설정되어 있으면 OFF
                _templateTriggerKey=rbDB.select(db_sql.GET_THRES_CAT_KEY(itemSeq, grade), 't_key')
                templateTriggerKey=None
                if _templateTriggerKey != None and len(_templateTriggerKey) > 0:
                    templateTriggerKey=_templateTriggerKey[0]
                    ret=zbm_api.setTemplateTriggerStatus(logger, svrOBID, templateTriggerKey, iKey, False, grade, dKey,
                                                         dList)
                    if ret == False:
                        soRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Set Disable ZB Template Trigger Error', None,
                                      {'host': svrOBID, 'item_key': iKey, 'trg_key': templateTriggerKey,
                                       'disc_key': dKey, 'disc_list': dList, 'grade': grade})
                        logger.error(soRes.lF(FNAME))
                        _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
                        return soRes
                    tmpList.append(
                        {'svr_id': svrOBID, 't_key': templateTriggerKey, 'i_key': iKey, 'status': True, 'grade': grade,
                         'd_key': dKey, 'd_list': dList})
        ## 제거
        for delThr in prevThresInst:
            ## zb host trigger 제거
            ret=zbm_api.delHostTrigger(logger, svrOBID, delThr['t_key'], iKey, dKey)
            if ret == False:
                soRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Del ZB Host Trigger Error', None,
                              {'host': svrOBID, 'trg_key': delThr['t_key'], 'item_key': iKey, 'disc_key': dKey})
                logger.error(soRes.lF(FNAME))
                _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
                return soRes
            delList.append(
                {'svr_id': svrOBID, 't_key': delThr['t_key'], 'i_key': iKey, 'name': delThr['threshold_name'],
                 'grade': delThr['fault_grade'], 'conditions': json.loads(delThr['condition']),
                 'repeat': delThr['repeat'], 'd_key': dKey, 'd_param': dParam})
            ret=rbDB.execute(db_sql.REMOVE_THRES_INST(svrSeq, delThr['t_key']))
            soRes=_resR((ret == None), ret, rrl.RS_FAIL_OP, 'Remove Host Trigger Data Error',
                        {'svr_seq': svrSeq, 'thr_key': delThr['t_key']})

            ## zb template trigger ON
            #             grade = delThr['fault_grade']
            #             _templateTriggerKey = rbDB.select( db_sql.GET_THRES_CAT_KEY( itemSeq, grade ), 't_key' )
            #             templateTriggerKey = None
            #             if _templateTriggerKey != None and len(_templateTriggerKey) > 0 :
            #                 templateTriggerKey = _templateTriggerKey[0]
            #                 ret = zbm_api.setTemplateTriggerStatus( logger, svrOBID, templateTriggerKey, iKey, True, grade, dKey, dList )
            #                 if ret == False:
            #                     soRes = rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Set Enable TemplateTrigger Error', None, delThr)
            #                     logger.error( soRes.lF(FNAME) )
            #                     _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
            #                     return soRes
            #                 tmpList.append({'svr_id':svrOBID, 't_key':templateTriggerKey, 'i_key':iKey,
            #                                 'status':False, 'grade':grade, 'd_key':dKey, 'd_list':dList})

            logger.info(rrl.rSc(tid, None, {'threshold': delThr}, _msg='Remove Threshold Inst Data').lS(FNAME))

        rbDB.commit()
        soRes=rrl.rSc(tid, {'tid': tid}, None)
        logger.info(soRes.lS(FNAME))
        return soRes
    except Exception, e:
        soRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(soRes.lF(FNAME))
        logger.fatal(e)
        _rollBackSetOBThreshold(tid, rbDB, addList, modList, delList, tmpList)
        return soRes
    finally:
        rbDB.close()


def getTargetSeq (dbm, targetInfo) :

    ## Target Sequence 가 없는 대상은 대상 정보로 target_seq를 얻어옴
    _monitorAt = (lambda x: x if x != None else monitorAt)(targetInfo.targetFor)
    targetVer = targetInfo.targetVer
    vdudSeq = targetInfo.targetVdudSeq

    strsql = db_sql.GET_TARGET_FOR_CREATE( targetInfo.targetCode, targetInfo.targetType,
                    targetInfo.targetVendor, targetInfo.targetModel, targetVer, vdudSeq, _monitorAt )

    # logger.info ('GET_TARGET_FOR_CREATE : %s ' % strsql )

    ret = dbm.select( strsql )

    if ret == None or len(ret) < 1:
        if ret == None: rs = rrl.RS_FAIL_DB
        else: rs = rrl.RS_NO_DATA
        rres = rrl.rFa(None, rs, 'Getting TargetSeq Error', ret, targetInfo)
        return None
    
    return ret[0]['montargetcatseq']

def delTargetOnSvr(tid, tPath, e2eUrl, _monInfo, dbm):
    """
    - FUNC: 모니터링 템플릿 해제
    - INPUT
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        _monInfo(M): 모니터링 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 모니터링 템플릿 해제 결과
        rrl_handler._ReqResult
    """
    FNAME='Release Host Template'

    dte2e=None
    if tPath != None:
        dte2e=e2e_logger.e2elogger('템플릿 해제', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    monInfo=mon_msg.MonInfo

    if _monInfo != None: monInfo=_monInfo

    svrInfo=monInfo.svrInfo
    svr_seq=str(svrInfo.svrSeq)

    dtRes=orchf_api.convertTargetSeq(dbm, svr_seq, monInfo, 'Provisioning', True)
    if dtRes.isFail():
        logger.error(dtRes.setErr('Convert Parameters Error').ltF(FNAME))
        if dte2e != None:
            dte2e.job('파라미터 변환 실패', e2e_logger.CONST_TRESULT_FAIL, dtRes.errStr(), None, '모니터링 시스템 파라미터로 변환')
        return dtRes
    monInfo=dtRes.ret()

    if dte2e != None:
        dte2e.job('파라미터 변환 완료', e2e_logger.CONST_TRESULT_SUCC, None, None, '모니터링 시스템 파라미터로 변환')

    try:
        svrOBID=svrInfo.svrObid
        ip=svrInfo.svrIP

        targetList=[]
        for targetInfo in monInfo.targetList:
             
            if targetInfo.targetSeq == None:
                # TargetSeq 가 없으면 쿼리로 가져온다.
                targetInfo.targetSeq = getTargetSeq(dbm, targetInfo) 
                if targetInfo.targetSeq == None:
                    dtRes=rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Target Seq', None, targetInfo)
                    logger.error(dtRes.lF(FNAME))
                    if dte2e != None:
                        dte2e.job('감시 템플릿 정보 오류', e2e_logger.CONST_TRESULT_FAIL, dtRes.errStr())
                    return dtRes

            targetList.append(str(targetInfo.targetSeq))

            # 템플릿 삭제시 Orch-F 와 연계 정보인 vdudseq 도 함께 삭제한다.
            # vdud 와 타겟 매핑 정보 삭제

            # TODO : 반드시 삭제해야 하나? - 18. 6. 5 - lsh
            vdudseq=targetInfo.targetVdudSeq
            mappingSql=db_sql.DELETE_VDUD_TARGET_MAPPING(svr_seq, str(targetInfo.targetSeq))
            dbm.execute(mappingSql)

        dtRes=_delTarget(tid, dte2e, svr_seq, svrOBID, ip, targetList, dbm)
        if dtRes.isSucc():
            dtRes=rrl.rSc(tid, {'tid': tid}, None)
            logger.info(dtRes.lS(FNAME))
            if dte2e != None:
                dte2e.job('감시 템플릿 해제 완료', e2e_logger.CONST_TRESULT_SUCC)
            sleep(3)
            return dtRes
        else:
            logger.error(dtRes.setErr('Delete Server Template Data Error').ltF(FNAME))
            if dte2e != None:
                dte2e.job('감시 템플릿 해제 실패', e2e_logger.CONST_TRESULT_FAIL, dtRes.errStr())
            return dtRes
    except Exception, e:
        dtRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, _monInfo)
        logger.error(dtRes.lF(FNAME))
        logger.fatal(e)
        if dte2e != None:
            dte2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, str(e))
        return dtRes


def _setWebMappingInfo(tid, dbm, svrSeq, mapInfo, targetAt, onebox_type):
    """
    - FUNC: WEB 화면 구성과 감시항목 매핑
    - INPUT
        tid(M): 요청 TID
        dbm(M): DB 연결 객체
        svrSeq(M): 서버 시퀀스
        mapInfo(M): 매핑정보
    - OUTPUT: WEB 화면 구성과 감시항목 매핑 결과
        rrl_handler._ReqResult
    """
    FNAME='Set WebMapping Info'

    try:
        if type(mapInfo) != dict:
            swRes=rrl.rFa(tid, rrl.RS_INVALID_PARAM, 'Web Mapping Info is not Dict', None,
                          {'svr_seq': svrSeq, 'map_info': mapInfo})
            logger.error(swRes.lF(FNAME))
            return swRes

        # 네트워크 매핑 정보는 서버 추가인 "OneTouch" 인 경우에만 수행한다.
        mapKeyList=['wan', 'server', 'office1', 'office2', 'office', 'extra_wan', 'other']
        if targetAt == "OneTouch":
            for mapKey in mapKeyList:
                # if mapInfo.has_key(mapKey):
                param=None
                if mapInfo.has_key(mapKey) and mapInfo[mapKey] != None and str(mapInfo[mapKey]) != '':
                    param=str(mapInfo[mapKey])

                key='net.' + mapKey + '.%'
                if DEBUG_LOG_YN == 'y': logger.info(
                    '[_setWebMappingInfo_1,OneTouch] ==========> svrSeq : %s, Key : %s, param : %s' % (svrSeq, key, str(param)))

                strsql = db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param)

                logger.info ("UPDATE_VIEW_INST_OBJ : %s " % strsql )

                ret = dbm.execute(strsql)

                if ret == None or ret < 1:
                    swRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Web Mapping Info Error', None,
                                  {'svr_seq': svrSeq, 'view_key': key, 'object': param})
                    logger.error(swRes.lF(FNAME))
                    return swRes


            # 2019. 3.11 - lsh, PNF 형은 UTM 쪽도 ether 정보 Update 필요.
            # logger.info( ' monInfo.svrInfo.onebox_type : ' +  str(onebox_type ))
            if onebox_type == 'KtPnf' :
                mapKeyList_pnf=['wan', 'server', 'office', 'other']                
                for mapKey in mapKeyList_pnf:
                    param=None
                    if mapInfo.has_key(mapKey) and mapInfo[mapKey] is not None and str(mapInfo[mapKey]) is not '' and str(mapInfo[mapKey]) is not 'None':
                        param=mapInfo[mapKey]
                    else :
                        continue

                    key='utm.' + mapKey + '.%'

                    # if param is None:
                    #     if DEBUG_LOG_YN == 'y': logger.info(
                    #         '[_setWebMappingInfoForMultiport_1,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                    #             svrSeq, key, str(param)))
                    #     ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param))

                    if type(param) is list:
                        if DEBUG_LOG_YN == 'y': logger.info(
                            '[_setWebMappingInfo_2,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                                svrSeq, key, str(param)))
                        ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param[0]))  # 첫번째는 update

                        if len(param) > 1:  # 두번째는 insert
                            for p in param[1:]:
                                if DEBUG_LOG_YN == 'y': logger.info(
                                    '[_setWebMappingInfo_3,OneTouch] ==========> svrSeq : %s, Key: %s, param: %s' % (
                                        svrSeq, key, str(p)))
                                qry=db_sql.INSERT_VIEW_INST_OBJ(svrSeq, key, p)
                                ret=dbm.execute(qry)
                    else:
                        # param str 처리.
                        if DEBUG_LOG_YN == 'y': logger.info(
                            '[_setWebMappingInfo_4,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                                svrSeq, key, str(param)))

                        ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param))

                    if ret == None or ret < 1:
                        swRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Web Mapping Info Error', None,
                                    {'svr_seq': svrSeq, 'view_key': key, 'object': param})
                        logger.error(swRes.lF(FNAME))
                        sleep(30)
                        return swRes

        for mapKey in mapKeyList:
            if mapInfo.has_key(mapKey):
                mapInfo.pop(mapKey)

        mappingKey=mapInfo.keys()
        for mKey in mappingKey:
            param=mapInfo[mKey]
            if type(param) is list:
                if DEBUG_LOG_YN == 'y': logger.info('[_setWebMappingInfo_11] ==========> param : %s' % str(param))
                param=str(param[0])

            if param == "None" or param == "":
                param=None

            if DEBUG_LOG_YN == 'y': logger.info(
                '[_setWebMappingInfo_2] ==========> svrSeq: %s, mKey: %s, param: %s' % (svrSeq, mKey, str(param)))
            ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, mKey, param))

            if ret == None or ret < 1:
                swRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Web Mapping Info Error', None,
                              {'svr_seq': svrSeq, 'view_key': mKey, 'object': param})
                logger.error(swRes.lF(FNAME))
                return swRes

        return rrl.rSc(tid, None, None)
    except Exception, e:
        swRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(swRes.lF(FNAME))
        logger.fatal(e)
        return swRes


def _setWebMappingInfoForMultiport(tid, dbm, svrSeq, mapInfo, targetAt, onebox_type):
    """
    - FUNC: WEB 화면 구성과 감시항목 매핑
    - INPUT
        tid(M): 요청 TID
        dbm(M): DB 연결 객체
        svrSeq(M): 서버 시퀀스
        mapInfo(M): 매핑정보
    - OUTPUT: WEB 화면 구성과 감시항목 매핑 결과
        rrl_handler._ReqResult
    """
    FNAME='Set WebMapping Info'

    try:
        if type(mapInfo) != dict:
            swRes=rrl.rFa(tid, rrl.RS_INVALID_PARAM, 'Web Mapping Info is not Dict', None,
                          {'svr_seq': svrSeq, 'map_info': mapInfo})
            logger.error(swRes.lF(FNAME))
            return swRes

        # 네트워크 매핑 정보는 서버 추가인 "OneTouch" 인 경우에만 수행한다.
        mapKeyList=['wan', 'server', 'office1', 'office2', 'office', 'extra_wan', 'other']
        if targetAt == "OneTouch":
            for mapKey in mapKeyList:
                param=None
                if mapInfo.has_key(mapKey) and mapInfo[mapKey] is not None and str(mapInfo[mapKey]) is not '' and str(mapInfo[mapKey]) is not 'None':
                    param=mapInfo[mapKey]

                key='net.' + mapKey + '.%'

                if param is None:
                    if DEBUG_LOG_YN == 'y': logger.info(
                        '[_setWebMappingInfoForMultiport_1,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                            svrSeq, key, str(param)))
                    ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param))

                if type(param) is list:
                    if DEBUG_LOG_YN == 'y': logger.info(
                        '[_setWebMappingInfoForMultiport_2,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                            svrSeq, key, str(param)))
                    ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param[0]))  # 첫번째는 update

                    if len(param) > 1:  # 두번째는 insert
                        for p in param[1:]:
                            if DEBUG_LOG_YN == 'y': logger.info(
                                '[_setWebMappingInfoForMultiport_22,OneTouch] ==========> svrSeq : %s, Key: %s, param: %s' % (
                                    svrSeq, key, str(p)))
                            qry=db_sql.INSERT_VIEW_INST_OBJ(svrSeq, key, p)
                            ret=dbm.execute(qry)
                else:
                    # param str 처리.
                    if DEBUG_LOG_YN == 'y': logger.info(
                        '[_setWebMappingInfoForMultiport_23,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                            svrSeq, key, str(param)))

                    ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param))

                if ret == None or ret < 1:
                    swRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Web Mapping Info Error', None,
                                  {'svr_seq': svrSeq, 'view_key': key, 'object': param})
                    logger.error(swRes.lF(FNAME))
                    sleep(30)
                    return swRes

            # 2019. 3.11 - lsh, PNF 형은 UTM 쪽도 ether 정보 Update 필요.
            # logger.info( ' monInfo.svrInfo.onebox_type : ' +  onebox_type )
            if onebox_type == 'KtPnf' :
                mapKeyList_pnf=['wan', 'server', 'office', 'other']                
                for mapKey in mapKeyList_pnf:
                    param=None
                    if mapInfo.has_key(mapKey) and mapInfo[mapKey] is not None and str(mapInfo[mapKey]) is not '' and str(mapInfo[mapKey]) is not 'None':
                        param=mapInfo[mapKey]
                    else :
                        continue

                    key='utm.' + mapKey + '.%'

                    # if param is None:
                    #     if DEBUG_LOG_YN == 'y': logger.info(
                    #         '[_setWebMappingInfoForMultiport_1,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                    #             svrSeq, key, str(param)))
                    #     ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param))

                    if type(param) is list:
                        if DEBUG_LOG_YN == 'y': logger.info(
                            '[_setWebMappingInfoForMultiport_2,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                                svrSeq, key, str(param)))
                        ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param[0]))  # 첫번째는 update

                        if len(param) > 1:  # 두번째는 insert
                            for p in param[1:]:
                                if DEBUG_LOG_YN == 'y': logger.info(
                                    '[_setWebMappingInfoForMultiport_22,OneTouch] ==========> svrSeq : %s, Key: %s, param: %s' % (
                                        svrSeq, key, str(p)))
                                qry=db_sql.INSERT_VIEW_INST_OBJ(svrSeq, key, p)
                                ret=dbm.execute(qry)
                    else:
                        # param str 처리.
                        if DEBUG_LOG_YN == 'y': logger.info(
                            '[_setWebMappingInfoForMultiport_23,OneTouch] ==========> svrSeq: %s, Key: %s, param: %s' % (
                                svrSeq, key, str(param)))

                        ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, key, param))

                    if ret == None or ret < 1:
                        swRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Web Mapping Info Error', None,
                                    {'svr_seq': svrSeq, 'view_key': key, 'object': param})
                        logger.error(swRes.lF(FNAME))
                        sleep(30)
                        return swRes

        for mapKey in mapKeyList:
            if mapInfo.has_key(mapKey):
                mapInfo.pop(mapKey)

        mappingKey=mapInfo.keys()
        for mKey in mappingKey:
            param=mapInfo[mKey]
            if type(param) is list:
                # 2017.03.21 'None' 필터 처리로 추가.
                if param[0] == "None" or param[0] == "":
                    param[0]=None

                if DEBUG_LOG_YN == 'y':
                    logger.info('[_setWebMappingInfoForMultiport_3] ==========> svrSeq : %s, Key : %s, param : %s' % (
                        svrSeq, mKey, str(param)))

                qry=db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, mKey, param[0])
                ret=dbm.execute(qry)  # 첫번째는 update

                if len(param) > 1:  # 두번째는 insert
                    for p in param[1:]:
                        qry=db_sql.INSERT_VIEW_INST_OBJ(svrSeq, mKey, p)
                        ret=dbm.execute(qry)

            else:  # 2017.03.22 김승주전임 else구문 추가 요청
                if param == "None" or param == "":
                    param=None

                if DEBUG_LOG_YN == 'y':
                    logger.info('[_setWebMappingInfoForMultiport_4] ==========> svrSeq : %s, Key : %s, param : %s' % (
                        svrSeq, mKey, str(param)))

                # param str 처리.
                ret=dbm.execute(db_sql.UPDATE_VIEW_INST_OBJ(svrSeq, mKey, param))

            if ret == None or ret < 1:
                swRes=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Web Mapping Info Error', None,
                              {'svr_seq': svrSeq, 'view_key': mKey, 'object': param})
                logger.error(swRes.lF(FNAME))
                return swRes

        return rrl.rSc(tid, None, None)
    except Exception, e:
        swRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(swRes.lF(FNAME))
        logger.fatal(e)
        return swRes


# def checkMapInfoNum(mapName, mapInfo):
#     """
#     - FUNC: 매핑 감시항목 이중화 체크
#     - INPUT
#         mapName(M): 확인할 맵정보
#         mapInfo(M): 매핑정보
#     - OUTPUT: 이중화 건수 결과
#     """
#     mapinfoNum = 0
#
#     if (mapName in mapInfo.keys() and type(mapInfo[mapName]) is list):
#         mapinfoNum = len(mapInfo[mapName])
#         if DEBUG_LOG_YN == 'y': logger.info('[checkMapInfoNum_1] ==========> %s : %s' % (mapName, str(mapInfo[mapName])))
#     else:
#         mapinfoNum = 0
#
#     return mapinfoNum


def addTargetToSvr(src, tid, tPath, e2eUrl, _monInfo, dbm, isAddSvr=False, progStart=0):
    """
    - FUNC: 모니터링 템플릿 등록
    - INPUT
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        _monInfo(M): Threshold 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 모니터링 템플릿 해제 결과
        rrl_handler._ReqResult
    """
    FNAME='Add Server Target'

    te2e=None
    if tPath != None:
        te2e=e2e_logger.e2elogger('템플릿 설정', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    def progress(progStart, perc):
        return int(round((100 - progStart) * perc / 100.0)) + progStart

    targetInfo = _monInfo.targetList[0]

    if targetInfo.targetType == 'svr' :
        isAddSvr = True

    if isAddSvr:
        req_handler.saveRequestStatus(dbm, src, tid, 'ADD TARGET', 'CONVERT_PARAM', progress(progStart, 1))
        logger.info("ADD TARGET        CONVERT_PARAM")
    else:
        req_handler.saveRequestStatus(dbm, src, tid, 'READY', 'CONVERT_PARAM', progress(progStart, 1))
        logger.info("READY    CONVERT_PARAM")

    targetAt=(lambda x: 'OneTouch' if x else 'Provisioning')(isAddSvr)
    
    atRes=orchf_api.convertProvisionParam(dbm, _monInfo, targetAt, defaultPluginPath)

    monInfo=mon_msg.MonInfo

    if atRes.isFail():
        logger.error(atRes.setErr('Convert Parameters Error').ltF(FNAME))
        req_handler.saveRequestFail(dbm, src, tid, atRes.errStr())
        if te2e != None:
            te2e.job('파라미터 변환 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None, '모니터링 시스템 파라미터로 변환')
        return atRes
    else:
        monInfo=atRes.ret()

    req_handler.saveRequestState(dbm, src, tid, 'PARSE_PARAM_3', progress(progStart, 5))
    svrInfo=monInfo.svrInfo         # 서버 정보
    svr_seq=str(svrInfo.svrSeq)     # 서버 시퀀스
    svrOBID=svrInfo.svrObid         # '원박스 아이디'로 추정
    svrIP=svrInfo.svrIP             # 서버 IP 주소

    try:
        if targetAt == "OneTouch":
            service_number=monInfo.service_number  # 서비스 넘버
        else:
            service_number=monInfo.targetList[0].targetCfg['service_number']  # 서비스 넘버
    except:
        service_number=''

    if te2e != None:
        te2e.job('파라미터 변환 완료', e2e_logger.CONST_TRESULT_SUCC, None, None, '모니터링 시스템 파라미터로 변환')

    rbDB=dbm.getRollBackDB()
    
    try:
        def _res(_bool, _ret, _resCode, _name, _reqRes, _param):

            if _bool:
                rbDB.rollback()
                if _ret == None:
                    rc=rrl.RS_FAIL_DB
                else:
                    rc=_resCode
                _atRes=rrl.rFa(tid, rc, _name, _ret, _param)
                logger.error(_atRes.lF(FNAME))
                req_handler.saveRequestFail(dbm, src, tid, _reqRes)
                return _atRes
            else:
                return None

        ## 유효성 체크
        req_handler.saveRequestState(dbm, src, tid, 'CHECK_PARAM', progress(progStart, 10))
        svrExistSql=db_sql.GET_SERVER_CNT_BY_SEQ(svr_seq)
        ret=rbDB.select(svrExistSql)
        atRes=_res((ret == None or len(ret) < 1), ret, rrl.RS_NO_DATA, 'No Server Info', 'No Server',
                   {'svr_seq': svr_seq})
                   
        if atRes != None:
            if te2e != None:
                te2e.job('서버 데이터 유효성 점검 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None, '서버 데이터 조회 ')
            return atRes

        atRes=_chkKeyDuplicated(rbDB, svr_seq, monInfo.targetList)  # 감시항목의 Key 값 중복 체크
        if atRes.isFail():
            rbDB.rollback()
            logger.error(atRes.setErr('Check Key Duplicated Error').ltF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, atRes.errStr())
            if te2e != None:
                te2e.job('감시 항목 Key 데이터 유효성 점검 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                         '감시 항목 Key 중복 점검')
            return atRes

        targetList=[]
        targetInfo=mon_msg.TargetInfo
        for targetInfo in monInfo.targetList:
            tSeq=targetInfo.targetSeq
            targetList.append(str(tSeq))

            # vdud 와 타겟 매핑
            # OneTouch(OnBoarding) 시에는 VNF 가 등록되는 것이 아니기 때문에 vdudseq 가 전달되지 않는다.
            if targetAt != "OneTouch" and targetInfo.targetVdudSeq != None:
                vdudseq=targetInfo.targetVdudSeq

                # 기존에 등록된 데이터가 존재하지 않을 경우에만 vdudseq 등록. -> 프로비저닝 실패시 복원, 백업/복구, 초기화(삭제 Order) 등을 내릴때 중복해서 호출된다.
                mappingSql=db_sql.GET_VDUD_TARGET_MAPPING(svr_seq, tSeq, vdudseq)
                mappingRet=rbDB.select(mappingSql)
                if mappingRet == None or len(mappingRet) == 0:
                    mappingSql=db_sql.INSERT_VDUD_TARGET_MAPPING(svr_seq, tSeq, vdudseq)
                    rbDB.execute(mappingSql)

            svrTargetExistSql=db_sql.GET_TARGET_CNT_BY_SERVER(svr_seq, str(tSeq))
            ret=rbDB.select(svrTargetExistSql)
            atRes=_res((ret == None or (len(ret) > 0 and int(ret[0]['c']) > 0)), ret, rrl.RS_ALREADY_EXIST,
                       'Already Used Target', 'Already Used Target, target=%s' % str(ret),
                       {'svr_seq': svr_seq, 'target_seq': tSeq})
            if atRes != None:
                if te2e != None:
                    te2e.job('감시 템플릿 유효성 점검 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None, '감시 템플릿 중복 조회 ')
                return atRes

        if te2e != None:
            te2e.job('데이터 유효성 점검 완료', e2e_logger.CONST_TRESULT_SUCC)
        # te2e.job('종합상황판 Mapping 데이터 설정 완료', e2e_logger.CONST_TRESULT_SUCC)

        target_list=''  # 타겟 목록을 튜플로 생성
        if len(targetList) > 1:
            target_list=str(tuple(targetList))
        else:
            target_list='(%s)' % targetList[0]

        ## PlugIn Inst 등록
        req_handler.saveRequestState(dbm, src, tid, 'REGISTER_PLUGIN_INST', progress(progStart, 20))

        atRes=plugin_handler.sendPlugIn(monInfo, rbDB, oba_port, _getDefaultDiscInput())
        if atRes.isFail():
            rbDB.rollback()
            logger.error(atRes.setErr('Send PlugIn Error').ltF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, atRes.errStr())
            if te2e != None:
                te2e.job('감시 PlugIn 전송 및 데이터 저장 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                         '감시 PlugIn 전송 및 데이터 저장 ')
            return atRes

        if te2e != None:
            te2e.job('감시 PlugIn 전송 및 데이터 저장 성공', e2e_logger.CONST_TRESULT_SUCC)

        ## 기존 감시 타겟 정보 조회
        getTargetSql=db_sql.GET_TARGET_BY_SVR(svr_seq)
        ret=rbDB.select(getTargetSql)
        atRes=_res((ret == None), ret, rrl.RS_FAIL_OP, 'Get Target Info Error', 'Get Target Info Error',
                   {'svr_seq': svr_seq})
        if atRes != None:
            if te2e != None:
                te2e.job('기존 감시 대상 데이터 조회 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None, '기존 감시 대상 데이터 조회 ')
            return atRes

        prevTargetList=[]
        for target in ret:
            prevTargetList.append(str(target['target_seq']))

        ## 일반 Item Inst 등록
        req_handler.saveRequestState(dbm, src, tid, 'ADD_ITEM_INST', progress(progStart, 35))
        addItemNoInput=db_sql.INSERT_ITEMINSTANCE_NOINPUT(svr_seq, service_number, target_list)
        ret=rbDB.execute(addItemNoInput)
        atRes=_res((ret == None), ret, rrl.RS_FAIL_OP, 'Insert Item Inst Data Error', 'Insert Item Inst Data Error',
                   {'svr_seq': svr_seq, 'service_number': service_number, 'target_list': target_list})
        if atRes != None:
            if te2e != None:
                te2e.job('일반 감시 항목 데이터 저장 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None, '일반 감시 항목 데이터 저장 ')
            return atRes
        logger.info(rrl.rSc(tid, {'item_cnt': ret},
                            {'svr_seq': svr_seq, 'service_number': service_number, 'target_list': target_list},
                            _msg='Insert Item Inst(NoObj)').lS(FNAME))

        if te2e != None:
            te2e.job('일반 감시 항목 데이터 저장 성공', e2e_logger.CONST_TRESULT_SUCC)

        ## Discovery Item Inst 등록
        req_handler.saveRequestState(dbm, src, tid, 'ADD_DISCOVERY_ITEM_INST', progress(progStart, 50))
        addedItem=0
        targetInfo=None
        for targetInfo in monInfo.targetList:
            targetSeq=str(targetInfo.targetSeq)
            if targetInfo.targetCfg != None:
                _cfg=targetInfo.targetCfg

                ret=rbDB.select(db_sql.GET_DISCOVERY_INPUT_BY_TARGET(targetSeq), 'discovery_cfg_input')
                atRes=_res((ret == None), ret, rrl.RS_FAIL_OP, 'Get Disc Input Error', 'Get Disc Input Error',
                           {'target_seq': targetSeq})
                if atRes != None:
                    if te2e != None:
                        te2e.job('탐색 감시 항목 입력 데이터 조회 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                                 '탐색 감시 항목 입력 데이터 조회 ')
                    return atRes

                if len(ret) > 0:
                    for discCfg in ret:
                        if _cfg.has_key(discCfg):
                            if type(_cfg[discCfg]) == list:
                                _cfgList=_cfg[discCfg]
                            else:
                                _cfgList=[_cfg[discCfg]]
                        else:
                            _cfgList=_getDefaultDiscInput(discCfg)
                        for itemObj in _cfgList:
                            addItemInput=db_sql.INSERT_ITEMINSTANCE_INPUT(svr_seq, str(itemObj), targetSeq,
                                                                          service_number, discCfg)
                            addedItem=addedItem + rbDB.execute(addItemInput)

        logger.info(
            rrl.rSc(tid, {'disc_item_cnt': addedItem}, {'target_seq': targetSeq, 'service_number': service_number},
                    _msg='Insert Item Inst(Obj)').lS(FNAME))

        if te2e != None:
            te2e.job('탐색 감시 항목 입력 데이터 조회 성공', e2e_logger.CONST_TRESULT_SUCC)

        ## Key Inst 등록
        req_handler.saveRequestState(dbm, src, tid, 'ADD_KEY_INST', progress(progStart, 65))
        addKey=db_sql.INSERT_KEYINSTANCE_BY_TARGET(svr_seq, target_list)
        ret=rbDB.execute(addKey)
        atRes=_res((ret == None), ret, rrl.RS_FAIL_OP, 'Insert Key Inst Error', 'Insert Key Inst Error',
                   {'svr_seq': svr_seq, 'target_list': target_list})
        if atRes != None:
            if te2e != None:
                te2e.job('감시 항목 Key 데이터 저장 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                         '감시 항목 Key 데이터 저장 ')
            return atRes
        logger.info(rrl.rSc(tid, {'item_key_cnt': ret}, {'svr_seq': svr_seq, 'target_list': target_list},
                            _msg='Insert Item Key Inst').lS(FNAME))

        if te2e != None:
            te2e.job('감시 항목 Key 데이터 저장 성공', e2e_logger.CONST_TRESULT_SUCC)

        ## 실시간 감시 항목 추가
        req_handler.saveRequestState(dbm, src, tid, 'ADD_REALTIME_ITEM', progress(progStart, 70))
        addRealTimeItem=db_sql.INSERT_INIT_REALTIMEPERF(svr_seq, target_list)
        ret=rbDB.execute(addRealTimeItem)
        atRes=_res((ret == None), ret, rrl.RS_FAIL_OP, 'Insert RealTime Item Error', 'Insert RealTime Item Error',
                   {'svr_seq': svr_seq, 'target_list': target_list})
        if atRes != None:
            if te2e != None:
                te2e.job('실시간 감시 항목 데이터 저장 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                         '실시간 감시 항목 데이터 저장 ')
            return atRes
        logger.info(rrl.rSc(tid, {'realtime_item_cnt': ret}, {'svr_seq': svr_seq, 'target_list': target_list},
                            _msg='Insert RealTime Item').lS(FNAME))

        if te2e != None:
            te2e.job('실시간 감시 항목 데이터 저장 성공', e2e_logger.CONST_TRESULT_SUCC)

        ## View Maping 추가
        wanNum=0
        officeNum=0
        serverNum=0
        extra_wanNum=0
        # 2019.3.7 - lsh
        # PNF 형에서 Zone 을 마음대로 지정할수 있어 Other 로 표시함.
        other_Num=0

        for targetInfo in monInfo.targetList:
            if type(targetInfo.targetMapping) == dict and len(targetInfo.targetMapping.keys()) > 0:
                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_1] ==========> targetInfo.targetCode : %s, targetInfo.targetType : %s' % (
                        targetInfo.targetCode, targetInfo.targetType))

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_11] ==========> targetInfo.targetMapping : %s' % str(targetInfo.targetMapping))

                # 2017.03.08 회선이중화 구분 조건 변경
                wanNum=sa.checkMapInfoNum('wan', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_2] ==========> wanNum : %s' % str(wanNum))

                wanRxNum=sa.checkMapInfoNum('utm.wan.rx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_21] ==========> wanRxNum : %s' % str(wanRxNum))

                if wanNum <= 1 and wanRxNum > 1:
                    wanNum=wanRxNum

                wanTxNum=sa.checkMapInfoNum('utm.wan.tx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_22] ==========> wanTxNum : %s' % str(wanTxNum))

                if wanNum <= 1 and wanTxNum > 1:
                    wanNum=wanTxNum


                extra_wanNum=sa.checkMapInfoNum('extra_wan', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y': logger.info('[addTargetToSvr_23] ==========> extra_wanNum : %s' % str(extra_wanNum))

                extra_wanRxNum=sa.checkMapInfoNum('utm.extra_wan.rx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y': logger.info('[addTargetToSvr_24] ==========> extra_wanRxNum : %s' % str(extra_wanRxNum))

                if extra_wanNum <= 1 and extra_wanRxNum > 1: extra_wanNum=extra_wanRxNum

                extra_wanTxNum=sa.checkMapInfoNum('utm.extra_wan.tx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':logger.info('[addTargetToSvr_25] ==========> extra_wanTxNum : %s' % str(extra_wanTxNum))

                if extra_wanNum <= 1 and extra_wanTxNum > 1: extra_wanNum=extra_wanTxNum


                # 2019. 3. 7 - lsh
                # LAN other 등록
                other_Num=sa.checkMapInfoNum('other', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y': logger.info('[addTargetToSvr_31] ==========> other_Num : %s' % str(other_Num))

                otherRxNum=sa.checkMapInfoNum('utm.other.rx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y': logger.info('[addTargetToSvr_32] ==========> otherRxNum : %s' % str(otherRxNum))

                if other_Num <= 1 and otherRxNum > 1: other_Num=otherRxNum

                otherTxNum=sa.checkMapInfoNum('utm.other.tx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':logger.info('[addTargetToSvr_33] ==========> otherTxNum : %s' % str(otherTxNum))

                if other_Num <= 1 and otherTxNum > 1: other_Num=otherTxNum
                


                officeNum=sa.checkMapInfoNum('office', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_3] ==========> officeNum : %s' % str(officeNum))

                officeRxNum=sa.checkMapInfoNum('utm.office.rx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y': logger.info(
                    '[addTargetToSvr_31] ==========> officeRxNum : %s' % str(officeRxNum))
                if officeNum <= 1 and officeRxNum > 1:
                    officeNum=officeRxNum
                officeTxNum=sa.checkMapInfoNum('utm.office.tx', targetInfo.targetMapping)
                if DEBUG_LOG_YN == 'y': logger.info(
                    '[addTargetToSvr_32] ==========> officeTxNum : %s' % str(officeTxNum))

                if officeNum <= 1 and officeTxNum > 1:
                    officeNum=officeTxNum


                serverNum=sa.checkMapInfoNum('server', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_4] ==========> serverNum : %s' % str(serverNum))

                serverRxNum=sa.checkMapInfoNum('utm.server.rx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y':
                    logger.info('[addTargetToSvr_41] ==========> serverRxNum : %s' % str(serverRxNum))

                if serverNum <= 1 and serverRxNum > 1:
                    serverNum=serverRxNum

                serverTxNum=sa.checkMapInfoNum('utm.server.tx', targetInfo.targetMapping)

                if DEBUG_LOG_YN == 'y': logger.info('[addTargetToSvr_42] ==========> serverTxNum : %s' % str(serverTxNum))

                if serverNum <= 1 and serverTxNum > 1:
                    serverNum=serverTxNum

                if DEBUG_LOG_YN == 'y': logger.info(
                    '[addTargetToSvr_5] ==========> wanNum : %s, extra_wanNum : %s, officeNum : %s, serverNum : %s , other_Num : %s ' % (
                        str(wanNum), str(extra_wanNum), str(officeNum), str(serverNum), str(other_Num)))

                # if targetInfo.targetCode == 'os' or targetInfo.targetType == 'UTM':  # 2017.02.27 회선 이중화에 대한 매핑
                if wanNum > 1 or officeNum > 1 or serverNum > 1 or extra_wanNum > 1 or other_Num > 1 :  # 2017.03.08 회선이중화 구분 조건 변경
                    # 2017.04.28 기존 function과 회선이중화function을 하나로 합침.
                    atRes=_setWebMappingInfoForMultiport(tid, rbDB, svr_seq, targetInfo.targetMapping, targetAt, svrInfo.onebox_type)
                else:
                    atRes=_setWebMappingInfo(tid, rbDB, svr_seq, targetInfo.targetMapping, targetAt, svrInfo.onebox_type)

                if atRes.isFail():
                    rbDB.rollback()
                    logger.error(atRes.setErr('Set Web Mapping Info Error').ltF(FNAME))
                    req_handler.saveRequestFail(dbm, src, tid, atRes.errStr())
                    if te2e != None:
                        te2e.job('종합상황판 Mapping 데이터 설정 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                                 '종합상황판 Mapping 데이터 설정 ')
                    return atRes

        rbDB.execute(db_sql.UPDATE_VIEW_INST_SEQ(svr_seq))
        if te2e != None:
            te2e.job('종합상황판 Mapping 데이터 설정 완료', e2e_logger.CONST_TRESULT_SUCC)

        # TODO :  UPDATE_REALTIME_YN 기능 추가
        # 프로비저닝후 moniteminstance 에 vpn 쪽 realtimeyn 에 'y' 들어갔나 확인필요.
        ret=rbDB.execute(db_sql.UPDATE_REALTIME_YN(svr_seq))
        if (ret == None):
            logger.error('UPDATE_REALTIME_YN Error ')

        ## zabbix agent에 설정 파일 전송 및 재기동
        req_handler.saveRequestState(dbm, src, tid, 'ZBAGENT_SETTING', progress(progStart, 85))

        atRes=xclient_handler.settingMonAgent(rbDB, oba_port, zbaCfgDir, monInfo)

        if atRes.isFail():
            rbDB.rollback()
            logger.error(atRes.setErr('Set Monitoring Agent Error').ltF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, atRes.errStr())
            if te2e != None:
                te2e.job('zabbix agent 설정 파일 전송 및 재기동 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                         'zabbix agent 설정 파일 전송 및 재기동 ')
            return atRes

        if te2e != None:
            te2e.job('zabbix agent 설정 파일 전송 및 재기동 성공', e2e_logger.CONST_TRESULT_SUCC)

        sleep(3)

        ## ZB 서버 설정
        req_handler.saveRequestState(dbm, src, tid, 'ZBSERVER_SETTING', progress(progStart, 90))
        ret=zbm_api.modHost(logger, svrOBID, prevTargetList + targetList)
        if ret == False:
            rbDB.rollback()
            atRes=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Set ZB Host Template Error', None,
                          {'host': svrOBID, 'template': prevTargetList + targetList})
            logger.error(atRes.lF(FNAME))
            req_handler.saveRequestFail(dbm, src, tid, 'Set ZB Host Template Error')
            if te2e != None:
                te2e.job('감시 템플릿 설정 실패(zabbix)', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None,
                         'Zabbix 시스템에 서버의 감시 템플릿 설정 ')
            return atRes

        if te2e != None:
            te2e.job('감시 템플릿 설정 성공(zabbix)', e2e_logger.CONST_TRESULT_SUCC)

        rbDB.commit()

        ## ZB 임계치 설정
        req_handler.saveRequestState(dbm, src, tid, 'ZBSERVER_THRESHOLD_SETTING', progress(progStart, 95))
        try:
            ## Item 임계치 설정
            strsql = db_sql.GET_ITEM_INST_BY_TARGETLIST(svr_seq, target_list)
            _itemList=dbm.select(strsql)

            strsql = db_sql.GET_D_ITEM_INST_BY_TARGETLIST(svr_seq, target_list)
            _dItemList=dbm.select(strsql)

            iList=_itemList + _dItemList
            for _itemInfo in iList:

                strsql=db_sql.GET_THRES_CAT(_itemInfo['monitemcatseq'])
                _thrCatList=dbm.select(strsql)
                thrParam={'item_seq': _itemInfo['moniteminstanceseq'], 'threshold': []}


                # Item 목록에서 아이템 별 start_value 값 추출
                _tmp_cdtList=[]
                _op_type=None

                for _thrInfo in _thrCatList:
                    _tmp_cdt=json.loads(_thrInfo['condition'])

                    if type(_tmp_cdt) is list:

                        for pc in _tmp_cdt:
                            if type(pc) is dict:
                                _tmp_cdtList.append(pc['value'])
                            else:
                                continue
                                # 2017.04.04 str_api.py 사용
                                # _tmp_cdtList = sa.dictValuesinList(_tmp_cdt, _tmp_cdtList, 'value')

                    else:
                        _tmp_cdtList.append(_tmp_cdt['value'])

                    _op_type=_thrInfo['condition_type']


                start_value=None
                if _op_type != None:
                    if _op_type.upper() == "GE":  # 이상
                        start_value=min(_tmp_cdtList)
                    else:
                        start_value=max(_tmp_cdtList)

                # 임계치 설정
                for _thrInfo in _thrCatList:
                    thrGrade=_thrInfo['fault_grade']
                    thrName='[%s] %s Fault' % (thrGrade, _itemInfo['monitoritem'])
                    cdt=json.loads(_thrInfo['condition'])
                    thrInfo={'name': thrName, 'grade': thrGrade, 'repeat': _thrInfo['repeat'], 'conditions': cdt,
                             'description': _thrInfo['description'], 'operator': _thrInfo['condition_type'],
                             'op_type': _thrInfo['condition_type'], 'start_value': start_value}


                    thrParam['threshold'].append(thrInfo)
                atRes=setOBThreshold(tid, thrParam, dbm, False, True)

                if atRes.isFail():
                    logger.error(atRes.setErr('Set ZB HostThreshold Error, threshold=%s' % str(thrParam)).ltF(FNAME))
                    req_handler.saveRequestFail(dbm, src, tid, atRes.errStr())
                    de2e=None
                    if te2e != None:
                        te2e.job('장애 임계치 설정 실패', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr(), None, '장애 임계치 설정 ')
                        te2e.job('감시 템플릿 해제', e2e_logger.CONST_TRESULT_NONE, atRes.errStr(), None, '감시 템플릿 해제 ')
                        de2e=e2e_logger.e2elogger('템플릿 해제', 'orch-M', tid, tPath + '/delTarget', None, None, None,
                                                  e2eUrl)
                    _delTarget(tid, de2e, svr_seq, svrOBID, svrIP, targetList, dbm)
                    if te2e != None:
                        te2e.job('감시 템플릿 해제', e2e_logger.CONST_TRESULT_SUCC)
                    return atRes

            if te2e != None:
                te2e.job('장애 임계치 설정 성공', e2e_logger.CONST_TRESULT_SUCC)

        except Exception, e:
            atRes=rrl.rFa(tid, rrl.RS_EXCP, 'Set ZB HostThreshold Exception, e=%s' % str(e), None, None)
            logger.error(atRes.lF(FNAME))
            logger.fatal(e)
            req_handler.saveRequestFail(dbm, src, tid, 'Set ZB HostThreshold Exception')
            de2e=None
            if te2e != None:
                te2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr())
                te2e.job('감시 템플릿 해제', e2e_logger.CONST_TRESULT_NONE, atRes.errStr(), None, '감시 템플릿 해제 ')
                de2e=e2e_logger.e2elogger('템플릿 해제', 'orch-M', tid, tPath + '/delTarget', None, None, None, e2eUrl)
            _delTarget(tid, de2e, svr_seq, svrOBID, svrIP, targetList, dbm)
            if te2e != None:
                te2e.job('감시 템플릿 해제', e2e_logger.CONST_TRESULT_SUCC)
            return atRes

        req_handler.saveRequestComplete(dbm, src, tid)
        logger.info(rrl.rSc(tid, None, None).lS(FNAME))

        # 2017. 11. 29 - lsh
        # 김승주 전임 요청으로 시작시 장비상태 체크 로직 제거.
        # itemChk=ItemChecker(svr_seq, svrOBID, dbm, tid)
        # itemChk.start()

        atRes=rrl.rSc(tid, None, None)
        logger.info(atRes.lS(FNAME))

        return atRes



    except Exception, e:
        rbDB.rollback()
        atRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(atRes.lF(FNAME))
        logger.fatal(e)
        req_handler.saveRequestFail(dbm, src, tid, e)
        if te2e != None:
            te2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, atRes.errStr())
        return atRes
    finally:
        rbDB.close()


def _rollbackModItem(tid, zbModified, isItemProto, svrOBID, key, dKey=None, prevPeriod=None, prevHist=None,
                     prevTrend=None):
    """
    - FUNC: ZB 변경 Item RollBack
    - INPUT
        tid(M): 요청 TID
        zbModified(M): ZB Item 변경 여부
        isItemProto(M): Disc Item 여부
        svrOBID(M): 서버 OB ID
        key(M): Item Key
        dKey(O): Disc Key
        prevPeriod(O): 변경 전 감시 주기
        prevHist(O): 변경 전 이력 저장 기간
        prevTrend(O): 변경 전 통계 저장 기간
    """
    FNAME='RollBack Modified Item'

    if zbModified == None or isItemProto == None or svrOBID == None or key == None:
        logger.error(rrl.rFa(tid, rrl.RS_INVALID_PARAM, None, None,
                             {'zb_mod': zbModified, 'is_disc_item': isItemProto, 'svr_obid': svrOBID, 'key': key}).lF(
            FNAME))
        return

    if isItemProto and (dKey == None or dKey == ''):
        logger.error(
            rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Disc Key', None, {'is_disc_item': isItemProto, 'disc_key': dKey}).lF(
                FNAME))
        return

    if zbModified and prevPeriod == None and prevHist == None and prevTrend:
        logger.error(rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Input Data for Zabbix ItemUpdate', None,
                             {'zb_mod': zbModified, 'prev_period': prevPeriod, 'prev_hist': prevHist,
                              'prev_trend': prevTrend}).lF(FNAME))
        return

    if zbModified and not isItemProto:
        zbm_api.setItemPeriod(logger, svrOBID, key, period=prevPeriod, history=prevHist, trend=prevTrend)
        return
    elif zbModified and isItemProto:
        zbm_api.modItemProtoInst(logger, svrOBID, key, dKey, period=prevPeriod, history=prevHist, trend=prevTrend)
        return


## discovery item은 전체 item에 적용됨
def setItemPeriod(tid, params, dbm):
    """
    - FUNC: 감시 항목 주기 설정(감시 주기, 이력 저장일, 통계 저장일)
    - INPUT
        tid(M): 요청 TID
        params(M): 주기 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 항목 주기 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Set Item Period'

    zbModified=False
    isItemProto=False
    prevItemInst=key=svrOBID=dKey=None
    try:
        svrSeq=params['svr_seq']
        itemSeq=params['item_seq']
        newPeriod=(lambda x: str(x['new_period']) if x.has_key('new_period') else None)(params)
        newHistory=(lambda x: str(x['new_history']) if x.has_key('new_history') else None)(params)
        newStat=(lambda x: str(x['new_statistic']) if x.has_key('new_statistic') else None)(params)

        ## 유효성 검사
        if newPeriod == None and newHistory == None and newStat == None:
            rres=rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Period Parameter', None,
                         {'new_period': newPeriod, 'new_history': newHistory, 'new_steatistic': newStat})
            logger.error(rres.lF(FNAME))
            return rres

        ## 이전 데이터 복사
        ret=dbm.select(db_sql.GET_ITEM_INST(svrSeq, itemSeq))
        if ret == None or len(ret) < 1:
            if ret == None:
                rsCode=rrl.RS_FAIL_DB
            else:
                rsCode=rrl.RS_NO_DATA
            rres=rrl.rFa(tid, rsCode, 'Get Item Inst Info Error', ret, {'svr_seq': svrSeq, 'item_seq': itemSeq})
            logger.error(rres.lF(FNAME))
            return rres
        prevItemInst=ret[0]

        ### FOR ZB
        if newPeriod != None or newHistory != None or newStat != None:
            ## 정보 조회: svrOBID, key
            ret=dbm.select(db_sql.GET_KEY_INST_BY_SVR_ITEM_FOR_MOD(svrSeq, itemSeq))
            if ret == None or len(ret) < 1 or len(ret) > 1:
                if ret == None:
                    rsCode=rrl.RS_FAIL_DB
                elif len(ret) < 1:
                    rsCode=rrl.RS_NO_DATA
                else:
                    rsCode=rrl.RS_DUPLICATE_DATA
                rres=rrl.rFa(tid, rsCode, 'Get Item Key Info Error', ret, {'svr_seq': svrSeq, 'item_seq': itemSeq})
                logger.error(rres.lF(FNAME))
                return rres

            ## ZB Item 변경
            svrOBID=str(ret[0]['onebox_id'])
            key=str(ret[0]['_key'])
            dKey=(lambda x: None if x == None or x == '' else x)(ret[0]['zbkey'])

            if dKey == None or dKey == '':
                dKey=None
                ret=zbm_api.setItemPeriod(logger, svrOBID, key, period=newPeriod, history=newHistory, trend=newStat)
            else:
                isItemProto=True
                ret=zbm_api.modItemProtoInst(logger, svrOBID, key, dKey, period=newPeriod, history=newHistory,
                                             trend=newStat)
            if ret == False:
                rres=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Modify ZB Item Period Error', None,
                             {'host': svrOBID, 'item_key': key})
                logger.error(rres.lF(FNAME))
                return rres
            zbModified=True

        ## Orch-M DB 반영
        ret=dbm.execute(
            db_sql.UPDATE_ITEM_INST_ALL_FOR_MOD(svrSeq, itemSeq, _newPeriod=newPeriod, _newHistroy=newHistory,
                                                _newStat=newStat))
        if ret == None or ret < 1:
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Item Inst Data Error', ret,
                         {'svr_seq': svrSeq, 'item_seq': itemSeq})
            logger.error(rres.lF(FNAME))
            _rollbackModItem(tid, zbModified, isItemProto, svrOBID, key, dKey, prevItemInst['period'],
                             prevItemInst['hist_save_month'], prevItemInst['stat_save_month'])
            return rres

        rres=rrl.rSc(tid, {'tid': tid}, None)
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        _rollbackModItem(tid, zbModified, isItemProto, svrOBID, key, dKey, prevItemInst['period'],
                         prevItemInst['hist_save_month'], prevItemInst['stat_save_month'])
        return rres


## discovery 개별 적용 가능
def setItemMonStatus(tid, params, dbm, forced=False, isSuspend=False):
    """
    - FUNC: 감시 항목 감시 On/Off 설정(resume/suspend도 처리)
    - INPUT
        tid(M): 요청 TID
        params(M): 감시 On/Off 정보
        dbm(M): DB 연결 객체
        forced(O): 감시 상태가 기존 설정과 동일하더라도 기능 실행
        isSuspend(O): resume/suspend 요청인지 확인(resume/suspend 일 경우 DB의 suspend 컬럼 사용)
    - OUTPUT: 감시 항목 감시 On/Off 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Set Item Monitoring Status'

    try:
        modField=(lambda x: 'suspend_yn' if x else 'monitoryn')(isSuspend)

        svrSeq=str(params['svr_seq'])
        itemSeq=str(params['item_seq'])
        newYN=str(params['monitor_yn']).lower()

        isOff=(lambda x: True if x == 'n' else False)(newYN)
        if isSuspend:
            newYN=(lambda x: 'y' if x == 'n' else 'n')(newYN)

        ## 이전 데이터 복사
        ret=dbm.select(db_sql.GET_ITEM_INST(svrSeq, itemSeq, isSuspend))
        if ret == None or len(ret) < 1:
            if ret == None:
                rsCode=rrl.RS_FAIL_DB
            else:
                rsCode=rrl.RS_NO_DATA
            rres=rrl.rFa(tid, rsCode, 'Get Item Inst Error', ret,
                         {'svr_seq': svrSeq, 'item_seq': itemSeq, 'suspend_yn': isSuspend})
            logger.error(rres.lF(FNAME))
            return rres
        prevItemInst=ret[0]
        prevIsOff=(lambda x: True if x == 'n' else False)(prevItemInst[modField])
        realtime_yn=prevItemInst['realtimeyn']

        if not forced and isOff == prevIsOff:
            rres=rrl.rSc(tid, {'tid': tid}, params, _msg='Same Monitoring Status')
            logger.info(rres.lS(FNAME))
            return rres

        ## 정보 조회
        ret=dbm.select(db_sql.GET_KEY_INST_BY_SVR_ITEM_FOR_MOD(svrSeq, itemSeq))
        if ret == None or len(ret) < 1 or len(ret) > 1:
            if ret == None:
                rsCode=rrl.RS_FAIL_DB
            elif len(ret) < 1:
                rsCode=rrl.RS_NO_DATA
            else:
                rsCode=rrl.RS_DUPLICATE_DATA
            rres=rrl.rFa(tid, rsCode, 'Get Item Key Inst Error', ret, {'svr_seq': svrSeq, 'item_seq': itemSeq})
            logger.error(rres.lF(FNAME))
            return rres

        svrOBID=str(ret[0]['onebox_id'])
        iKey=str(ret[0]['org_key'])

        ## Zabbix 반영
        ret=zbm_api.setItemMonStatus(logger, svrOBID, iKey, isOff)
        if ret == False:
            rres=rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Set ZB Item Monitoring Status Error', None,
                         {'host': svrOBID, 'item_key': iKey, 'is_off': isOff})
            logger.error(rres.lF(FNAME))
            return rres

        ## orch-m Db 반영
        if isSuspend:
            ret=dbm.execute(db_sql.UPDATE_ITEM_INST_EACH_FOR_MOD(svrSeq, itemSeq, _newSuspend=newYN))
        else:
            ret=dbm.execute(db_sql.UPDATE_ITEM_INST_EACH_FOR_MOD(svrSeq, itemSeq, _newMonYN=newYN))
        if ret == None or ret < 1:
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update Item Monitoring Status Error', ret,
                         {'svr_seq': svrSeq, 'item_seq': itemSeq, 'off_yn': newYN})
            logger.error(rres.lF(FNAME))
            ## rollback
            zbm_api.setItemMonStatus(logger, svrOBID, iKey, prevIsOff)
            return rres

        ## RealTime 항목에 반영
        if not isSuspend:
            realTimeParam={'svr_seq': svrSeq, 'item_seq': itemSeq, 'realtime_yn': realtime_yn}
            rres=setRealItemItem(tid, realTimeParam, dbm, True)
            if rres.isFail():
                logger.error(rres.ltF(FNAME))
                return rres

        rres=rrl.rSc(tid, {'tid': tid}, None)
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres


## discovery 개별 적용 가능
def setRealItemItem(tid, params, dbm, isCallMonStaus=False):
    """
    - FUNC: 실시간 감시 항목 설정
    - INPUT
        tid(M): 요청 TID
        params(M): 실시간 감시 항목 정보
        dbm(M): DB 연결 객체
        isCallMonStaus(O): Monitoring Status 설정 함수에서 호출한 것인지 여부(False 일 경우, 이전 상태와 같아도 기능 수행)
    - OUTPUT: 실시간 감시 항목 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Set Item Monitoring Status'

    try:
        svrSeq=str(params['svr_seq'])
        itemSeq=str(params['item_seq'])
        newRealTimeYN=str(params['realtime_yn']).lower()

        ## 이전 데이터 복사
        ret=dbm.select(db_sql.GET_ITEM_INST(svrSeq, itemSeq))
        if ret == None or len(ret) < 1:
            if ret == None:
                rsCode=rrl.RS_FAIL_DB
            else:
                rsCode=rrl.RS_NO_DATA
            rres=rrl.rFa(tid, rsCode, 'Get Item Inst Error', ret, {'svr_seq': svrSeq, 'item_seq': itemSeq})
            logger.error(rres.lF(FNAME))
            return rres
        prevItemInst=ret[0]
        prevRealTimeYN=prevItemInst['realtimeyn']
        monitorYN=prevItemInst['monitoryn']

        if not isCallMonStaus and newRealTimeYN == prevRealTimeYN:
            rres=rrl.rSc(tid, {'tid': tid}, None, _msg='Same RealTime Status')
            logger.info(rres.lS(FNAME))
            return rres

        ## orch-m Db 반영
        ret=dbm.execute(db_sql.UPDATE_ITEM_INST_EACH_FOR_MOD(svrSeq, itemSeq, _newRealTimeYN=newRealTimeYN))
        if ret == None or ret < 1:
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update RealTime Item Inst Error', ret,
                         {'svr_seq': svrSeq, 'item_seq': itemSeq, 'realtime_yn': newRealTimeYN})
            logger.error(rres.lF(FNAME))
            return rres

        if monitorYN == 'y' and newRealTimeYN == 'y':
            ret=dbm.execute(db_sql.INSERT_INIT_REALTIMEPERF_BY_ITEM(svrSeq, itemSeq))
        elif monitorYN == 'n' or newRealTimeYN == 'n':
            ret=dbm.execute(db_sql.REMOVE_REALTIMEPERF_ITEM(svrSeq, itemSeq))

        rres=rrl.rSc(tid, {'tid': tid}, None)
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres


## svr_seq, item_cat_seq, object_list
def modItemObject(tid, params, dbm):
    """
    - FUNC: 감시항목 Object 설정
    - INPUT
        tid(M): 요청 TID
        params(M): 감시항목 Object 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Modify Item Object'


    # TODO : 설변시 extra_wan 처리 - 2018. 3.22

    svrSeq=None
    icSeq=None
    iObjList=None
    rbDB=dbm.getRollBackDB()

    added=False
    deleted=False
    try:
        svrSeq=params['svr_seq']
        icSeq=params['item_cat_seq']
        iObjList=(lambda x: x['object_list'] if x.has_key('object_list') else [])(params)

        ## 기존 아이템 정보 가져오기
        prevList=rbDB.select(db_sql.GET_ITEMINSTANCE_FOR_MOD_OBJ(svrSeq, icSeq))
        if prevList == None or len(prevList) < 1:
            if prevList == None:
                rsCode=rrl.RS_FAIL_DB
            else:
                rsCode=rrl.RS_NO_DATA

            rres=rrl.rFa(tid, rsCode, 'Get Item Inst Error', prevList, params)
            logger.error(rres.lF(FNAME))
            return rres

        for objInfo in iObjList:
            obj=str(objInfo)

            ## 동일 object 정보  스킵
            isPass=False
            for prevInfo in prevList:
                if str(prevInfo['monitorobject']) == obj:
                    prevList.remove(prevInfo)
                    isPass=True
                    break

            if isPass:
                continue

            #### 추가
            ## Item 설정
            addExtraItemInput=db_sql.INSERT_EXTRA_ITEMINSTANCE_FOR_MOD_OBJ(svrSeq, icSeq, obj)
            iiSeq=rbDB.execute(addExtraItemInput, True)
            if iiSeq == None:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert Item Inst Object Error', None, params)
                logger.error(rres.lF(FNAME))
                return rres

            ## Item Key 설정
            addExtraKey=db_sql.INSERT_EXTRA_KEYINSTANCE_FOR_MOD_OBJ(iiSeq)
            ret=rbDB.execute(addExtraKey)
            if ret == None or ret < 1:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert Item Key Inst Error', ret, {'item_inst_seq': iiSeq})
                logger.error(rres.lF(FNAME))
                return rres

            added=True

        ## 삭제
        for prevInfo in prevList:
            iiSeq=prevInfo['moniteminstanceseq']

            ## 장애 해제 처리
            updAlarm=db_sql.UPDATE_CURR_ALARM_FOR_MOD_OBJ(iiSeq, '삭제 처리')
            rbDB.execute(updAlarm)
            rbDB.execute(db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE())

            ## Key 삭제
            delKeyInst=db_sql.REMOVE_KEY_FOR_MOD_OBJ(iiSeq)
            rbDB.execute(delKeyInst)

            ## Item 삭제
            delItemInst=db_sql.DEL_ITEMINSTANCE_FOR_MOD_OBJ(iiSeq)
            rbDB.execute(delItemInst)

            ## RealTime Perf 삭제
            delReal=db_sql.REMOVE_REALTIMEPERF_ITEM(svrSeq, iiSeq)
            rbDB.execute(delReal)

            _delRowNoUse('tb_moniteminstance', 'moniteminstanceseq', rbDB)

            deleted=True

        ## PlugIn Config 설정
        if added or deleted:
            rres=plugin_handler.modPlugInDiscList(rbDB, svrSeq, icSeq, iObjList, oba_port)
            if rres.isFail():
                rbDB.rollback()
                logger.error(rres.setErr('Modify PlugIn Config Error').ltF(FNAME))
                return rres

        rbDB.commit()
        rres=rrl.rSc(tid, {'tid': tid}, None)
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres
    finally:
        rbDB.close()


## 2022. 5. 10 - lsh
# snmp host 추가 
def zabbix_host_create(tid, params, dbm, cfg):
    """
    - FUNC: snmp host 추가 
    - INPUT
        tid(M): 요청 TID
        params(M): Host Name
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Zabbix Host Create'
    
    rbDB=dbm.getRollBackDB()
    try:
        serverseq = params['serverseq']
        ret=rbDB.select(db_sql.GET_SNMP_HOST_INFO(serverseq))
        
        if ret == None :
            rsCode=rrl.RS_FAIL_DB
            rres=rrl.rFa(tid, rsCode, 'ZABBIX_HOST_CREATE Error', serverseq, params)
            logger.error(rres.lF(FNAME))
            return rres

        snmp_info = ret[0]
       
        logger.info (snmp_info)
        # DB 작업
        ## 서버 타입 GET
        # ret=rbDB.select(db_sql.GET_SERVER_TYPE(serverseq), 'svr_type')
        # if ret == None or len(ret) != 1 :
        #     rsCode=rrl.RS_FAIL_DB
        #     rres=rrl.rFa(tid, rsCode, 'ZABBIX_HOST_CREATE GET_SERVER_TYPE Error', serverseq, params)
        #     logger.error(rres.lF(FNAME))
        #     return rres

        # svrType=ret[0]
        # tb_maphostinstance 추가, server UUID 필요.
        
        svrUuid = snmp_info['serveruuid']
        service_number = snmp_info['service_number']
        svrOBID = snmp_info['onebox_id']
        svrIP = snmp_info['public_ip']
        zbaPort = 161 if snmp_info['port'] == '' else snmp_info['port']
        zbGroup = snmp_info['zabbix_group']

   
        ret=rbDB.execute(db_sql.INSERT_SERVER(serverseq, svrUuid, svrOBID, svrIP, zbaPort))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'INSERT_SERVER Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        
        if zbGroup == 'Icmp':
            ret=rbDB.execute(db_sql.INSERT_VIEW_ICMP(serverseq))            
            target_list='(%s)' % cfg['icmp_template_seq']
        else :
            ret=rbDB.execute(db_sql.INSERT_VIEW_SNMP(serverseq))            
            target_list='(%s)' % cfg['smmp_template_seq']
            
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'INSERT_VIEW_SNMP(ICMP) Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres

        logger.info (cfg)
        
        
        ret=rbDB.execute(db_sql.INSERT_ITEMINSTANCE_SNMP( serverseq, service_number, target_list ) )
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'INSERT_ITEMINSTANCE_NOINPUT Error', ret, {'serverseq': serverseq, 'targetseq': target_list})
            logger.error(rres.lF(FNAME))
            return rres

        ret=rbDB.execute(db_sql.INSERT_KEYINSTANCE_BY_TARGET(serverseq, target_list))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'INSERT_KEYINSTANCE_BY_TARGET Error', ret, {'serverseq': serverseq, 'targetseq': target_list})
            logger.error(rres.lF(FNAME))
            return rres

        ret=rbDB.execute(db_sql.INSERT_INIT_REALTIMEPERF(serverseq, target_list))
        
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'INSERT_INIT_REALTIMEPERF Error', ret, {'serverseq': serverseq, 'targetseq': target_list})
            logger.error(rres.lF(FNAME))
            return rres

        rbDB.execute(db_sql.UPDATE_VIEW_INST_SEQ(serverseq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'UPDATE_VIEW_INST_SEQ Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres

        # DB 작업 완료 되면 Zabbix 에 Host 추가
        template_model = rbDB.select(db_sql.GET_ONEBOX_TEMPLATE_MODEL())
        logger.debug("template_model = %s" % str(template_model))
        if zabbix_api.create_host(snmp_info, cfg, template_model, logger) :
            rres=rrl.rSc(tid, {'tid': tid}, None)
            logger.info(rres.lS(FNAME))
        else :
            rres=rrl.rFa(tid, rrl.RS_EXCP, 'Zabbix Host create fail !', None, None)
            logger.error(rres.lF(FNAME))

        rbDB.commit()
        return rres
        
    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres
    finally:
        rbDB.close()


## 2022. 5. 10 - lsh
# snmp host 제거
def zabbix_host_delete(tid, params, dbm, cfg):
    """
    - FUNC: snmp host 제거
    - INPUT
        tid(M): 요청 TID
        params(M): Host Name
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Zabbix Host Delete'
    rbDB=dbm.getRollBackDB()

    try:

        import redis
        redis = redis.StrictRedis(host=cfg['zb_ip'], db=2)

        serverseq = params['serverseq']
        ret=rbDB.select(db_sql.GET_SNMP_HOST_INFO(serverseq))
        if ret == None :
            rsCode=rrl.RS_FAIL_DB
            rres=rrl.rFa(tid, rsCode, 'ZABBIX_HOST_DELETE Error', serverseq, params)
            logger.error(rres.lF(FNAME))
            return rres

        onebox_id = ret[0]['onebox_id']
        zbGroup = ret[0]['zabbix_group']
        
        ## curr/hist 알람 장애 미조치 내역 내용 변경 -> 서비스 해지
        ret=rbDB.execute(db_sql.UPDATE_CURR_ALARM_FOR_DEL_SVR_SNMP(onebox_id, '서비스 해지'))
        if ret == None :
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'UPDATE_CURR_ALARM_FOR_DEL_SVR Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres

        logger.info ('Update Current Alarm 최근 장애 데이터 서비스 해지 처리')
        ret=rbDB.execute(db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE())
        if ret == None :
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres

        logger.info('Update History Alarm 장애 이력 데이터 동기화')

        # Threshold Instance 제거
        ret=rbDB.execute(db_sql.REMOVE_THRESHOLD_INST_SNMP(serverseq))
        if ret == None :
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'REMOVE_THRESHOLD_INST_SNMPError', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres

        # Key Instance 제거
        ret=rbDB.execute(db_sql.REMOVE_KEYINSTANCE_SNMP(serverseq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'REMOVE_KEYINSTANCE_SNMP Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        logger.info('Remove Zabbix Key Instance 감시 항목 Key 데이터 제거')

        # Item Instance 제거

        ret=rbDB.execute(db_sql.DEL_ITEMINSTANCE_SNMP(serverseq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'DEL_ITEMINSTANCE_SNMP Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        
        logger.info('Delete Item Instance 감시 항목 데이터 제거')

        # RealTime 성능 제거
        ret=rbDB.execute(db_sql.REMOVE_REALTIMEPERF_SNMP(serverseq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'DEL_ITEMINSTANCE Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        logger.info('Remove RealTime PerfData 실시간 성능 데이터 제거')


        ret=dbm.execute(db_sql.REMOVE_WEB_MAPPING(serverseq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'DEL_ITEMINSTANCE Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        logger.info('Remove WebMapping Info, 종합상황판 Mapping 데이터 서버 제거')


        # 17.10.25 - tb_smsschedule 에서 삭제
        ret=dbm.execute(db_sql.DEL_SMSSCHEDULE (serverseq))
        if ret == None :
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'DEL_ITEMINSTANCE Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        logger.info('Delete smsschedule , SMS 스케쥴 서버 제거')

        # 안쓰는 RealTime Item 제거
        ret=dbm.execute(db_sql.REMOVE_REALTIME_ITEM_UNUSED ())
        if ret == None :
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'DEL_ITEMINSTANCE Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres
        logger.info('Remove Unused RealTime PerfData')

        ret=rbDB.execute(db_sql.REMOVE_HOSTINSTANCE_BY_SERVER(serverseq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'REMOVE_HOSTINSTANCE_BY_SERVER Error', ret, {'serverseq': serverseq})
            logger.error(rres.lF(FNAME))
            return rres

        # redis delete
        # 같은 onebox_id 로 재등록 했을 경우, 데이터 중복 방지
        keyList = ['', 'vpnstatus', 'wantotal', 'tx_rate', 'wanstatus', 'rx_rate']
        redisKey = None

        for rk in keyList:
            if rk == None or rk == '':
                redisKey = onebox_id
            else:
                redisKey = '%s.%s' % (str(onebox_id),  str(rk))

            logger.debug('redisKey = %s' % str(redisKey))
            redis.delete(redisKey)

        redis.close()


        if zabbix_api.delete_host(onebox_id, cfg, logger) :
            rres=rrl.rSc(tid, {'tid': tid}, None)
            logger.info(rres.lS(FNAME))
        else :
            rres=rrl.rFa(tid, rrl.RS_EXCP, 'Zabbix Host delete fail !', None, None)
            logger.error(rres.lF(FNAME))
        return rres
    
    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres
    finally:
        rbDB.close()



def zabbix_host_update(tid, params, dbm, cfg):
    """
    - FUNC: snmp host 제거
    - INPUT
        tid(M): 요청 TID
        params(M): Host Name
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Zabbix Host Update'
    rbDB=dbm.getRollBackDB()
    try:
        serverseq = params['serverseq']
        ret=rbDB.select(db_sql.GET_SNMP_HOST_INFO(serverseq))
        
        if ret == None :
            rsCode=rrl.RS_FAIL_DB
            rres=rrl.rFa(tid, rsCode, 'ZABBIX_HOST_UPDATE Error', serverseq, params)
            logger.error(rres.lF(FNAME))
            return rres

        snmp_info = ret[0]
        
        if zabbix_api.update_host(snmp_info, cfg, logger) :
            rres=rrl.rSc(tid, {'tid': tid}, None)
            logger.info(rres.lS(FNAME))
        else :
            rres=rrl.rFa(tid, rrl.RS_EXCP, 'Zabbix Host update fail !', None, None)
            logger.error(rres.lF(FNAME))
        return rres
    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres
    finally:
        rbDB.close()


def zabbix_host_snmp_check(tid, params):
    """
    - FUNC: zabbix host snmp check
    - INPUT
        tid(M): 요청 TID
        params(M): Host Name
    - OUTPUT: SNMP Device 정보
        rrl_handler._ReqResult
    """
    FNAME='Zabbix Host SNMP Check'
    
    try:
        return_value = {'tid': tid }
        snmp_info = {}
        snmp_info = params
        #snmp_info['snmp_ver'] = 'v2c'
        #snmp_info['snmp_community'] = 'flex@2022'
        #snmp_info['snmp_ip'] = '183.102.117.100'
        #snmp_info['snmp_port'] = 161

        # Device Model
        snmp_info['snmp_oid'] = ['.1.3.6.1.2.1.1.5.0']

        # ICMP
        return_value['icmp_check'] = "OK" if zabbix_api.ping_check(snmp_info['snmp_ip']) == 1 else "FAIL"
    except Exception, e:
        return_value['icmp_check'] = "FAIL"

    try :         
        # SNMP
        ret = zabbix_api.snmp_get(snmp_info)
        return_value['snmp_check'] = ret['value'] if ret['value'] != '0' else "FAIL"
    except Exception, e:
        return_value['snmp_check'] = "FAIL"
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        
    rres=rrl.rSc(tid, return_value, None)
    logger.info(rres.lS(FNAME))
    return rres



## 2020. 4. 7 - lsh
# ping.sh 감시 item 추가를 위한 API 
def addItemPing(tid, params, dbm):
    """
    - FUNC: 감시항목 추가 ( ping.sh )
    - INPUT
        tid(M): 요청 TID
        params(M): Onebox ID
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object 설정 결과
        rrl_handler._ReqResult
    """
    FNAME='Add Item, Ping '
    rbDB=dbm.getRollBackDB()
    try:

        lst_onebox_id=params['onebox_id']
        # onebox id를 여러개 처리 
        for onebox_id in lst_onebox_id :
            svrSeq=None
            icSeq=None

            ret=rbDB.select(db_sql.GET_SVR_SEQ(onebox_id))
            if ret == None:
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'ServerSeq Error', ret, {'onebox_id': onebox_id})
                logger.error(rres.lF(FNAME))
                return rres

            if len(ret) < 1 :
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'No Server', ret, {'onebox_id': onebox_id})
                logger.error(rres.lF(FNAME))
                return rres


            ip = ret[0]['mgmtip']
            svrSeq = ret[0]['serverseq']

            ## 등록된 ITEM 인지 확인 
            ret=rbDB.select(db_sql.GET_PING_ITEM(svrSeq))
            if ret == None or len(ret) > 0:
                if ret == None:
                    rsCode=rrl.RS_FAIL_DB
                    rres=rrl.rFa(tid, rsCode, 'GET_PING_ITEM Error', svrSeq, params)
                else:
                    rsCode=rrl.RS_ALREADY_EXIST
                    rres=rrl.rFa(tid, rsCode, 'Already Existed Item', svrSeq, params)

                logger.error(rres.lF(FNAME))
                return rres


            ## PluginInstance 에 추가.
            ipluginseq=rbDB.execute(db_sql.INSERT_ITEM_PING(svrSeq), True)
            if ipluginseq == None:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert error, tb_monplugininstance', None, params)
                logger.error(rres.lF(FNAME))
                return rres

            ## ZBA_CONF DB 에 추가.
            ipluginseq=rbDB.execute(db_sql.INSERT_ZBA_INST(svrSeq, ipluginseq), True)
            if ipluginseq == None:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert error, tb_zba_configinstance', None, params)
                logger.error(rres.lF(FNAME))
                return rres

            ## itemcatseq 가져오기
            ret=rbDB.select(db_sql.GET_ITEMCATSEQ(svrSeq))
            if ret == None or len(ret) < 1:
                if icSeq == None:
                    rsCode=rrl.RS_FAIL_DB
                else:
                    rsCode=rrl.RS_NO_DATA
                rres=rrl.rFa(tid, rsCode, 'Get Item Seq Error', icSeq, params)
                logger.error(rres.lF(FNAME))
                return rres

            icSeq = ret[0]['monitemcatseq']
            service_number = ret[0]['service_number']

            #### 추가
            ## Item 설정
            iiSeq=rbDB.execute(db_sql.INSERT_ITEM_INST( svrSeq, icSeq, service_number ), True)
            if iiSeq == None:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert Item Inst Object Error', None, params)
                logger.error(rres.lF(FNAME))
                return rres

            ## Item Key 설정
            ret=rbDB.execute(db_sql.INSERT_PING_KEYINSTANCE(iiSeq))
            if ret == None or ret < 1:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert Item Key Inst Error', ret, {'item_inst_seq': iiSeq})
                logger.error(rres.lF(FNAME))
                return rres

            # Zabbix 에 템플릿이 등록 되어있고, Link 를 끊었다 다시 넣어줘야 
            # 추가된 ITEM 이 동작됨.
            # ping.sh 기능이 OS 템플릿에 적용되어 있어
            # OS 를 뺀 템플릿 List 를 Zabbix 에 넣었다가
            # OS 포함된 템플릿 List 를 다시 호출.
            # Link 를 끊었다 다시 넣어도, 기존 Zabbix Data는 남아있음.

            # OS 제외, 템플릿 적용. 
            ret=rbDB.select(db_sql.GET_TARGET_BY_SVR_WITHOUT_OS(svrSeq))
            if ret == None or ret < 1:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'GET_TARGET_BY_SVR_WITHOUT_OS Error', ret, {'svrSeq': svrSeq})
                logger.error(rres.lF(FNAME))
                return rres

            targetlist = []
            for r in ret :
                targetlist.append (str(r['target_seq']))

            ret=zbm_api.modHost(logger, onebox_id, targetlist)
            if ret:
                logger.info(
                    rrl.rSc(tid, None, {'host': onebox_id, 'remain_template': ret}, _msg='Modify Zabbix Template').lS(
                        FNAME))
            else:
                logger.error(rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Modify Zabbix Template Error', None,
                                    {'host': onebox_id, 'remain_template': ret}).lF(FNAME))


            # 모든 템플릿 다시 적용. 
            ret=rbDB.select(db_sql.GET_TARGET_BY_SVR(svrSeq))
            if ret == None or ret < 1:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'GET_TARGET_BY_SVR Error', ret, {'svrSeq': svrSeq})
                logger.error(rres.lF(FNAME))
                return rres

            targetlist = []
            for r in ret :
                targetlist.append (str(r['target_seq']))

            ret=zbm_api.modHost(logger, onebox_id, targetlist)
            if ret:
                logger.info(
                    rrl.rSc(tid, None, {'host': onebox_id, 'remain_template': ret}, _msg='Modify Zabbix Template').lS(
                        FNAME))
            else:
                logger.error(rrl.rFa(tid, rrl.RS_API_ZBS_ERR, 'Modify Zabbix Template Error', None,
                                    {'host': onebox_id, 'remain_template': ret}).lF(FNAME))

            rbDB.commit()
            ## --- DB 작업 끝

            # 플러그인 재 전송
            # sample data
            # body = {"tid": "", "svr_info": {"onebox_id": "MODEL.OB1", "ip": "220.86.29.36", "seq": 1930}}

            body={ "tid": "ping_item_add-" + str(random.randrange(1000,9999)),
                    "svr_info": {   "onebox_id": onebox_id, 
                                    "ip": ip,
                                    "seq": svrSeq}
                    }        
            ob_plugin_check(body, dbm)




        rres=rrl.rSc(tid, {'tid': tid}, None)
        logger.info(rres.lS(FNAME))
        return rres

    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres
    finally:
        rbDB.close()


def setItemName(tid, params, dbm):
    """
    - FUNC: 감시항목 표시명 변경
    - INPUT
        tid(M): 요청 TID
        params(M): 감시항목 표시명 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 표시명 변경 결과
        rrl_handler._ReqResult
    """
    FNAME='Set Item Name'

    try:
        svrSeq=params['svr_seq']
        itemSeq=params['item_seq']
        itemNewName=params['item_new_name']
        if params.has_key('all_mod_yn') and str(params['all_mod_yn']).lower() == 'y':
            ret=dbm.execute(db_sql.UPDATE_D_ITEM_INST_NAME(svrSeq, itemSeq, itemNewName))
        else:
            ret=dbm.execute(db_sql.UPDATE_ITEM_INST_NAME(svrSeq, itemSeq, itemNewName))

        if ret == None:
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Modify Item Name Error', None, params)
            logger.error(rres.lF(FNAME))
            return rres

        rres=rrl.rSc(tid, {'tid': tid}, params)
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres


def rollbackMonStatus(tid, params, dbm):
    """
    - FUNC: 감시항목 Monitoring 상태 rollback
    - INPUT
        tid(M): 요청 TID
        params(M): 감시항목 모니터링 상태 정보
        dbm(M): DB 연결 객체
    """
    try:
        for param in params:
            setItemMonStatus(tid, param, dbm, True, True)
    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF('RollBack Item Monitoring Status'))
        logger.fatal(e)


def _setSuspendMonitor(tid, params, dbm, isResume=True):
    """
    - FUNC: 감시 항목 resume/suspend
    - INPUT
        tid(M): 요청 TID
        params(M): 감시항목 resume/suspend 정보
        dbm(M): DB 연결 객체
        isResume(O): 감시 항목 Resume 여부(기본 True)
    - OUTPUT: 감시 항목 resume/suspend 결과
        rrl_handler._ReqResult
    """
    FNAME='Suspend/Resume Item Status'

    svrSeq=str(params['svr_info']['seq'])

    itemList=[]
    chkYN=(lambda x: 'y' if x else 'n')(isResume)
    rbYN=(lambda x: 'n' if x else 'y')(isResume)
    try:
        targetList=params['target_info']
        for targetInfo in targetList:
            ret=dbm.select(db_sql.GET_ITEM_INST_SUSP_BY_TARGET(svrSeq, targetInfo['target_seq']))
            for itemInfo in ret:
                iSeq=itemInfo['moniteminstanceseq']
                #                 iMonYN = str(itemInfo['suspend_yn']).lower()
                #                 if iMonYN != chkYN :
                rres=setItemMonStatus(tid, {'svr_seq': svrSeq, 'item_seq': iSeq, 'monitor_yn': chkYN}, dbm, True, True)
                if rres.isFail():
                    logger.warning(rres.lF(FNAME))
                # rollbackMonStatus(tid, itemList, dbm)
                #                     return ret
                else:
                    itemList.append({'svr_seq': svrSeq, 'item_seq': iSeq, 'monitor_yn': rbYN})

        if isResume:
            msg='Resume Monitoring'
        else:
            msg='Suspend Monitoring'

        rres=rrl.rSc(tid, {'tid': tid}, params, _msg=msg)
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        rollbackMonStatus(tid, itemList, dbm)
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres


# 백업 및 복구 작업시 HW, OS, VIM (OpenStack) 변경되었을때
# 템플릿 제거후 재 생성
def tempDeleteAndAdd(tid, tPath, e2eUrl, params, dbm):
    FNAME='Template remove and add '

    logger.info(" params : %s " % str(params))

    svrSeq=str(params['svr_info']['seq'])
    onebox_id=str(params['svr_info']['onebox_id'])
    onebox_ip=str(params['svr_info']['ip'])
    uuid=str(params['svr_info']['uuid'])

    targetList=params['target_info']

    # Model 변경이 있으면 삭제후 추가 한다.
    for targetInfo in targetList :

        target_model=(lambda x: x['target_model'] if x.has_key('target_model') else None)(targetInfo)
        target_type=(lambda x: x['target_type'] if x.has_key('target_type') else None)(targetInfo)
        target_code=(lambda x: x['target_code'] if x.has_key('target_code') else None)(targetInfo)
        vendor_code=(lambda x: x['vendor_code'] if x.has_key('vendor_code') else None)(targetInfo)

        # 저장된 Target Number 가져오기
        strsql = db_sql.GET_TARGET_NO(svrSeq, target_code)
        logger.info ( " GET_TARGET_NO : %s " % strsql )
        ret = dbm.select(strsql)

        if ret == None:
            rres=rrl.rFa(None, rrl.RS_FAIL_DB, 'Getting Target_No Error', ret, targetInfo)
            logger.error(rres.lF(FNAME))
            return rres

        logger.info ( " targetseq : %s " % str( ret[0]['targetseq'] ))

        # DB에 저장된 템플릿 SEQ
        targetseq = ret[0]['targetseq']

        # targetinfo 정보랑 DB 저장된 값이랑 같은지 비교
        strsql = db_sql.GET_TARGETCATSEQ(target_code, target_type, vendor_code, target_model)
        logger.info ( " GET_TARGETCATSEQ : %s " % strsql )
        ret = dbm.select(strsql)

        if ret == None:
            rres=rrl.rFa(None, rrl.RS_FAIL_DB, 'Getting TargetCatSeq Error', ret, targetInfo)
            logger.error(rres.lF(FNAME))
            return rres

        targetcatseq = ret[0]['montargetcatseq']
        logger.info ( " targetcatseq : %s " % str( targetcatseq ))

        if targetseq == targetcatseq :
            continue


        # delete body
        body={ "tid": tid + str(random.randrange(1000,9999)),
                "svr_info": { "onebox_id": "",
                                "ip": "",
                                "uuid": "",
                                "seq": ""},
                "tpath": "WebUI/orch_ns-del",
                "target_info": [{"target_seq": "" }]
                 }

        body['svr_info']['onebox_id'] = onebox_id
        body['svr_info']['ip'] = onebox_ip
        body['svr_info']['uuid'] = uuid
        body['svr_info']['seq'] = svrSeq
        body['target_info'][0]['target_seq'] = targetseq

        logger.info ( "tempDeleteAndAdd Delete - Body : %s  " % str (body))

        try:
            param=mon_msg.MonInfo(body)
            rres=delTargetOnSvr(tid, tPath, e2eUrl, param, dbm)
        except Exception, e:
            logger.fatal(e)
            return rrl.rFa(tid, rrl.RS_EXCP, "Template delete error ", None, body)

        # Add Body
        # SERVER - TARGET - ADD
        # HW, OS, VIM 구분하여 처리

        if target_code == 'hw' :
            body= { "ob_service_number": "",
                "tid": tid + "-os_add",
                "svr_info": {
                    "onebox_id": "",
                    "ip": "",
                    "uuid": "",
                    "seq": "",
                    "name": ""
                },
                "target_info": [
                    {
                        "target_model": "",
                        "target_type": "",
                        "target_code": "",
                        "vendor_code": ""
                    }
                ]
            }

        elif target_code == 'os' :
            body= { "ob_service_number": "",
                "tid": tid + "-os_add",
                "svr_info": {
                    "onebox_id": "",
                    "ip": "",
                    "uuid": "",
                    "seq": "",
                    "name": ""
                },
                "target_info": [
                    {
                        "cfg": {
                            "svr_net": ["" ],
                            "svr_fs": ["/"]
                        },
                        "mapping": {
                            "wan": "eth0",
                            "office": "eth1",
                            "server": "eth2"
                        },
                        "target_code": "",
                        "target_type": "",
                        "target_model": "",
                        "vendor_code": "ubuntu"
                    }
                ]
            }
            body['target_info'][0]['cfg']= targetInfo['cfg']

        elif target_code == 'vim' :
            body= { "ob_service_number": "",
                "tid": tid + "-vim_add",
                "svr_info": {
                    "onebox_id": "",
                    "ip": "",
                    "uuid": "",
                    "seq": "",
                    "name": ""
                },
                "target_info": [
                    {
                        "cfg": {
                            "vim_net": [],
                            "vim_mgmt_net": "",
                            "vim_domain": "",
                            "vim_id": "",
                            "vim_passwd": "",
                            "vim_auth_url": "",
                            "vim_router": [  ]
                        },

                        "target_code": "",
                        "target_type": "",
                        "target_model": "",
                        "vendor_code": ""
                    }
                ]
            }
            body['target_info'][0]['cfg']= targetInfo['cfg']

        body['tid'] = body['tid']  + str(random.randrange(1000, 9999))

        body['target_info'][0]['target_model'] =target_model
        body['target_info'][0]['target_type'] =target_type
        body['target_info'][0]['target_code'] =target_code
        body['target_info'][0]['vendor_code'] =vendor_code

        body['svr_info']['onebox_id'] = onebox_id
        body['svr_info']['ip'] = onebox_ip
        body['svr_info']['uuid'] = uuid
        body['svr_info']['seq'] = svrSeq
        body['svr_info']['name'] = onebox_id

        logger.info ( "tempDeleteAndAdd - Add Body : %s  " % str (body))

        try:
            # 추가.
            param=mon_msg.MonInfo(body)
            rres = addTargetToSvr('127.0.0.1', tid, tPath, e2eUrl, param, dbm)

        except Exception, e:
            logger.fatal(e)
            return rrl.rFa(tid, rrl.RS_EXCP, "Template Add error ", None, param)

    return rrl.rSc(tid, {'tid': tid}, params, "tempDeleteAndAdd success")

def resumeMonitor(tid, tPath, e2eUrl, params, dbm):
    """
    - FUNC: 감시 항목 resume
    - INPUT
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        params(M): 감시항목 resume 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 항목 resume 결과
        rrl_handler._ReqResult
    """
    FNAME='Resume Item Status'

    re2e=None
    if tPath != None:
        re2e=e2e_logger.e2elogger('감시 재시작', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    try:
        svrSeq=str(params['svr_info']['seq'])

        if not params.has_key('type'):
            rres=rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Resume Type', None, params)
            logger.error(rres.lF(FNAME))
            if re2e != None:
                re2e.job('요청 파라미터 오류', e2e_logger.CONST_TRESULT_FAIL, '재시작 대상 정보 없음')
            return rres

        susType=params['type'].lower()
        if susType == 'vnf' or susType == 'pnf' :
            targetFor='Provisioning'
        elif susType == 'onebox':
            targetFor='All'
        else:
            rres=rrl.rFa(tid, rrl.RS_INVALID_PARAM, 'Unknown Type', None, {'type': susType})
            logger.error(rres.lF(FNAME))
            if re2e != None:
                re2e.job('요청 파라미터 오류', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
            return rres


        # 2019. 3.26 - PNF 형 한번에 resume 하기위해 - LSH
        # target_info 없으면 조회해서 만들어 넣기
        if not params.has_key('target_info') :
            getTargetSql=db_sql.GET_TARGET_BY_SVR(svrSeq)
            ret=dbm.select(getTargetSql)
            kv = {}
            kv['target_seq'] = ret
            params['target_info'] = kv['target_seq']

        rres=orchf_api.convertTargetSeqParam(dbm, svrSeq, params, targetFor)  # Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환


        # HW 변경시 삭제후 h/w 추가 방법으로 처리. - 18. 6.11 - lsh
        # 모델 에러 나면 추가 제거
        if rres.resCode() == rrl.RS_INVALID_DATA :
            result = tempDeleteAndAdd(tid, tPath, e2eUrl, params, dbm)
            if result :
                rres=orchf_api.convertTargetSeqParam(dbm, svrSeq, params, targetFor)  # Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환


        if rres.isFail():
            logger.error(rres.setErr('Convert Parameters Error').ltF(FNAME))
            if re2e != None:
                re2e.job('파라미터 변환 실패', e2e_logger.CONST_TRESULT_FAIL, rres.errStr(), None, '모니터링 시스템 파라미터로 변환')
            return rres

        params=rres.ret()

        ## Parameter에 없는 타겟 정보 보정, 2017.04.13 김승주전임 주석처리 요청.
        # if susType == 'onebox' :
        #     ret = dbm.select( db_sql.GET_TARGET_BY_SVR(svrSeq) )
        #     if ret == None :
        #         rres = rrl.rFa(tid, rrl.RS_FAIL_DB, 'Get Target Info Error', None, {'svr_seq':svrSeq})
        #         logger.error( rres.lF(FNAME) )
        #         if re2e != None:
        #             re2e.job('서버 템플릿 데이터 조회 실패', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
        #         return rres
        #
        #     tmpPmTargetList = copy.copy(params['target_info'])
        #     for dbTargetInfo in ret :
        #         isContain = False
        #         dbTargetSeq = str(dbTargetInfo['target_seq'])
        #         for pmTargetInfo in tmpPmTargetList :
        #             pmTargetSeq = str(pmTargetInfo['target_seq'])
        #             if dbTargetSeq == pmTargetSeq :
        #                 isContain = True
        #                 break
        #         if not isContain :
        #             params['target_info'].append({'target_seq':dbTargetSeq})

        ## 플러그인 설정 변경

        targetList=params['target_info']
        rres=plugin_handler.updatePlugInCfg(dbm, svrSeq, targetList, oba_port)
        if rres.isFail():
            logger.error(rres.setErr('Update PlugIn Config Error').lF(FNAME))
            if re2e != None:
                re2e.job('PlugIn 설정 정보 업데이트 오류', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
            return rres

        ## curalarm nsr, nfr, vdu 정보 변경
        for targetInfo in targetList:
            ret=dbm.execute(db_sql.UPDATE_CURR_ALARM_NFV_FOR_RESUME(svrSeq, targetInfo['target_seq']))
            if ret == None:
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update CurAlarm NFV Info Error', None,
                             {'svr_seq': svrSeq, 'target_seq': targetInfo['target_seq']})
                logger.error(rres.lF(FNAME))
                if re2e != None:
                    re2e.job('최근 장애 데이터 업데이트 오류', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
                return rres
            ret=dbm.execute(db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESUME(svrSeq, targetInfo['target_seq']))
            if ret == None:
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Update HistAlarm NFV Info Error', None,
                             {'svr_seq': svrSeq, 'target_seq': targetInfo['target_seq']})
                logger.error(rres.lF(FNAME))
                if re2e != None:
                    re2e.job('장애 이력 데이터 업데이트 오류', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
                return rres

        ## 모니터링 상태 변경
        if re2e != None:
            re2e.job('감시 항목 재시작', e2e_logger.CONST_TRESULT_NONE)

        rres=_setSuspendMonitor(tid, params, dbm, True)
        if rres.isSucc():
            if re2e != None:
                re2e.job('감시 항목 재시작', e2e_logger.CONST_TRESULT_SUCC)
        else:
            if re2e != None:
                re2e.job('감시 항목 재시작', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())

    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        if re2e != None:
            re2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, str(e))

    return rres


def suspendMonitor(tid, tPath, e2eUrl, params, dbm):
    """
    - FUNC: 감시 항목 suspend
    - INPUT
        tid(M): 요청 TID
        tPath(O): E2E 계층 구조 표시(None일 경우 E2E 호출 안함)
        e2eUrl(O): E2E URL
        params(M): 감시항목 suspend 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시 항목 suspend 결과
        rrl_handler._ReqResult
    """
    FNAME='Suspend Item Status'

    se2e=None
    if tPath != None:
        se2e=e2e_logger.e2elogger('감시 일시 정지', 'orch-M', tid, tPath, None, None, None, e2eUrl)

    try:
        svrSeq=str(params['svr_info']['seq'])

        if not params.has_key('type'):
            rres=rrl.rFa(tid, rrl.RS_NO_PARAM, 'No Suspend Type', None, params)
            logger.error(rres.lF(FNAME))
            if se2e != None:
                se2e.job('요청 파라미터 오류', e2e_logger.CONST_TRESULT_FAIL, '일시 정지 대상 정보 없음')
            return rres

        susType=params['type'].lower()
        if susType == 'vnf' or susType == 'pnf':
            rres=orchf_api.convertTargetSeqParam(dbm, svrSeq, params,
                                                 'Provisioning')  # Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
            if rres.isFail():
                logger.error(rres.setErr('Convert Parameters Error').ltF(FNAME))
                if se2e != None:
                    se2e.job('파라미터 변환 실패', e2e_logger.CONST_TRESULT_FAIL, rres.errStr(), None, '모니터링 시스템 파라미터로 변환')
                return rres
            params=rres.ret()
        elif susType == 'onebox':
            ret=dbm.select(db_sql.GET_TARGET_BY_SVR(svrSeq))
            if ret == None:
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Get Target Info Error', None, {'svr_seq': svrSeq})
                logger.error(rres.lF(FNAME))
                if se2e != None:
                    se2e.job('서버 템플릿 데이터 조회 실패', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
                return rres
            params['target_info']=ret
        else:
            rres=rrl.rFa(tid, rrl.RS_INVALID_PARAM, 'Unknown Type', None, {'type': susType})
            logger.error(rres.lF(FNAME))
            if se2e != None:
                se2e.job('요청 파라미터 오류', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
            return rres

        if se2e != None:
            se2e.job('감시 항목 일시 정지', e2e_logger.CONST_TRESULT_NONE)

        rres=_setSuspendMonitor(tid, params, dbm, False)
        if rres.isSucc():
            if se2e != None:
                se2e.job('감시 항목 일시 정지', e2e_logger.CONST_TRESULT_SUCC)
        else:
            if se2e != None:
                se2e.job('감시 항목 일시 정지', e2e_logger.CONST_TRESULT_FAIL, rres.errStr())
    except Exception, e:
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        if se2e != None:
            se2e.job('내부 exception 발생', e2e_logger.CONST_TRESULT_FAIL, str(e))

    return rres


def checkTargetSeq(tid, montargetcatseq, dbm):
    """템플릿 아이디가 올바른지 검증

    :param int montargetcatseq: tb_montargetcatalog 테이블의 시퀀스
    :param dbm: 연결된 DB 객체

    :returns: 템플릿 아이디의 존재유무. 템플릿이 존재할 경우 True, 그렇지 않을 경우 False
    """
    FNAME='Target Check'
    param={'montargetcat_seq': montargetcatseq}

    try:
        ### Target 정보
        _ret=dbm.select(db_sql.GET_TEMPLATE_SEQ(montargetcatseq))

        if (len(_ret) != 0):
            rres=rrl.rSc(tid, _ret[0], param)
        else:
            rres=rrl.rFa(tid, rrl.RS_NO_DATA, "Template Not Found", None, param)
        return rres
    except Exception, e:
        etRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, param)
        logger.error(etRes.lF(FNAME))
        logger.fatal(e)
        return etRes


def changeItemSelect(tid, reqdata, dbm):
    """통계 데이터 생성 여부 변경
    """

    # {
    # u'tid': u'item-mod-statistics-1',
    # u'svr_seq': 240,
    # u'statisticsYN': u'y',
    # u'item_seq': 32072
    # }

    moniteminstanceseq=reqdata['item_seq']
    statistics_yn=reqdata['statisticsYN']
    if statistics_yn == "y" or statistics_yn == "On":
        statistics_yn='y'
    else:
        statistics_yn='n'

    FNAME='Change Item Selecte'
    param={'moniteminstanceseq': moniteminstanceseq, 'statistics_yn': statistics_yn}

    try:
        ret=dbm.execute(db_sql.UPDATE_ITEM_SELECT(param))
        rres=rrl.rSc(tid, {'Update': ret}, {'moniteminstanceseq': moniteminstanceseq}, _msg='Update Statistics')
        logger.info(rres.lS(FNAME))
        return rres
    except Exception, e:
        etRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, param)
        logger.error(etRes.lF(FNAME))
        logger.fatal(e)
        return etRes


def test(tid, dbm):
    script='/usr/local/plugin/vim/openstack_prov/neutron_discovery.py'
    cfgName='neutron_cfg.yaml'
    cfgPath='./'
    getCfgInput=db_sql.GET_PLUGIN_CFGINPUT(script, cfgName, cfgPath)
    ret=dbm.select(getCfgInput, 'cfg_input')
    if ret != None and len(ret) > 0:

        cfgInputList=[]
        for cfgInputGroup in ret:
            if cfgInputGroup == None or cfgInputGroup == '':
                continue
            try:
                cigList=json.loads(cfgInputGroup)
                for ci in cigList:
                    if not str(ci) in cfgInputList:
                        cfgInputList.append(str(ci))
            except:
                logger.error('DB Fail: PluginConfig Input Format Error, cfg_input=%s' % str(cfgInputGroup))
                continue

        print str(cfgInputList).replace("""'""", '"')
    return rrl.rSc(tid, None, None)


def modItemObject_Delete(tid, params, dbm):
    """
    - FUNC: 감시항목 Object Delete
    - INPUT
        tid(M): 요청 TID
        params(M): 감시항목 Object 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object Delete 결과
        rrl_handler._ReqResult
    """
    FNAME='Modify Item Object Delete'

    #iObjList=None
    rbDB=dbm.getRollBackDB()

    try:

        tid =params['tid']
        svrSeq=params['svr_seq']
        ethname=params['ethname']
        lanname=params['lanname']

        # 2019. 3.12  - lsh
        # PNF 형이면 targetcode = OS 와 UTM 둘다 변경 필요
        ret=rbDB.select(db_sql.GET_SVR_IP(svrSeq))
        if ret == None:
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'modItemObject_Delete ServerSeq Error', ret, {'Server_seq': svrSeq})
            logger.error(rres.lF(FNAME))
            return rres

        isPNF = str(ret[0]['nfsubcategory']).lower() == 'ktpnf'

        targetcode_list = ['os']

        if isPNF :
            targetcode_list.append ( 'pnf' )

        for tcode in targetcode_list :

            # moniteminstseq 에 저장된 값 가져오기
            ItemSeqList=rbDB.select(db_sql.GET_ITEMINSTANCE_KEY_BY_MON_OBJECT(svrSeq, ethname, tcode))

            # 자료 없다. Error
            if ItemSeqList == None:
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Get MonItemInstance Seq Error', ret, {'Server_seq': svrSeq})
                logger.error(rres.lF(FNAME))
                return rres

            for ItemSeq  in ItemSeqList :
                iiSeq = ItemSeq["moniteminstanceseq"]
                logger.info('DELETE Start   %s  ' % params)

                ## 장애 해제 처리
                updAlarm=db_sql.UPDATE_CURR_ALARM_FOR_MOD_OBJ(iiSeq, '삭제 처리')
                rbDB.execute(updAlarm)
                rbDB.execute(db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE())

                ## Key 삭제
                delKeyInst=db_sql.REMOVE_KEY_FOR_MOD_OBJ(iiSeq)
                rbDB.execute(delKeyInst)

                ## Item 삭제
                delItemInst=db_sql.DEL_ITEMINSTANCE_FOR_MOD_OBJ(iiSeq)
                rbDB.execute(delItemInst)

                ## RealTime Perf 삭제
                delReal=db_sql.REMOVE_REALTIMEPERF_ITEM(svrSeq, iiSeq)
                rbDB.execute(delReal)

                ## MonviewInstance 삭제
                delmonview=db_sql.REMOVE_MONVIEWINSTANCE_ITEM(iiSeq)
                rbDB.execute(delmonview)

                _delRowNoUse('tb_moniteminstance', 'moniteminstanceseq', rbDB)

                logger.info("Delete DB End  %s " % str(iiSeq))


        # 설변시 OB 재부팅으로
        # 통신에러시 재시도
        for i in range(0, 9) :
            rres=plugin_handler.modPlugInMod (rbDB, svrSeq, lanname, ethname, 'D', oba_port)
            if rres.isFail():
                logger.error('modPlugInMod Retry ===> %s ' % str(i))
                sleep(10)
                continue
            else :
                rres=rrl.rSc(tid, {'tid': tid}, params)
                logger.info('COMMMMMMMMMMMMMMIT ')
                rbDB.commit()
                logger.info(rres.lS(FNAME))
                break

            # rres=plugin_handler.modPlugInDiscList(rbDB, svrSeq, icSeq, iObjList, oba_port)
            # if rres.isFail():
            #    rbDB.rollback()
            #    logger.error(rres.setErr('Modify PlugIn Config Error').ltF(FNAME))
            #    return rres

    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
    finally:
        rbDB.close()

    return rres


## svr_seq, item_cat_seq, object_list
def modItemObject_Insert(tid, params, dbm):
    """
    - FUNC: 감시항목 Object Insert
    - INPUT
        tid(M): 요청 TID
        params(M): 감시항목 Object Insert 정보
        dbm(M): DB 연결 객체
    - OUTPUT: 감시항목 Object Insert 결과
        rrl_handler._ReqResult
    """
    FNAME='Modify Item Object Insert'

    rbDB=dbm.getRollBackDB()

    logger.info('modItemObject_Insert  %s ' % params)

    try:

        tid=params['tid']
        svrSeq=params['svr_seq']
        lanname=params['lanname']
        ethname=(lambda x: x['ethname'] if x.has_key('ethname') else [])(params)
        logger.info('params = %s ' % params)

        # 2019. 3.12  - lsh
        # PNF 형이면 targetcode = OS 와 UTM 둘다 변경 필요
        ret=rbDB.select(db_sql.GET_SVR_IP(svrSeq))
        if ret == None:
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'modItemObject_Insert ServerSeq Error', ret, {'Server_seq': svrSeq})
            logger.error(rres.lF(FNAME))
            return rres

        isPNF = str(ret[0]['nfsubcategory']).lower() == 'ktpnf'

        targetcode_list = ['os']

        if isPNF :
            targetcode_list.append ( 'pnf' )

        for tcode in targetcode_list :

            ItemSeqList=rbDB.select(db_sql.GET_ITEMCATSEQ_BY_SUL(svrSeq, tcode))

            # 자료 없다. Error
            if ItemSeqList == None:
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'GET_ITEMCATSEQ_BY_SUL Error', None, params )
                logger.error(rres.lF(FNAME))
                return rres

            for ItemCatSeq in ItemSeqList :
                logger.info('ItemCatSeq = %s ' % ItemCatSeq)

                icSeq = ItemCatSeq['monitemcatseq']

                # 기존 아이템 정보 가져오기
                prevList=rbDB.select(db_sql.GET_ITEMINSTANCE_KEY_BY_MON_OBJECT_SEQ(svrSeq, ethname, icSeq))
                if len(prevList) > 0:
                    rbDB.rollback()
                    rsCode=rrl.RS_DUPLICATE_DATA
                    rres=rrl.rFa(tid, rsCode, 'Get Item Inst Error', prevList, params)
                    logger.error(rres.lF(FNAME))
                    return rres

                ## 동일 object 정보  스킵
                isPass=False
                for prevInfo in prevList:
                    if str(prevInfo['monitorobject']) == ethname:
                        prevList.remove(prevInfo)

                ## Item 설정
                addExtraItemInput=db_sql.INSERT_EXTRA_ITEMINSTANCE_FOR_MOD_OBJ(svrSeq, icSeq, ethname)
                iiSeq=rbDB.execute(addExtraItemInput, True)
                if iiSeq == None:
                    rbDB.rollback()
                    rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert Item Inst Object Error', None, params)
                    logger.error(rres.lF(FNAME))
                    return rres

                ## Item Key 설정
                addExtraKey=db_sql.INSERT_EXTRA_KEYINSTANCE_FOR_MOD_OBJ(iiSeq)
                ret=rbDB.execute(addExtraKey)
                if ret == None or ret < 1:
                    rbDB.rollback()
                    rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert Item Key Inst Error', ret, {'item_inst_seq': iiSeq})
                    logger.error(rres.lF(FNAME))
                    return rres

            # 한번에 3개 Insert 된다.
            addMonViewItem=db_sql.INSERT_VIEW_INST_LAN(svrSeq, lanname.lower(), ethname, tcode)
            ret=rbDB.execute(addMonViewItem)

            if ret == None or ret < 1:
                rbDB.rollback()
                rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert MonviewInstance Error', ret, {'ethname': ethname})
                logger.error(rres.lF(FNAME))
                return rres


        ## MonView 에 SEQ 추가
        addMonViewSEQ=db_sql.UPDATE_VIEW_INST_SEQ(svrSeq)
        ret=rbDB.execute(addMonViewSEQ)
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Insert MonviewInstance Error', ret, {'svrSeq': svrSeq})
            logger.error(rres.lF(FNAME))
            return rres

        # 2019.11.27 - lsh
        # eth 추가후 사용중인 포트 개수 증가안되는 버그 수정.
        # moniteminstance 에 realtimeyn 에 'y' 
        ret=rbDB.execute(db_sql.UPDATE_REALTIME_YN(svrSeq))
        if ret == None or ret < 1:
            rbDB.rollback()
            rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'modItemObject_Insert - UPDATE_REALTIME_YN Error ', ret, {'svrSeq': svrSeq})
            logger.error(rres.lF(FNAME))
            return rres

        # 설변시 OB 재부팅으로, 재시도
        for i in range(0, 9) :
            rres=plugin_handler.modPlugInMod (rbDB, svrSeq, lanname, ethname, 'A', oba_port)
            if rres.isFail():
                logger.error('modPlugInMod Retry ===> %s ' % str(i))
                sleep(5)
                continue
            else :
                rres=rrl.rSc(tid, {'tid': tid}, params)
                logger.info('COMMMMMMMMMMMMMMIT ')
                rbDB.commit()
                logger.info(rres.lS(FNAME))
                break

    except Exception, e:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
    finally:
        rbDB.close()

    return rres


def ob_plugin_check(reqdata, dbm):
    """
    - FUNC: OB Plugin 파일 체크
    - INPUT
        reqdata : API 에서 넘어온 값
    """
    FNAME='Onebox Plugin Check'

    try:
        # TODO : OBA 쪽  Plugin 확인.
        # TODO :  프로비저닝 후 한번더 검사차원에서 해당로직 실행
        tid=reqdata['tid']
        svrseq=reqdata['svr_info']['seq']
        ip=reqdata['svr_info']['ip']
        onebox_id=reqdata['svr_info']['onebox_id']

        logger.info("ob_plugin_check reqdata: %s" % str(reqdata))

        # resp=oba_api.plugin_check(ip, oba_port)
        # respdata=json.loads(resp)
        # logger.info("respdata : %s " % respdata)

        # if respdata == None:
        #    str=('plugin_check Error : respdata None ')
        #    logger.error(str)
        #    return str

        # 에러 : {u'result': u'FA', u'error': {u'message': u'No ZB-Key-Directory, dir=/etc/zabbix/zabbix_agentd.conf.da', u'name': u'No Data'}}
        #result=setArg(respdata, 'result')

        #if result == 'FA':
        #    str=setArg(respdata, 'error')
        #    logger.error(str)
        #    return str

        # 성공 : {u'template_list': [10, 11, 9], u'zba_key_list': [10, 9]}
        #template_list=setArg(respdata, 'template_list')
        #zba_key_list=setArg(respdata, 'zba_key_list')

        catseq_list=[]
        catseq_list=dbm.select(db_sql.GET_TARGET_CAT_SEQ(svrseq))

        # 19. 3.20 - lsh
        # FirstNotify 에서 설정파일 전송시만 Restart 하도록 bool 변수 선언.

        bRestartZBA = False

        for t in catseq_list:
            # TODO : template 전송.
            targetseq=t['catseq']
            # try:
            #     idx=template_list.index(targetseq)
            # except:

            ## 2019. 5.17 - lsh
            # 설변이 되어 .yaml 파일만 먼저 내려가서 플러그인 파일이 안내려가는 문제발생
            # 설변시 무조건 파일 내리는것으로 변경.
            logger.info("1. targetseq : %s " % targetseq)
            plugin_handler.sendPlugIn_first_notify(dbm, ip, oba_port, svrseq, targetseq)
            # bRestartZBA = True

        # Zabbix 에 설치된 template 조회.
        zcatseq_list=[]
        zcatseq_list=dbm.select(db_sql.GET_ZBCONFIG_INST_SEQ(svrseq))

        # zba_key 전송.
        for z in zcatseq_list:
            zba_key=z['catseq']
            #try:
            #    idx=zba_key_list.index(zba_key)
            #except:
            ## 2019. 5.17 - lsh
            # 설변이 되어 .yaml 파일만 먼저 내려가서 플러그인 파일이 안내려가는 문제발생
            # 설변시 무조건 파일 내리는것으로 변경.
            logger.info("2. zba_key : %s " % zba_key)
            xclient_handler.settingMonAgent_first_notify(dbm, ip, oba_port, svrseq, zba_key)

        ## 2019. 5.17 - lsh
        # 무조건 재시작
        bRestartZBA = True

        if bRestartZBA : 
            ## ZBA 감시 중지. 
            isOff = True
            ret=zbm_api.setItemMonStatus(logger, onebox_id, 'net.tcp.service[tcp,,10050]', isOff)

            rres=oba_api.restartZBA(ip, oba_port)
            if rres.isFail():
                logger.error(rres.lF('Restart ZBA'))

            ## ZBA 감시 시작
            isOff = False
            ret=zbm_api.setItemMonStatus(logger, onebox_id, 'net.tcp.service[tcp,,10050]', isOff)


        dsRes=rrl.rSc(tid, {'tid': tid}, {'svr_seq': svrseq})
        logger.info(dsRes.lS('Onebox Plugin Check'))
        sleep(3)
        return dsRes
        # logger.info(" FIRST_NOTIFY %s, %s " % (svrseq, tid))

    except Exception, e:
        isOff = False
        ret=zbm_api.setItemMonStatus(logger, onebox_id, 'net.tcp.service[tcp,,10050]', isOff)
        dsRes=rrl.rFa(tid, rrl.RS_EXCP, e, None, {'svr_seq': svrseq})
        logger.fatal(e)
        logger.error(rres.lF(FNAME))
        return dsRes
    return True

