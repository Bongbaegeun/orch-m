# -*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
import json, threading
from tornado.web import RequestHandler
from time import sleep

from util.db_mng import dbManager
from handler import mon_handler, plugin_handler, req_handler
from handler import rrl_handler as rrl
from util import db_sql
from msg import mon_msg

TITLE = 'orchm'
TITLE_API = 'apimsg'

import logging
logger = logging.getLogger(TITLE)
apiLogger = logging.getLogger(TITLE_API)

TEST = 'TEST'
FIRST_NOTIFY = 'FIRST_NOTIFY'
REQ_PROGRESS = 'REQUEST-PROGRESS'
PLUGIN_REG = 'PLUGIN-REGISTER'
PLUGIN_REM = 'PLUGIN-REMOVE'
MONITOR_SUSPEND = 'MONITOR-SUSPEND'
MONITOR_RESUME = 'MONITOR-RESUME'
TARGET_CREATE = 'TARGET-CREATE'
TARGET_REMOVE = 'TARGET-REMOVE'
TARGET_UPDATE = 'TARGET-UPDATE'
TARGET_ITEM_ADD = 'TARGET-ITEM-ADD'
TARGET_ITEM_DEL = 'TARGET-ITEM-DEL'
TARGET_ITEM_MOD_THRESHOLD = 'TARGET-ITEM-MOD-THRESHOLD'
TARGET_ITEM_MOD_NAME = 'TARGET-ITEM-MOD-NAME'
TARGET_ITEM_MOD_PERIOD = 'TARGET-ITEM-MOD-PERIOD'
TARGET_ITEM_MOD_REALTIME = 'TARGET-ITEM-MOD-REALTIME'
TARGET_ITEM_MOD_STATISTICS = 'TARGET-ITEM-MOD-STATISTICS'
TARGET_ITEM_MOD_GUIDE = 'TARGET-ITEM-MOD-GUIDE'
TARGET_MAPPING = 'TARGET-MAPPING'
TARGET_EXTRACT = 'TARGET-EXTRACT'
TARGET_CHECK_ID = 'TARGET-CHECK-ID'

SERVER_ADD = 'SERVER-ADD'
SERVER_MOD = 'SERVER-MOD'
SERVER_DEL = 'SERVER-DEL'
SERVER_TARGET_ADD = 'SERVER-TARGET-ADD'
SERVER_TARGET_DEL = 'SERVER-TARGET-DEL'
SERVER_ITEM_MOD = 'SERVER-ITEM-MODIFY'
SERVER_ITEM_MOD_NAME = 'SERVER-ITEM-MOD-NAME'
SERVER_ITEM_MOD_PERIOD = 'SERVER-ITEM-MOD-PERIOD'
SERVER_ITEM_MOD_THRESHOLD = 'SERVER-ITEM-MOD-THRESHOLD'
SERVER_ITEM_MOD_OBJECT = 'SERVER-ITEM-MOD-OBJECT'
SERVER_ITEM_SET_MON = 'SERVER-ITEM-SET-MON'
SERVER_ITEM_SET_REAL = 'SERVER-ITEM-SET-REALTIME'

STATIC_ITEM_SELECT = 'STATIC-ITEM-SELECT'

def getTPath(opCode, body):
    return (lambda x: x['tpath']+'/%s'%opCode if x.has_key('tpath') else None )(body)

def setArg( arg, argName, noneType=None ):
    return (lambda x: x[argName] if x.has_key(argName) else noneType)(arg)


class MonManager(RequestHandler):
    """
    - FUNC: 모니터링 관리 메시지 수신 API 생성 및 처리하는 클래스
    - INPUT
        opCode(M): 요청 서비스 이름
        cfg(M): Orch-M 설정 정보
    """

    def initialize(self, opCode, cfg):
        self.opCode = opCode
        self.cfg = cfg
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        self.dbm = dbManager( 'orchm', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                    cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )

    def post(self):
        reqdata = self.request.body
        self.src = self.request.remote_ip
        logger.info( rrl.lRReq(self.src, 'MonHandler', self.opCode, reqdata) )
        apiLogger.info( rrl.lRReq(self.src, 'MonHandler', self.opCode, reqdata) )

        mon_handler.globalSetting(  self.cfg['port'], self.cfg['oba_port'], self.cfg['zba_port'], self.cfg['zba_cfg_dir'], self.cfg['pnf_zba_cfg_dir'],
                                   self.cfg['basic_backup_dir'], self.cfg['remote_plugin_path'], self.cfg['pnf_remote_plugin_path'],
                                   self.cfg['gVar'] )

        res = None
        if self.opCode == TARGET_CREATE :
            res = self.targetCreate()
        elif self.opCode == TARGET_REMOVE :
            res = self.targetRemove()
        elif self.opCode == TARGET_ITEM_ADD :
            res = self.targetItemAdd()
        elif self.opCode == TARGET_ITEM_DEL :
            res = self.targetItemDel()
        elif self.opCode == TARGET_ITEM_MOD_THRESHOLD:
            res = self.targetItemModThreshold()
        elif self.opCode == TARGET_ITEM_MOD_NAME:
            res = self.targetItemModName()
        elif self.opCode == TARGET_ITEM_MOD_PERIOD:
            res = self.targetItemModPeriod()
        elif self.opCode == TARGET_ITEM_MOD_REALTIME:
            res = self.targetItemModRealtime()
        elif self.opCode == TARGET_ITEM_MOD_STATISTICS:
            res = self.targetItemModStatistics()
        elif self.opCode == TARGET_ITEM_MOD_GUIDE:
            res = self.targetItemModGuide()
        elif self.opCode == TARGET_MAPPING :
            res = self.targetMapping()
        elif self.opCode == TARGET_EXTRACT :
            res = self.targetExtract()
        elif self.opCode == TARGET_CHECK_ID :
            res = self.targetCheck()
        elif self.opCode == SERVER_ADD :
            res = self.serverAdd()                          # OneTouch 시 서버 모니터링 시작 - 서버 자체 모니터링
        elif self.opCode == SERVER_MOD :
            res = self.serverMod()
        elif self.opCode == SERVER_DEL :
            res = self.serverDel()
        elif self.opCode == SERVER_TARGET_ADD :
            res = self.serverTargetAdd()                    # 프로비저닝 시 VNF 모니터링 시작 API 처리(템플릿 추가)
        elif self.opCode == SERVER_TARGET_DEL :
            res = self.serverTargetDel()
        elif self.opCode == SERVER_ITEM_MOD :
            res = self.serverItemModify()
        elif self.opCode == SERVER_ITEM_MOD_PERIOD :
            res = self.serverItemPeriodSetting()
        elif self.opCode == SERVER_ITEM_MOD_NAME :
            res = self.serverItemModName()
        elif self.opCode == SERVER_ITEM_SET_MON :
            res = self.serverItemMonStatusSetting()
        elif self.opCode == SERVER_ITEM_SET_REAL :
            res = self.serverItemRealTimeSetting()
        elif self.opCode == STATIC_ITEM_SELECT:
            res = self.staticItemSelect()
        elif self.opCode == SERVER_ITEM_MOD_THRESHOLD :
            res = self.serverItemThresholdSetting()
        elif self.opCode == SERVER_ITEM_MOD_OBJECT :
            res = self.serverItemModObject()
        elif self.opCode == PLUGIN_REG :
            res = self.pluginReg()
        elif self.opCode == FIRST_NOTIFY:
            res=self.firstNotify()
        elif self.opCode == REQ_PROGRESS :
            res = self.requestProgress()
        elif self.opCode == MONITOR_SUSPEND :
            res = self.suspendMonitor()                     # 모니터링 일시정지 API 처리
        elif self.opCode == MONITOR_RESUME :
            res = self.resumeMonitor()                      # 모니터링 재시작 API 처리
        elif self.opCode == TEST:
            res = self.test()

        self.write(res)
        self.flush()

        # apiLogger.info( rrl.lSRes(self.src, 'MonHandler', self.opCode, res) )

    def _saveRequest(self, tid, status, state='READY'):
        """
        - FUNC: 요청 메시지 저장
        - INPUT
            tid(M): 요청 TID
            status(M): 서비스 진행 상태
            state(O): 서비스 처리 상태
        - OUTPUT : 저장 결과(True/False)
        """
        import yaml
        yamlReq = yaml.safe_load( self.request.body )
        strReq = yaml.safe_dump( yamlReq, encoding='utf-8', default_flow_style=False, allow_unicode=True )
        strReq = str(strReq).replace("""'""", '"')

        return req_handler.saveRequest( self.dbm, self.src, tid, self.opCode, strReq, status, state )

    def _saveReqFail(self, tid, error):
        """
        - FUNC: 요청 처리 실패 메시지 저장
        - INPUT
            tid(M): 요청 TID
            error(M): 실패 원인
        - OUTPUT : 저장 결과(True/False)
        """
        return req_handler.saveRequestFail( self.dbm, self.src, tid, error )

    def firstNotify(self):
        """
        - 2017.10.12 - lsh
        - FUNC : One-Box 재부팅후 처음 보내주는 Noti
        - OUTPUT :
        """
        try :
            reqdata=json.loads(self.request.body)
            rres = mon_handler.ob_plugin_check(reqdata, self.dbm)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.info(str(e))

        return rres.toOrchFRes(self)

    ## Mandatory : tid
    def requestProgress(self):
        """
        - FUNC: 요청 처리 진행 상태 확인 API 처리
        - OUTPUT : 요청 처리 진행 상태
            result: Orch-F 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = req_handler.getRequestStatus( self.dbm, self.src, tid, self.opCode )
        except (ValueError, TypeError):
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toOrchFRes(self)

    def pluginReg(self):
        """
        - FUNC: PlugIn 등록 API 처리
        - OUTPUT : PlugIn 등록 처리 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            gSeq = (lambda x : x['group_seq'] if x.has_key('group_seq') else None)(reqdata)
            rres = plugin_handler.registerPlugIn( reqdata['target_seq'], gSeq, reqdata, self.dbm )
        except (ValueError, TypeError):
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    def suspendMonitor(self):
        """
        - FUNC: 모니터링 일시정지 API 처리
        - OUTPUT : 모니터링 일시정지 처리 결과
            result: Orch-F 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            tPath = getTPath(self.opCode, reqdata)
            rres = mon_handler.suspendMonitor( tid, tPath, self.cfg['e2e_url'], reqdata, self.dbm )
            sleep(10)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toOrchFRes(self)

    def resumeMonitor(self):
        """
        - FUNC: 모니터링 재시작 API 처리
        - OUTPUT : 모니터링 재시작 처리 결과
            result: Orch-F 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            tPath = getTPath(self.opCode, reqdata)
            rres = mon_handler.resumeMonitor( tid, tPath, self.cfg['e2e_url'], reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toOrchFRes(self)

    ## Mandatory : tid, target_info[code, type, name, version, vendor_code, description]
    ## Optional : group(list)[name, description, item(list), discovery(list)]
    def targetCreate(self):
        """
        - FUNC: 감시 템플릿 생성 API 처리
        - OUTPUT : 감시 템플릿 생성 처리 결과
            result: Orch-F 용 응답
        """
        tid = None
        try:
            reqdata = json.loads(self.request.body)

            logger.info ( '========== targetCreate reqdata : %s' % reqdata)

            tid = reqdata['tid']
            __res = self._saveRequest( tid, 'RECEIVED' )
            if __res == False:
                rres = rrl.rFa(tid, rrl.RS_FAIL_OP, 'Fail to Save Request(CREATE_TARGET)', None, reqdata)
                logger.error( rres.lF(self.opCode) )
            else:
                rres = rrl.rSc(tid, {'tid':tid, 'status':'STARTING'}, None)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        if rres.isSucc():
            svrThr = threading.Thread( target=mon_handler.createTarget,
                                       args=(self.src, tid, reqdata, self.dbm) )
            svrThr.start()
        elif rres.isFail() and tid != None:
            self._saveReqFail(tid, e)

        return rres.toOrchFRes(self)

    ## Mandatory : tid, target_seq
    def targetRemove(self):
        """
        - FUNC: 감시 템플릿 제거 API 처리
        - OUTPUT : 감시 템플릿 제거 처리 결과
            result: Orch-F 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.removeTarget( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemAdd(self):
        """
        - FUNC: 감시 템플릿의 감시항목 추가 API 처리
        - OUTPUT : 감시 템플릿의 감시항목 추가 처리 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.addTargetItem( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toOrchFRes(self)

    def targetItemDel(self):
        """
        - FUNC: 감시 템플릿의 감시항목 제거 API 처리
        - OUTPUT : 감시 템플릿의 감시항목 제거 처리 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.delTargetItem( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemModThreshold(self):
        """템플릿에 속한 감시 아이템의 정보 수정 - 임계치
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modTargetItemThresheld( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemModName(self):
        """템플릿에 속한 감시 아이템의 정보 수정 - 감시명
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modTargetItemName( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemModPeriod(self):
        """템플릿에 속한 감시 아이템의 정보 수정 - 감시주기
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modTargetItemPeriod( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemModRealtime(self):
        """템플릿에 속한 감시 아이템의 정보 수정 - 실시간 감시 설정
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modTargetItemRealtime( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemModStatistics(self):
        """템플릿에 속한 감시 아이템의 정보 수정 - 통계 생성
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modTargetItemStatistics( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetItemModGuide(self):
        """템플릿에 속한 감시 아이템의 정보 수정 - 알람 가이드
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modTargetItemGuide( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def targetMapping(self):
        """
        - FUNC: Orch-F와 감시 템플릿 연동 API 처리
        - OUTPUT : Orch-F와 감시 템플릿 연동 처리 결과
            result: Orch-F 용 응답

        /target/mapping URI를 호출하여도 아무런 동작을 수행하지 않게 하기 위해서 주석 처리

        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.getTargetInfo( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
        """

        rres = rrl.rSc(None, rrl.RS_SUCC, self.request.body, None, self.request.body)

        return rres.toOrchFRes(self)

    def targetExtract(self):
        """
        - FUNC: DB에서 타겟 정보를 추출하여 json으로 변경
        - OUTPUT : 타겟 정보 추출 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            targetSeq = reqdata['target_seq']
            rres = mon_handler.extractTarget( tid, targetSeq, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    def targetCheck(self):
        """오케스트레이터가 전달한 템플릿 ID가 올바른지 DB에서 조회하여 검사

        :returns: 템플릿 검증 후 결과값 반환
        """
        tid = None
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            montargetcatseq = reqdata['montargetcat_seq']
            # vdudseq = reqdata['vdud_seq']
            rres = mon_handler.checkTargetSeq(tid, montargetcatseq, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toOrchFRes(self)

    ## Mandatory : tid, svr_info[seq, uuid, name, ip, mon_port, desc], target_info(list)
    ## Optional : svr_info[mon_port]
    def serverAdd(self):
        """
        - FUNC: OneTouch 시 서버 모니터링 시작 API 처리(서버 자체 모니터링)
        - OUTPUT : OneTouch 시 서버 모니터링 시작 처리 결과
            result: Orch-F 용 응답
        """
        tid = None
        reqdata = None
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            tPath = getTPath(self.opCode, reqdata)          # e2e log
            __res = self._saveRequest( tid, 'RECEIVED' )    # 요청 메시지 저장
            if __res == False:
                rres = rrl.rFa(tid, rrl.RS_FAIL_OP, 'Save Request(ADD_SERVER) Error', None, reqdata)        # Orch-M 내부 요청 에러 형식으로 변환
                logger.error( rres.lF(self.opCode) )
            else:
                rres = rrl.rSc(tid, {'tid':tid, 'status':'STARTING'}, reqdata)      # Orch-M 내부 요청 성공 형식으로 변환
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)       # Orch-M 내부 요청 에러 형식으로 변환
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        if rres.isSucc() :
            param = mon_msg.MonInfo(reqdata)        # 모니터링 대상 정보. 서버, 타겟(템플릿) 정보를 포함
            svrThr = threading.Thread( target=mon_handler.addServer,
                                       args=(self.src, tid, tPath, self.cfg['e2e_url'], param, self.dbm) )
            svrThr.start()      # 서버 모니터링 시작
        elif rres.isFail() and tid != None:
            self._saveReqFail(tid, e)       # 요청 처리 실패 메시지 저장

        # Orch-F 형식으로 결과 변환
        return rres.toOrchFRes(self)

    def serverMod(self):
        """
        - FUNC: 서버 주소 변경(IP)
        - OUTPUT : 서버 주소 변경 결과
            result: Orch-F 용 응답
        """
        FNAME='Modify Server'

        try:
            reqdata = json.loads(self.request.body)

            logger.info('serverMod : %s' % str ( reqdata ) )

            tid = reqdata['tid']
            tPath=getTPath(self.opCode, reqdata)

            rbDB=self.dbm.getRollBackDB()

            # 기존 서버 IP 변경
            svrinfo = setArg(reqdata, 'svr_info')

            # 20. 2.13 - lsh
            # Port 변경 시나리오 추가.
            # 기존 Port 값 없을때, 강제로 Default 지정.
            if not setArg ( svrinfo, 'new_port') :
                svrinfo["new_port"] = "10050" 

            if svrinfo <> None :
                if svrinfo["seq"] <> "" and svrinfo["new_ip"] <> "" :
                    param_svrinfo = mon_msg.SvrModInfo( svrinfo )
                    rres = mon_handler.modServer( tid, tPath, self.cfg['e2e_url'], param_svrinfo, self.dbm )

            change_info = setArg(reqdata, 'change_info')

            # TODO - 설변기능
            if change_info <> None :
                for info in change_info :
                    bADD = info['before_eth'] == "" and info["before_lan"] == "" and info['after_eth'] <> "" and info["after_lan"] <> ""
                    bDELETE = info['before_eth'] <> "" and info["before_lan"] <> "" and info['after_eth'] == "" and info["after_lan"] == ""

                    # 모두 값이 있으면, 지우고, 다시 생성.
                    if info['before_eth'] <> "" and info["before_lan"] <> "" and info['after_eth'] <> "" and info["after_lan"] <> "" :
                        bADD = True
                        bDELETE= True

                    logger.info(rrl.lI2('change_info  = %s' % info))

                    svrseq = info['svrseq']
                    
                    add_del_dbm = self.dbm                    
                    
                    ## 삭제
                    if bDELETE :
                        delete_data = {"tid" : tid, "svr_seq" : svrseq, "lanname":info["before_lan"], "ethname":info['before_eth']  }
                        logger.info(rrl.lI2('DELETE  !!!!! delete_data  = %s' % delete_data))

                        # DB 제거.
                        rres = mon_handler.modItemObject_Delete(tid, delete_data, add_del_dbm)
                        if rres.isFail():
                            rbDB.rollback()
                            return rres


                    if bADD :
                        # eth0 ~ eth 7 추가.
                        logger.info('ADDDDDDDDDDDDD ')
                        add_data={"tid": tid, "svr_seq": svrseq, "ethname": info["after_eth"], "lanname": info["after_lan"]}
                        logger.info(rrl.lI2('ADD  !!!!! add_data  = %s' % add_data))

                        # DB 추가.
                        rres=mon_handler.modItemObject_Insert(tid, add_data, add_del_dbm)
                        if rres.isFail():
                            rbDB.rollback()
                            return rres

            # rres=mon_handler.modServersul(tid, tPath, self.cfg['e2e_url'], param, self.dbm)
            # rres = rrl.rSc(tid, {'tid': tid, "result":True}, reqdata)

        except Exception, e:
            rbDB.rollback()
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, None)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            return rres

        logger.info('ENDDDDDDDDDDDDDDDDD')
        # rres = rrl.rSc(tid, {'tid': tid}, {'svr_seq': svrseq})
        return rres.toOrchFRes(self)

    ## Mandatory : tid, svr_info[seq, uuid, ip]
    def serverDel(self):
        """
        - FUNC: 서버 모니터링 제거 API 처리
        - OUTPUT : 서버 모니터링 제거 처리 결과
            result: Orch-F 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            tPath = getTPath(self.opCode, reqdata)
            param = mon_msg.SvrInfo( reqdata['svr_info'] )
            rres = mon_handler.delServer( tid, tPath, self.cfg['e2e_url'], param, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toOrchFRes(self)

    ## Mandatory : tid, svr_info[seq, uuid, ip], target_info(list)
    def serverTargetAdd(self):
        """
        - FUNC: 프로비저닝 시 VNF 모니터링 시작 API 처리(템플릿 추가)
        - OUTPUT : 프로비저닝 시 VNF 모니터링 시작 결과
            result: Orch-F 용 응답
        """
        tid = None
        reqdata = None
        try:
            reqdata = json.loads(self.request.body)
            logger.info (' ============== serverTargetAdd reqdate : %s ' % reqdata)

            tid = reqdata['tid']
            tPath = getTPath(self.opCode, reqdata)              # 모니터링 관리 메시지 수신 API 생성 및 처리하는 클래스
            __res = self._saveRequest( tid, 'RECEIVED' )        # 요청 메시지 저장
            if __res == False:
                rres = rrl.rFa(tid, rrl.RS_FAIL_OP, 'Fail to Save Request(ADD_TARGET)', None, reqdata)      # Orch-M 내부 요청 에러 형식으로 변환
                logger.error( rres.lF(self.opCode) )
            else:
                rres = rrl.rSc(tid, {'tid':tid, 'status':'STARTING'}, None)     # Orch-M 내부 요청 성공 형식으로 변환
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)       # Orch-M 내부 요청 에러 형식으로 변환
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        if rres.isSucc():
            param = mon_msg.MonInfo(reqdata)
            svrThr = threading.Thread( target=mon_handler.addTargetToSvr,
                                       args=(self.src, tid, tPath, self.cfg['e2e_url'], param, self.dbm) )
            svrThr.start()
        elif rres.isFail() and tid != None:
            self._saveReqFail(tid, e)

        return rres.toOrchFRes(self)

    ## Mandatory : tid, svr_info[seq, uuid, ip], target_info[target_seq(list)]
    def serverTargetDel(self):
        """
        - FUNC: 프로비저닝 시 VNF 모니터링 제거 API 처리(템플릿 제거)
        - OUTPUT : 프로비저닝 시 VNF 모니터링 제거 결과
            result: Orch-F 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            tPath = getTPath(self.opCode, reqdata)
            param = mon_msg.MonInfo( reqdata )
            rres = mon_handler.delTargetOnSvr( tid, tPath, self.cfg['e2e_url'], param, self.dbm)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toOrchFRes(self)

    ## Mandatory : tid, svr_seq, item_seq
    ## Optional : new_period, new_history, new_statistic
    def serverItemPeriodSetting(self):
        """
        - FUNC: 감시 아이템 주기 관련 항목 수정 API 처리
        - OUTPUT : 감시 아이템 주기 관련 항목 수정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.setItemPeriod( tid, reqdata, self.dbm)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    def serverItemModName(self):
        """
        - FUNC: 감시 아이템 이름 수정 API 처리
        - OUTPUT : 감시 아이템 이름 수정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.setItemName( tid, reqdata, self.dbm)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    ## Mandatory : tid, svr_seq, item_seq, monitor_yn
    def serverItemMonStatusSetting(self):
        """
        - FUNC: 감시 아이템 감시 On/Off 설정 API 처리
        - OUTPUT : 감시 아이템 감시 On/Off 설정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.setItemMonStatus( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    ## Mandatory : tid, svr_seq, item_seq, realtime_yn
    def serverItemRealTimeSetting(self):
        """
        - FUNC: 감시 아이템 실시간 감시 On/Off 설정 API 처리
        - OUTPUT : 감시 아이템 실시간 감시 On/Off 설정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.setRealItemItem( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    def staticItemSelect(self):
        """통계 데이터 생성을 위해 감시항목 선택 또는 선택해제

        tid: 트랜잭션 아이디
        moniteminstanceseq: 감시항목 시퀀스
        statistics_yn: 통계 데이터 생성 여부
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.changeItemSelect( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    ## Mandatory: tid, svr_seq, item_seq, op_code, threshold_list
    def serverItemThresholdSetting(self):
        """
        - FUNC: 감시 아이템 임계치 설정 API 처리
        - OUTPUT : 감시 아이템 임계치 설정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.setOBThreshold( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, self.request.body)
            logger.error(rres.lF(self.opCode))
            logger.fatal(e)

        return rres.toWebRes()

    def serverItemModObject(self):
        """
        - FUNC: 감시 아이템 Object(Discovery 항목) 수정 API 처리
        - OUTPUT : 감시 아이템 Object(Discovery 항목) 수정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.modItemObject( tid, reqdata, self.dbm )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    def serverItemModify(self):
        """
        - FUNC: 감시 아이템 전체 수정 API 처리
        - OUTPUT : 감시 아이템 전체 수정 결과
            result: WEB 용 응답
        """
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']

            errState = "PERIOD_SETTING_ERROR"
            rres = mon_handler.setItemPeriod( tid, reqdata, self.dbm)
            if rres.isSucc():
                errState = "THRESHOLD_SETTING_ERROR"
                rres = mon_handler.setOBThreshold( tid, reqdata, self.dbm)
                if rres.isSucc():
                    errState = "REALTIME_SETTING_ERROR"
                    rres = mon_handler.setRealItemItem( tid, reqdata, self.dbm)
                    if rres.isFail():
                        errState = "ON_OFF_SETTING_ERROR"
                        rres = mon_handler.setItemMonStatus( tid, reqdata, self.dbm)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, errState + ' Exception', None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

    def test(self):
        try:
            reqdata = json.loads(self.request.body)
            tid = reqdata['tid']
            rres = mon_handler.test(tid, self.dbm)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)

        return rres.toWebRes()

class zbStatusChecker(threading.Thread):
    """
    - FUNC: Zabbix 연결 상태 확인
    - INPUT
        cfg(M): Orch-M 설정 정보
    """

    def __init__( self, cfg ):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.mPort = (lambda x: int(x['port']) if x.has_key('port') else 5555 )(cfg)
        self.zbIP = cfg['zb_ip']
        self.zbPort = (lambda x: int(x['zb_port']) if x.has_key('zb_port') else 10051 )(cfg)
        self.zbProcName = (lambda x: x['zb_proc_name'] if x.has_key('zb_proc_name') else 'zabbix-server' )(cfg)
        self.period = (lambda x: int(x['zb_chk_period']) if x.has_key('zb_chk_period') else 30 )(cfg)

    def run(self):
        from util import rest_api
        from datetime import datetime
        import socket

        FNAME = 'ZBS Status Check'

        isFault = True
        HEADER={"content-type":"application/json-rpc"}
        URL = '%s://%s:%s/fault'%(str(self.cfg['zb_chk_protocal']), self.cfg['zb_chk_host'], self.mPort)
        BODY = {"body":
                    {
                        "host":{"name": '', "ip": self.zbIP},
                        "item":[{"key":"", "value":""}],
                        "trigger":{"name":"", "status_code":"", "grade_code":""},
                        "event":{"date": "", "time": ""}
                    }
                }

        sleep(10)
        while True:
            try:
                sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.zbIP, self.zbPort))
                sock.close()

                dbm = dbManager( 'zbchk', self.cfg['db_name'], self.cfg['db_user'], self.cfg['db_passwd'],
                            self.cfg['db_addr'], int(self.cfg['db_port']), connCnt=1, _logger=logger )
                ret = dbm.select( db_sql.GET_ITEM_INST_FOR_ZBCHK(self.zbIP, self.zbProcName) )
                if ret != None and len(ret) > 0 :

                    body = BODY['body']
                    body["host"]["name"] = ret[0]['onebox_id']
                    body["item"][0]["key"] = ret[0]['key']
                    body["trigger"]["name"] = ret[0]['t_name']

                    isSucc = True
                    if result != 0 :
                        isSucc = False

                    ## 성공 시
                    dbm.execute( db_sql.UPDATE_REALTIMEPERF_FOR_ZBCHK(ret[0]['itemseq'], int(isSucc)) )
                    if isFault and isSucc :
                        isFault = False
                        body["item"][0]["value"] = "1"
                        body["trigger"]["status_code"] = "0"
                        body["trigger"]["grade_code"] = "5"
                        body["event"]["date"] = datetime.now().strftime("%Y.%m.%d")
                        body["event"]["time"] = datetime.now().strftime("%H:%M:%S")
                        rest_api.sendReq(HEADER, URL, 'POST', BODY, 10)

                    ## 실패 시
                    elif not isFault and not isSucc :
                        isFault = True
                        body["item"][0]["value"] = "0"
                        body["trigger"]["status_code"] = "1"
                        body["trigger"]["grade_code"] = "5"
                        body["event"]["date"] = datetime.now().strftime("%Y.%m.%d")
                        body["event"]["time"] = datetime.now().strftime("%H:%M:%S")
                        rest_api.sendReq(HEADER, URL, 'POST', BODY, 10)

                else:
                    rres = rrl.rFa(None, rrl.RS_NO_DATA, 'No ZB Server Info', ret, {'zb_ip':self.zbIP, 'zb_name':self.zbProcName})
                    logger.warning( rres.lF( FNAME ) )

            except Exception, e:

                logger.info ( "%s,  %s,  %s " % (HEADER, URL, BODY) )
                rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'zb_ip':self.zbIP, 'zb_name':self.zbProcName})
                logger.error( rres.lF(FNAME) )
                logger.fatal(e)

            sleep(self.period)

def url( _cfg ):
    """
    - FUNC: MonManager의 URL 및 API Handler, 인자 관리
    - INPUT
        _cfg(M): Orch-M 설정 정보
    - OUTPUT : API에 대한 URL, Handler, 인자 리스트
    """
    url = [
            ('/test', MonManager, dict(opCode=TEST, cfg=_cfg)),                                             # 테스트를 위해 만든 코드. 현재는 불필요하다.
            ('/oba/first_notify', MonManager, dict(opCode=FIRST_NOTIFY, cfg=_cfg)),                         # OB 재시작후 Notify

            ('/request/progress', MonManager, dict(opCode=REQ_PROGRESS, cfg=_cfg)),                         # 요청 처리 진행 상태 확인 API
            ('/target/extract', MonManager, dict(opCode=TARGET_EXTRACT, cfg=_cfg)),                         # DB에서 테겟 정보를 추출하여 json으로 변경

            ('/plugin', MonManager, dict(opCode=PLUGIN_REG, cfg=_cfg)),                                     # 플러그인 등록
            ('/plugin/remove', MonManager, dict(opCode=PLUGIN_REM, cfg=_cfg)),                              # 플러그인 제거

            ('/monitor/suspend', MonManager, dict(opCode=MONITOR_SUSPEND, cfg=_cfg)),                       # 모니터링 중지
            ('/monitor/resume', MonManager, dict(opCode=MONITOR_RESUME, cfg=_cfg)),                         # 모니터링 재개

            ('/target', MonManager, dict(opCode=TARGET_CREATE, cfg=_cfg)),                                  # 감시 템플릿 생성
            ('/target/remove', MonManager, dict(opCode=TARGET_REMOVE, cfg=_cfg)),                           # 감시 템플릿 제거
            ('/target/item/add', MonManager, dict(opCode=TARGET_ITEM_ADD, cfg=_cfg)),                       # 감시 템플릿의 감시 항목 추가
            ('/target/item/del', MonManager, dict(opCode=TARGET_ITEM_DEL, cfg=_cfg)),                       # 감시 템플릿의 감시항목 제거
            ('/target/item/mod/threshold', MonManager, dict(opCode=TARGET_ITEM_MOD_THRESHOLD, cfg=_cfg)),   # 감시 템플릿의 감시항목 수정 - 임계치
            ('/target/item/mod/name', MonManager, dict(opCode=TARGET_ITEM_MOD_NAME, cfg=_cfg)),             # 감시 템플릿의 감시항목 수정 - 감시명
            ('/target/item/mod/period', MonManager, dict(opCode=TARGET_ITEM_MOD_PERIOD, cfg=_cfg)),         # 감시 템플릿의 감시항목 수정 - 감시주기
            ('/target/item/mod/realtime', MonManager, dict(opCode=TARGET_ITEM_MOD_REALTIME, cfg=_cfg)),     # 감시 템플릿의 감시항목 수정 - 실시간 감지
            ('/target/item/mod/statistics', MonManager, dict(opCode=TARGET_ITEM_MOD_STATISTICS, cfg=_cfg)), # 감시 템플릿의 감시항목 수정 - 통계 생성
            ('/target/item/mod/guide', MonManager, dict(opCode=TARGET_ITEM_MOD_GUIDE, cfg=_cfg)),           # 감시 템플릿의 감시항목 수정 - 장애 알람 가이드
            ('/target/checkid', MonManager, dict(opCode=TARGET_CHECK_ID, cfg=_cfg)),                        # 오케스트레이터-F 에서 검증을 위해서 전달한 템플릿 아이디 검사

            ('/server', MonManager, dict(opCode=SERVER_ADD, cfg=_cfg)),                                     # OneTouch 시 서버 모니터링 시작 - 서버 자체 모니터링
            ('/server/mod', MonManager, dict(opCode=SERVER_MOD, cfg=_cfg)),                                 # 서버 변경 - IP 주소만 변경
            ('/server/del', MonManager, dict(opCode=SERVER_DEL, cfg=_cfg)),                                 # 서버 모니터링 제거

            ('/server/target/add', MonManager, dict(opCode=SERVER_TARGET_ADD, cfg=_cfg)),                   # 프로비저닝 시 VNF 모니터링 시작 - 템플릿 추가
            ('/server/target/del', MonManager, dict(opCode=SERVER_TARGET_DEL, cfg=_cfg)),                   # 프로비저닝 시 VNF 모니터일 제거 - 템플릿 제거

            ('/server/item/mod', MonManager, dict(opCode=SERVER_ITEM_MOD, cfg=_cfg)),                       # 감시 아이템 전체 수정
            ('/server/item/mod/period', MonManager, dict(opCode=SERVER_ITEM_MOD_PERIOD, cfg=_cfg)),         # 감시 아이템 주기 관련 항목 수정
            ('/server/item/mod/monstatus', MonManager, dict(opCode=SERVER_ITEM_SET_MON, cfg=_cfg)),         # 감시 아이템 On/Off 설정
            ('/server/item/mod/realtime', MonManager, dict(opCode=SERVER_ITEM_SET_REAL, cfg=_cfg)),         # 감시 아이템 실시간 감시 On/Off 설정
            ('/server/item/mod/threshold', MonManager, dict(opCode=SERVER_ITEM_MOD_THRESHOLD, cfg=_cfg)),   # 감시 아이템 임계치 설정
            ('/server/item/mod/object', MonManager, dict(opCode=SERVER_ITEM_MOD_OBJECT, cfg=_cfg)),         # 감시 아이템 Object(Discovery 항목) 수정
            ('/server/item/mod/name', MonManager, dict(opCode=SERVER_ITEM_MOD_NAME, cfg=_cfg)),             # 감시 아이템 이름 수정

            ('/server/item/mod/select', MonManager, dict(opCode=STATIC_ITEM_SELECT, cfg=_cfg)),             # 통계 데이터 생성을 위한 감시항목 선택 또는 선택해제

            # 기존에 프로비저닝시 사용하는 api. 현재는 사용하지 않으며 호출시 아무런 동작도 하지 않는다.
            # 2016-11-17. 추후에 확인이 되면 코드 삭제할 예정
            ('/target/mapping', MonManager, dict(opCode=TARGET_MAPPING, cfg=_cfg)),
        ]
    return url

def onStart(cfg):
    """
    - FUNC: MonManager 시작 시 실행해야할 기능 구현
    - INPUT
        cfg(M): Orch-M 설정 정보
    """
    mon_handler.globalSetting( cfg['port'], cfg['oba_port'], cfg['zba_port'], cfg['zba_cfg_dir'], cfg['pnf_zba_cfg_dir'],
                               cfg['basic_backup_dir'], cfg['remote_plugin_path'], cfg['pnf_remote_plugin_path'],
                               cfg['gVar'] )

    # 2017. 11. 29 - lsh
    # 김승주 전임 요청으로 시작시 장비상태 체크 로직 제거.
    # try:
    #     connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
    #     dbm = dbManager( 'orchm-monitor', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
    #                     cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )
    #
    #     ret = dbm.select( db_sql.GET_SERVER_LIST() )
    #     if ret == None :
    #         logger.error( 'DB Fail to Get Server OBID' )
    #
    #     for svrInfo in ret:
    #         connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
    #         _dbm = dbManager( 'orchm-monitor', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
    #                         cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )
    #
    #         # iChk = mon_handler.ItemChecker(svrInfo['svr_seq'], svrInfo['onebox_id'], _dbm, None, True)
    #         # iChk.start()
    #         rres = rrl.rSc(None, None, {'onebox_id':svrInfo['onebox_id']})
    #         logger.info( rres.lS('OnStart ItemStatus Checker') )
    # except Exception, e:
    #     rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
    #     logger.error(rres.lF('OnStart ItemStatus Checker'))
    #     logger.fatal(e)

    return




