#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
import json, threading, MySQLdb
from time import sleep
from tornado.web import RequestHandler

import api.zbm_api as zb
from util.db_mng import dbManager
from util import db_sql, sms_mng
from api import web_api
from handler import rrl_handler as rrl

import time
from datetime import datetime, timedelta

import util.str_api as sa
import urllib2
import redis
import socket, copy


TITLE = 'orchm'
TITLE_FAULT = 'faultmsg'
TITLE_API = 'apimsg'

import logging
logger = logging.getLogger(TITLE)
apiLogger = logging.getLogger(TITLE_API)
#fLogger = logging.getLogger(TITLE_FAULT)

# 개발시 로그표시 유무.
DEBUG_LOG_YN = 'n'

# 20. 5.12 - lsh
# 운영팀 요청,  SMS 중복건수 표시 가능 ? 
# redis 를 이용하여 최근 24시간 중복 카운터.
redis = redis.Redis(host='localhost', port=6379, db=1)


# 17.11.29 - LSH
# 운영팀 요청, 고객명은 절삭 금지.
# TargetName 길이 조절로 변경
# 18. 4.18 - LSH
# 뒤에서 부터 절삭
def make_short_msg ( msg ) :

    done_msg = ""
    str_len = len(unicode(msg))+1

    for i in range(0, str_len):

        stmp = unicode(msg)[:str_len-i]

        # logger.info ( "vName : %s " % vName )
        # stmp= msg.replace('SUB_MESSAGE', vName)

        # stmp = stmp + short_sub_msg
        # stmp=stmp.replace(' 상태', '')
        # stmp=stmp.replace (", 지속시간 ", ",")

        if done_msg == "" :
            done_msg=stmp

        shortlen=len(stmp.decode('utf-8').encode('euc-kr'))


        if shortlen <= 80:
            done_msg = stmp
            break

    #logger.info("stmp : %s " % stmp)
    #logger.info("len: %s " % str(shortlen))

    return done_msg


def _toSmsMsg( orgCode, serverName, targetName, targetVersion, monitorItem,
               monitorObject, unit, itemVal, alertGrade, dttm,
               trig_name, visibleName, valueTypeName, group_name, customerName ):
    """
    - FUNC: 장애 발생 정보를 SMS 메시지로 변환(SMS 80 Byte 고려)
    - INPUT
        orgCode(M): 국사 코드
        serverName(M): 서버 이름
        targetName(M): 감시대상 이름
        targetVersion(O): 감시대상 버전
        monitorItem(M): 감시항목 이름
        monitorObject(O): 감시항목 Object
        unit(O): 감시항목 측정값의 단위
        itemVal(M): 감시항목 측정값
        alertGrade(M): 장애 등급 코드
        dttm(O): 장애 발생 시간
        trig_name(M): 장애 요약 설명(zabbix Trigger Name)
    - OUTPUT : SMS 장애 발생 메시지
    """

    msg = ''
    # short_msg = ''
    sub_msg = ''

    # msg += ( '[%s] %s %s서버, %s %s, 측정값:%s'%(getGrade(alertGrade), orgCode, serverName, targetName, monitorItem, itemVal) )
    # 2017.11. 7 - lsh, 상용 인수 시험 요청안.
    # UTM Daemon 상태의 vpn SMS 표시,
    # Daemon 하위 값 모두 표시토록 변경
    if visibleName.find ("UTM Daemon") > -1 :
        visibleName = visibleName.replace ('UTM Daemon', 'Daemon-%s') % monitorObject

    msg += ('[%s/%s]%s %s,%s,%s' % (sa.getState_short(1), sa.getGrade_short(alertGrade), unicode(group_name)[:2], customerName, orgCode,visibleName))
    # short_msg += ('[%s/%s]%s %s,%s,SUB_MESSAGE' % (sa.getState_short(1), sa.getGrade_short(alertGrade), unicode(group_name)[:2], customerName, unicode(targetName)[:3]))

#     msg += (trig_name)
#     msg +=  ( '지역:%s, '%orgCode )
#     msg += ( '발생시간:%s'%str(dttm) )
#     msg += ( '서버:%s, '%serverName )
#     msg += ( '\n' )
#     msg += ( '대상:%s[%s], '%(targetName, targetVersion ) )
#     msg += ( '항목:%s'%monitorItem )
#     msg += ( lambda x : '[%s]'%x if x is not None and x != '' else ', ' )( monitorObject )
#     msg += ( '장애등급:%s, '%alertGrade )
#     msg += ( '측정값:%s'%str(itemVal) )

    if valueTypeName == '상태':
        if itemVal is not None:
            if float(itemVal) > 0:
                sub_msg += (' %s' % 'UP')
            else:
                sub_msg += (' %s' % 'DOWN')
    else:
        if unit == "bps":
            unit = 'Mbps'
            if itemVal is not None:
                if float(itemVal) > 0:
                    itemVal = round(float(itemVal) / 1000000, 1)  # 단위는 1000,000 으로 나눔, Mbps표시.
            else:
                itemVal = ''

        sub_msg += (' %s' % itemVal)
        sub_msg += (lambda x: '%s' % x if x is not None and x != '' else '')(unit)

    msg+=sub_msg

    strlen=len(msg.decode('utf-8').encode('euc-kr'))

    # 80 Byte 보다 크면, 짧은 SMS 전송.
    if strlen > 80:
        msg=make_short_msg(msg)

    return msg


def _toSmsMsg_Aruba( orgCode, serverName, targetName, targetVersion, monitorItem,
               monitorObject, unit, itemVal, alertGrade, dttm,
               trig_name, visibleName, valueTypeName, group_name, customerName ):
    """
    - FUNC: 장애 발생 정보를 SMS 메시지로 변환(SMS 80 Byte 고려)
    - INPUT
        orgCode(M): 국사 코드
        serverName(M): 서버 이름
        targetName(M): 감시대상 이름
        targetVersion(O): 감시대상 버전
        monitorItem(M): 감시항목 이름
        monitorObject(O): 감시항목 Object
        unit(O): 감시항목 측정값의 단위
        itemVal(M): 감시항목 측정값
        alertGrade(M): 장애 등급 코드
        dttm(O): 장애 발생 시간
        trig_name(M): 장애 요약 설명(zabbix Trigger Name)
    - OUTPUT : SMS 장애 발생 메시지
    """

    msg = ''
    # short_msg = ''
    sub_msg = ''

    # msg += ( '[%s] %s %s서버, %s %s, 측정값:%s'%(getGrade(alertGrade), orgCode, serverName, targetName, monitorItem, itemVal) )
    # 2017.11. 7 - lsh, 상용 인수 시험 요청안.
    # UTM Daemon 상태의 vpn SMS 표시,
    # Daemon 하위 값 모두 표시토록 변경
    if visibleName.find ("UTM Daemon") > -1 :
        visibleName = visibleName.replace ('UTM Daemon', 'Daemon-%s') % monitorObject

    # msg += ('[%s/%s]%s %s,%s' % (sa.getState_short(1), sa.getGrade_short(alertGrade), group_name, orgCode, customerName))
    msg += ('[%s/%s]%s %s,%s' % (sa.getState_short(1), 'C', group_name, orgCode, customerName))
    # short_msg += ('[%s/%s]%s %s,%s,SUB_MESSAGE' % (sa.getState_short(1), sa.getGrade_short(alertGrade), unicode(group_name)[:2], customerName, unicode(targetName)[:3]))

#     msg += (trig_name)
#     msg +=  ( '지역:%s, '%orgCode )
#     msg += ( '발생시간:%s'%str(dttm) )
#     msg += ( '서버:%s, '%serverName )
#     msg += ( '\n' )
#     msg += ( '대상:%s[%s], '%(targetName, targetVersion ) )
#     msg += ( '항목:%s'%monitorItem )
#     msg += ( lambda x : '[%s]'%x if x is not None and x != '' else ', ' )( monitorObject )
#     msg += ( '장애등급:%s, '%alertGrade )
#     msg += ( '측정값:%s'%str(itemVal) )

    if valueTypeName == '상태':
        if itemVal is not None:
            if float(itemVal) > 0:
                sub_msg += (' %s' % 'UP')
            else:
                sub_msg += (' %s' % 'DOWN')
    else:
        if unit == "bps":
            unit = 'Mbps'
            if itemVal is not None:
                if float(itemVal) > 0:
                    itemVal = round(float(itemVal) / 1000000, 1)  # 단위는 1000,000 으로 나눔, Mbps표시.
            else:
                itemVal = ''

        sub_msg += (' %s' % itemVal)
        sub_msg += (lambda x: '%s' % x if x is not None and x != '' else '')(unit)

    # msg+=sub_msg

    strlen=len(msg.decode('utf-8').encode('euc-kr'))

    # 80 Byte 보다 크면, 짧은 SMS 전송.
    if strlen > 80:
        msg=make_short_msg(msg)

    return msg


def _getResolveMsg(orgCode, serverName, targetName, monitorItem, monitorObject, resolveDesc,
                   alertGrade, visibleName, valueTypeName, group_name, customerName, resolve_mon_gap,
                   unit, itemVal):
    """
    - FUNC: 장애 해제 정보를 SMS 메시지로 변환(SMS 80 Byte 고려)
    - INPUT
        orgCode(M): 국사 코드
        serverName(M): 서버 이름
        targetName(M): 감시대상 이름
        monitorItem(M): 감시항목 이름
        resolveDesc(M): 장애 헤제 시간
    - OUTPUT : SMS 장애 해제 메시지
    """

    msg = ''
    # short_msg = ''
    sub_msg = ''

    # msg += ( '[장애해제] %s %s서버, %s %s, %s'%(orgCode, serverName, targetName, monitorItem, resolveDesc) )
    # 2017.11. 7 - lsh, 상용 인수 시험 요청안.
    # UTM Daemon 상태의 vpn SMS 표시,
    # Daemon 하위 값 모두 표시토록 변경

    if visibleName.find ("UTM Daemon") > -1 :
        visibleName = visibleName.replace ('UTM Daemon', 'Daemon-%s') % monitorObject

    msg += ('[%s/%s]%s %s,%s,%s' % (sa.getState_short(0), sa.getGrade_short(alertGrade), unicode(group_name)[:2], customerName, orgCode, visibleName))
    # short_msg += ('[%s/%s]%s %s,%s,SUB_MESSAGE' % (sa.getState_short(0), sa.getGrade_short(alertGrade), unicode(group_name)[:2], customerName, unicode(targetName)[:3]))

    if valueTypeName == '상태':
        if itemVal is not None:
            if float(itemVal) > 0:
                sub_msg += (' %s' % 'UP')
            else:
                sub_msg += (' %s' % 'DOWN')
    else:
        if unit == "bps":
            unit = 'Mbps'
            if itemVal is not None:
                if float(itemVal) > 0: 
                    itemVal = round(float(itemVal) / 1000000, 1)  # 단위는 1000,000 으로 나눔, Mbps표시.
            else:
                itemVal = ''

        sub_msg += (' %s' % itemVal)
        sub_msg += (lambda x: '%s' % x if x is not None and x != '' else '')(unit)


    if resolve_mon_gap != '':
        sub_msg += ('%s' % ', 지속시간 ' + resolve_mon_gap)

    msg+=sub_msg
    strlen=len(msg.decode('utf-8').encode('euc-kr'))

    # 고객명을 가변적으로
    # 80 Byte 보다 크면, 짧은 SMS 전송.
    if strlen > 80:
        msg=make_short_msg(msg)

    return msg


def _getResolveMsg_Aruba(orgCode, serverName, targetName, monitorItem, monitorObject, resolveDesc,
                   alertGrade, visibleName, valueTypeName, group_name, customerName, resolve_mon_gap,
                   unit, itemVal):
    """
    - FUNC: 장애 해제 정보를 SMS 메시지로 변환(SMS 80 Byte 고려)
    - INPUT
        orgCode(M): 국사 코드
        serverName(M): 서버 이름
        targetName(M): 감시대상 이름
        monitorItem(M): 감시항목 이름
        resolveDesc(M): 장애 헤제 시간
    - OUTPUT : SMS 장애 해제 메시지
    """

    msg = ''
    # short_msg = ''
    sub_msg = ''

    # msg += ( '[장애해제] %s %s서버, %s %s, %s'%(orgCode, serverName, targetName, monitorItem, resolveDesc) )
    # 2017.11. 7 - lsh, 상용 인수 시험 요청안.
    # UTM Daemon 상태의 vpn SMS 표시,
    # Daemon 하위 값 모두 표시토록 변경

    if visibleName.find ("UTM Daemon") > -1 :
        visibleName = visibleName.replace ('UTM Daemon', 'Daemon-%s') % monitorObject

    # msg += ('[%s/%s]%s %s,%s' % (sa.getState_short(0), sa.getGrade_short(alertGrade), group_name, orgCode, customerName))
    msg += ('[%s/%s]%s %s,%s' % (sa.getState_short(0), 'C', group_name, orgCode, customerName))
    # short_msg += ('[%s/%s]%s %s,%s,SUB_MESSAGE' % (sa.getState_short(0), sa.getGrade_short(alertGrade), unicode(group_name)[:2], customerName, unicode(targetName)[:3]))

    # if valueTypeName == '상태':
    #     if itemVal is not None:
    #         if float(itemVal) > 0:
    #             sub_msg += (' %s' % 'UP')
    #         else:
    #             sub_msg += (' %s' % 'DOWN')
    # else:
    #     if unit == "bps":
    #         unit = 'Mbps'
    #         if itemVal is not None:
    #             if float(itemVal) > 0:
    #                 itemVal = round(float(itemVal) / 1000000, 1)  # 단위는 1000,000 으로 나눔, Mbps표시.
    #         else:
    #             itemVal = ''
    #
    #     sub_msg += (' %s' % itemVal)
    #     sub_msg += (lambda x: '%s' % x if x is not None and x != '' else '')(unit)


    if resolve_mon_gap != '':
        sub_msg += ('%s' % ', 지속 ' + resolve_mon_gap)

    msg+=sub_msg
    strlen=len(msg.decode('utf-8').encode('euc-kr'))

    # 고객명을 가변적으로
    # 80 Byte 보다 크면, 짧은 SMS 전송.
    if strlen > 80:
        msg=make_short_msg(msg)

    return msg


def _saveSmsHist(dbm, isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeqList=None, smsMsgId=None ):
    """
    - FUNC: SMS 전송 이력 저장
    - INPUT
        dbm(M): DB 연결 객체
        isResult(M): SMS 전송 처리 완료 여부
        itemSeq(M): 감시 아이템 Seq
        sendStatus(M): SMS 전송 상태
        error(M): SMS 전송 처리 상태
        curAlarmSeq(M): 장애 Seq
        userSeqList(O): SMS 수신자 리스트(None 일 경우, 수신자 정보 생략)
        smsMsgId(O): SMS 메시지 ID(None 일 경우, 없을 경우 생략)
    """
    try:
        if DEBUG_LOG_YN == 'y': logger.info("""[_saveSmsHist] ==========> isResult : %s, itemSeq : %s, sendStatus : %s, error : %s, curAlarmSeq : %s, userSeqList : %s, smsMsgId : %s
            """ % (str(isResult), str(itemSeq), str(sendStatus), str(error), str(curAlarmSeq), sa.myPrettyPrinter().pformat(userSeqList), str(smsMsgId)))
        if userSeqList == None:
            dbm.execute( db_sql.INSERT_SMS_HIST( isResult, itemSeq, sendStatus, error, curAlarmSeq ) )
        else:
            for userSeq in userSeqList:
                dbm.execute( db_sql.INSERT_SMS_HIST( isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeq['smsuserseq'], smsMsgId ) )
    except Exception, e:
            logger.fatal(e)
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
            logger.error( rres.lF('Save SMSHistory') )
            web_api.notiInternalError( rres.toWebRes() )


def _saveSmsHist_Aruba(dbm, isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeqList=None, smsMsgId=None ):
    """
    - FUNC: SMS 전송 이력 저장
    - INPUT
        dbm(M): DB 연결 객체
        isResult(M): SMS 전송 처리 완료 여부
        itemSeq(M): 감시 아이템 Seq
        sendStatus(M): SMS 전송 상태
        error(M): SMS 전송 처리 상태
        curAlarmSeq(M): 장애 Seq
        userSeqList(O): SMS 수신자 리스트(None 일 경우, 수신자 정보 생략)
        smsMsgId(O): SMS 메시지 ID(None 일 경우, 없을 경우 생략)
    """
    try:
        if DEBUG_LOG_YN == 'y': logger.info("""[_saveSmsHist] ==========> isResult : %s, itemSeq : %s, sendStatus : %s, error : %s, curAlarmSeq : %s, userSeqList : %s, smsMsgId : %s
            """ % (str(isResult), str(itemSeq), str(sendStatus), str(error), str(curAlarmSeq), sa.myPrettyPrinter().pformat(userSeqList), str(smsMsgId)))
        if userSeqList == None:
            dbm.execute( db_sql.INSERT_SMS_HIST_ARUBA( isResult, itemSeq, sendStatus, error, curAlarmSeq ) )
        else:
            for userSeq in userSeqList:
                sql = db_sql.INSERT_SMS_HIST_ARUBA( isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeq['smsuserseq'], smsMsgId )
                # logger.info(sql)
                dbm.execute( db_sql.INSERT_SMS_HIST_ARUBA( isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeq['smsuserseq'], smsMsgId ) )
    except Exception, e:
            logger.fatal(e)
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
            logger.error( rres.lF('Save SMSHistory') )
            web_api.notiInternalError( rres.toWebRes() )


def _notifySms( isResolve, dbm, mysql, cfg, smsID, callback,
               itemSeq, itemVal=None, alertGrade=None, trig_name=None, dttm=None, curAlarmSeq=None, isLineStatus=None ):
    """
    - FUNC: SMS로 장애 정보 전송
    - INPUT
        isResolve(M): 장애 발생/해제 여부
        dbm(M): DB 연결 객체
        mysql(M): SMS DB 연결 객체
        cfg(M): Orch-M 설정 정보
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
        itemSeq(M): 장애 헤제 시간
        itemVal(O): 장애 헤제 시간
        alertGrade(O): 장애 헤제 등급
        trig_name(O): 장애 헤제 시간
        dttm(O): 장애 헤제 시간
        curAlarmSeq(O): 장애 헤제 시간
    - OUTPUT : SMS 장애 메시지 전송 결과
        result: rrl_handler._ReqResult
    """
    FNAME = 'Notify SMS'
    try :

        # DEBUG_LOG_YN = 'y'
        
        ## Item 정보조회
        if isResolve:
            if DEBUG_LOG_YN == 'y': logger.info("""[_notifySms_1] ==========> cfg : %s, smsID : %s, callback : %s, itemSeq : %s, itemVal : %s,
                           alertGrade : %s, trig_name : %s, dttm : %s, curAlarmSeq : %s
                        """ % (str(cfg), str(smsID), str(callback), str(itemSeq), str(itemVal),
                               str(alertGrade), str(trig_name), str(dttm), str(curAlarmSeq)))

            # 2017.03.29 운영팀요구사항에대한 김승주전임 주석처리 요청.
            # ## 하나의 아이템에 대해 장애가 모두 해결되었을 경우 SMS 전송
            # ret = dbm.select( db_sql.GET_UNRESOLVED_ALARM(itemSeq) )
            # if len(ret) > 0:
            #     rres = rrl.rSc(None, ret, itemSeq)
            #     return rres

            getSql = db_sql.GET_RESOLVED_ALARM(itemSeq)
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_2] ==========> getSql : %s' % str(getSql))

        else:
            getSql = db_sql.GET_ITEMINSTANCE_INFO_FOR_SMS( itemSeq )
        ## 가장 최근 장애 데이터 가져오기

        # logger.info('[getSql] ==========> %s' % getSql)

        ret = dbm.select( getSql )
        if DEBUG_LOG_YN == 'y': 
            logger.info('[_notifySms_3] ==========> isResolve : %s, ret : %s' % (str(isResolve), sa.myPrettyPrinter().pformat(ret)))
            
        if isResolve and len(ret) < 1:
            rres = rrl.rSc(None, ret, itemSeq)
            return rres

        if ret == None or len(ret) < 1 :
            if ret == None:
                rc = rrl.RS_FAIL_DB
                err = 'Fail to Get Info'
            else:
                rc = rrl.RS_NO_DATA
                err = None
            rres = rrl.rFa(None, rc, err, ret, {'itemInstSeq':itemSeq})
            logger.error( rres.lF(FNAME) )
            web_api.notiInternalError( rres )
            return rres

        orgName = ret[0]['orgnamescode']
        svrSeq = ret[0]['serverseq']
        onebox_type = ret[0]['nfsubcat']
        onebox_ip = ret[0]['mgmtip']

        # 2017.10.26 - lsh,
        # One-Box 가 아닌 System 일 경우 그룹명 시스템
        if onebox_type == 'System' :
            group_seq = -1
            group_name = "시스템"
        else :
            # 2017.09.18 - lsh, group seq, group_name 추가
            group_seq = (lambda x: '%s' % x if x is not None and x != '' else '0')(ret[0]['group_seq'])
            group_name = (lambda x: '%s' % x if x is not None and x != '' else "99.미분류")(ret[0]['group_name'])

        # 2017.03.31 운영팀 sms메시지 한글처리로 추가
        visibleName = ret[0]['visiblename']
        # visibleName = 'UTM 라이센스 상태'

        # TODO : 회선 상태조회 DOWN 일때 처리 필요
        if isLineStatus :
            visibleName = '회선연결상태'

        valueType = ret[0]['value_type']
        if valueType == 'status':
            valueTypeName = '상태'
        else:
            if visibleName.find('라이센스') > 0:
                valueType = 'status'
                valueTypeName = '상태'
            else:
                valueTypeName = '성능'
                valueType = 'perf'

        customerName = ret[0]['customername']
        if isResolve :
            curAlarmSeq = ret[0]['curalarmseq']


        # 2017. 9.18 - lsh
        # 문자발송은 지정한 장애등급, 그룹 스케쥴에 해당할경우 발송 한다.
        grade = sa.getGrade(alertGrade)     # 발생한 장애/해제 등급.
        
        # Column 이름 조립.
        fault_name = str(grade).lower() + '_' + valueType + '_yn'

        # logger.info('fault_name = %s' % fault_name)

        # 요일별, 그레이드별 조회.
        # 우선순위별 Onebox, Group, All 로 3개의 ROW 를 가져온다. (DB 값이 없을 경우 표시안됨)
        #  3 Row 중 첫줄만 체크한다.  (값이 있는건 우선 순위라는 뜻)
        ret_info = dbm.select(db_sql.GET_SMS_WEEK_FAULT_INFO( svrSeq, group_seq, fault_name ))

        if ret_info == None or len(ret_info) < 1 :
            if ret_info == None:
                rc = rrl.RS_FAIL_DB
                err = 'Fail to GET_SMS_WEEK_FAULT_INFO Info'
            else:
                rc = rrl.RS_NO_DATA
                err = None
            rres = rrl.rFa(None, rc, err, ret_info, {'itemInstSeq':svrSeq,'itemInstSeq':group_seq,'itemInstSeq':fault_name})
            logger.error( rres.lF(FNAME) )
            web_api.notiInternalError( rres )
            return rres

        bSendSMS = False

        # 2024-25 추가 개발 : 라이센스 major 도 sms 발송 가능하도록
        # 라이센스 이고,
        # major 이면 fault_yn = 'Y' 로
        # deny_yn = 'Y' 로
        # alertGrade = 5 (critical)로
        # 강제 변경해주어 sms 발송되도록 유도한다
        if visibleName.find ('라이센스') > 0 and str(grade).lower() == 'major':
            ret_info[0]['fault_yn'] = 'Y'
            ret_info[0]['deny_yn'] = 'Y'
            alertGrade = 5

        # 발송금지 이면 제외
        bDeny = False
        if ret_info[0]['deny_yn'] == 'Y':
            # 날짜조건 계산
            today=datetime.today().date()
            deny_sdt = ret_info[0]['deny_sdt']
            deny_edt = ret_info[0]['deny_edt']

            # 발송금지 기간이다.
            if today >= deny_sdt and today <= deny_edt:
                bDeny = True

        # logger.info('ret_info[0] = %s' % ret_info[0])

        # 조건에 만족하면 SMS 발송.
        # 발송금지기간 아니고,  요일, 장애등급 == Y
        if not bDeny and ( ret_info[0]['today_yn'] == 'Y' and ret_info[0]['fault_yn'] == 'Y'):
            # 발송시간 체크해서 발송유무 확정.
            allow_stm=ret_info[0]['allow_stm']
            allow_etm=ret_info[0]['allow_etm']


            # 발송시간 입력 없으면
            if allow_stm.strftime('%H:%M:%S') == '00:00:00' and allow_etm.strftime('%H:%M:%S') == '00:00:00':
                bSendSMS = True  # SMS 발송한다.
            else :
                # 발송시간이 입력 되어있을 경우 오늘[날짜] 더하기 발송 가능 [시간].
                current_date = datetime.today().date()
                stime = datetime.combine(current_date, allow_stm)
                etime = datetime.combine(current_date, allow_etm)

                # 시간 범위가 종료가 작을경우 하루를 더해준다.
                if allow_stm > allow_etm :
                    etime = etime + timedelta(days=1)

                # 뒷부분 시간을 59분 59초로
                etime = etime.replace (minute=59, second=59)

                # logger.info('stime = %s' % stime)
                # logger.info('etime = %s' % etime)
                # logger.info('now = %s' % datetime.now())

                # 현재 시간이 발송시간 범위 안에 있나?
                if datetime.now() >=  stime and datetime.now() <= etime :
                    bSendSMS = True # SMS 발송한다.

        ## SMS 전송 문자열 생성
        subject = '' #trig_name
        if isResolve:
            msg = _getResolveMsg(orgName, ret[0]['servername'], ret[0]['targetname'], ret[0]['monitoritem'], ret[0]['monitorobject'], ret[0]['resolve_methodcode'],
                                    alertGrade, visibleName, valueTypeName, group_name, customerName, ret[0]['resolve_mon_gap'], ret[0]['unit'], itemVal)
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_7] ==========> msg : %s' % str(msg))
        else:
            msg = _toSmsMsg(orgName, ret[0]['servername'], ret[0]['targetname'], ret[0]['targetversion'], ret[0]['monitoritem'],
                                ret[0]['monitorobject'], ret[0]['unit'], itemVal, alertGrade, dttm,
                                trig_name, visibleName, valueTypeName, group_name, customerName)
        

        # 18. 4.16 - kt 요구 사항
        # "연결" 문자열이 없으면 발송 취소
        if bSendSMS :
            if visibleName.find('연결') == -1 :
                logger.info('SMS [연결] 문자열 없음. 발송취소 ')
                bSendSMS = False

            if msg.find('회선') > 0 :
                logger.info('SMS [회선] 문자열 있으면. 발송취소 ')
                bSendSMS = False

            # 19. 4. 5 - kt 요구 사항
            # "VPN" 문자열이 있으면 전송
            if msg.find ('VPN') > 0 or msg.find ('vpn') > 0 :
                #logger.info('msg : %s ' % msg)
                #logger.info('SMS [VPN] 문자열 있음. 발송 ')
                bSendSMS = True

            # 24. 3. 5 - kt 요구 사항 : 라이센스 만료로 인한 문자 발송 요청
            # "라이센스" 문자열이 있으면 전송
            if visibleName.find ('라이센스') > 0:
                logger.info('msg : %s ' % msg)
                logger.info('SMS [라이센스] 문자열 있음. 발송 ')
                bSendSMS = True

        if bSendSMS :
            msg_copy = msg
            # 20. 5.12 - lsh
            # 운영진 요구사항, SMS 중복발송 표시.
            # 발생만 누적, 해제는 지속시간 때문에 중복처리 안되어 제외함.
            if msg.find ('[발/') > -1 :
                # redis 에 카운터 증가, Key 없으면 1로 리턴됨.
                sms_count = redis.incr (msg)

                # SMS 중복체크 유지기간 24시간.
                redis.expire (msg, 86400) 

                if sms_count > 1 : 
                    # [발  --> [발2회 .. [발3회 .. [발4회
                    # 예)  [발4회/C]1. LTEPNF0310,본사,Daemon-vpn 상태 DOWN 
                    msg = msg.replace ('[발', '[발%s회' % sms_count )


            logger.info("Send MSG : %s " % msg)

            ## SMS 전송 리스트 조회
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_5] ==========> orgName : %s, svrSeq : %s' % (str(orgName), str(svrSeq)))
            smsUserList = dbm.select( db_sql.GET_SMSUSERS( orgName, svrSeq ) )

            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_6] ==========> smsUserList : %s' % sa.myPrettyPrinter().pformat(smsUserList))

            if len(smsUserList) < 1 :
                rres = rrl.rSc(None, smsUserList, {'orgName':orgName, 'svrSeq':svrSeq}, _msg='No SMS User')
                logger.warning( rres.lL(FNAME) )
                web_api.notiInternalError( rres )
                return rres
    #             return True

            # 2021. 3. 8 - KT 요구사항, UTM 연결상태 DOWN 일때 TCP Ping 체크
            if msg.find ('UTM 연결상태 DOWN') > 0 :
                # 2021. 3.26 - 추가
                # KT-VNF 는 체크 안함.
                isKT_VNF = dbm.select( db_sql.IS_KT_VNF( svrSeq ) )

                # 결과 없으면 KT-VNF 아님 -> AXGATE
                if len(isKT_VNF) < 1 :
                    smsUserList_copy = copy.deepcopy(smsUserList)
                    tcpping = TcpPingChecker( onebox_ip, logger, cfg, smsID, subject, msg_copy, callback, smsUserList_copy, sms_mng.saveSms)
                    tcpping.start()

            # SMS 전송
            ret = sms_mng.saveSms( logger, mysql, smsID, subject, msg, callback, smsUserList )
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_9] ==========> ret : %s' % str(ret))
            _param = {'smsid':smsID, 'subject':subject, 'msg':msg, 'callback':callback, 'user_list':smsUserList}
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_10] ==========> _param : %s' % sa.myPrettyPrinter().pformat(_param)) # str(_param)

            if ret == None :
                rres = rrl.rFa(None, rrl.RS_API_SMS_ERR, None, ret, _param)
                logger.error( rres.lF(FNAME) )
                web_api.notiInternalError( rres )
                # SMS 전송 이력 저장
                _saveSmsHist( dbm, True, itemSeq, 'FAIL', 'SMS-SEND REQ FAIL', curAlarmSeq )
                return rres
    
            ## Telegram 전송, api key 값이 있으면 전송.
            api_key=(lambda x: x['telegram_apikey'] if x.has_key('telegram_apikey') else '')(cfg)
            if api_key !='' :
                url = "https://api.telegram.org/bot%s/sendMessage?chat_id=-1001216014305&text=%s" % (api_key, msg)
                try :
                    aaa = ''
                    # url_ret = urllib2.urlopen(url)
                except :
                    logger.error("Telegram API Error : %s" % url )

            rres = rrl.rSc(None, ret, _param)
            # logger.info( rres.lL(FNAME) )
            # SMS 전송 이력 저장
            _saveSmsHist( dbm, False, itemSeq, 'SENDING', 'SMS-SEDNING', curAlarmSeq, smsUserList, ret )

            ## SMS 전송 결과 확인 및 이력 저장
            smsChk = smsRecvChecker( cfg, curAlarmSeq, ret, smsUserList )
            smsChk.start()
        else :
            rres=rrl.rSc(None, ret,  { 'svrSeq': svrSeq})

        return rres
#         return True
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error( rres.lF(FNAME) )
        logger.fatal(e)
        # SMS 전송 이력 저장
        _saveSmsHist( dbm, True, itemSeq, 'FAIL', 'INTERNAL_EXCEPTION', curAlarmSeq )
        return rres


def _notifySms_Aruba(isResolve, dbm, mysql, cfg, smsID, callback,
               itemSeq, itemVal=None, alertGrade=None, trig_name=None, dttm=None, curAlarmSeq=None, isLineStatus=None, ArubaData={}):
    """
    - FUNC: SMS로 장애 정보 전송
    - INPUT
        isResolve(M): 장애 발생/해제 여부
        dbm(M): DB 연결 객체
        mysql(M): SMS DB 연결 객체
        cfg(M): Orch-M 설정 정보
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
        itemSeq(M): 장애 헤제 시간
        itemVal(O): 장애 헤제 시간
        alertGrade(O): 장애 헤제 등급
        trig_name(O): 장애 헤제 시간
        dttm(O): 장애 헤제 시간
        curAlarmSeq(O): 장애 헤제 시간
        ArubaData : Aruba fault noti data
    - OUTPUT : SMS 장애 메시지 전송 결과
        result: rrl_handler._ReqResult
    """
    FNAME = 'Notify SMS'
    try:

        # DEBUG_LOG_YN = 'y'

        ## Item 정보조회
        if isResolve:
            if DEBUG_LOG_YN == 'y': logger.info("""[_notifySms_1] ==========> cfg : %s, smsID : %s, callback : %s, itemSeq : %s, itemVal : %s,
                           alertGrade : %s, trig_name : %s, dttm : %s, curAlarmSeq : %s
                        """ % (str(cfg), str(smsID), str(callback), str(itemSeq), str(itemVal),
                               str(alertGrade), str(trig_name), str(dttm), str(curAlarmSeq)))

            # 2017.03.29 운영팀요구사항에대한 김승주전임 주석처리 요청.
            # ## 하나의 아이템에 대해 장애가 모두 해결되었을 경우 SMS 전송
            # ret = dbm.select( db_sql.GET_UNRESOLVED_ALARM(itemSeq) )
            # if len(ret) > 0:
            #     rres = rrl.rSc(None, ret, itemSeq)
            #     return rres

            getSql = db_sql.GET_RESOLVED_ALARM_ARUBA(itemSeq)
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_2] ==========> getSql : %s' % str(getSql))

        else:
            getSql = db_sql.GET_ITEMINSTANCE_INFO_FOR_SMS_ARUBA(itemSeq)
        ## 가장 최근 장애 데이터 가져오기

        # logger.info('[getSql] ==========> %s' % getSql)

        ret = dbm.select(getSql)
        if DEBUG_LOG_YN == 'y':
            logger.info('[_notifySms_3] ==========> isResolve : %s, ret : %s' % (
            str(isResolve), sa.myPrettyPrinter().pformat(ret)))

        if isResolve and len(ret) < 1:
            rres = rrl.rSc(None, ret, itemSeq)
            return rres

        if ret == None or len(ret) < 1:
            if ret == None:
                rc = rrl.RS_FAIL_DB
                err = 'Fail to Get Info'
            else:
                rc = rrl.RS_NO_DATA
                err = None
            rres = rrl.rFa(None, rc, err, ret, {'itemInstSeq': itemSeq})
            logger.error(rres.lF(FNAME))
            # web_api.notiInternalError(rres)
            return rres

        # orgName = ret[0]['orgnamescode']
        # svrSeq = ret[0]['serverseq']
        # onebox_type = ret[0]['nfsubcat']
        # onebox_ip = ret[0]['mgmtip']

        # logger.info('ArubaData = %s' % str(ArubaData))

        orgName = ret[0]['orgnamescode']
        if orgName == None:
            orgName = '미분류'

        svrSeq = itemSeq
        onebox_type = 'Aruba'
        onebox_ip = ret[0]['publicip']
        if onebox_ip == None:
            onebox_ip = ArubaData['body']['host']['ip']

        # logger.debug('ArubaData = %s' % str(ArubaData))

        # 2017.10.26 - lsh,
        # One-Box 가 아닌 System 일 경우 그룹명 시스템
        if onebox_type == 'System':
            group_seq = -1
            group_name = "시스템"
        else:
            # # 2017.09.18 - lsh, group seq, group_name 추가
            # group_seq = (lambda x: '%s' % x if x is not None and x != '' else '0')(ret[0]['group_seq'])
            # group_name = (lambda x: '%s' % x if x is not None and x != '' else "99.미분류")(ret[0]['group_name'])
            group_name = (lambda x: '%s' % x if x is not None and x != '' else "99.미분류")('AC')

        # 2017.03.31 운영팀 sms메시지 한글처리로 추가
        # visibleName = ret[0]['visiblename']
        # visibleName = ArubaData['body']['trigger']['name']
        visibleName = '서버 연결 상태'

        # TODO : 회선 상태조회 DOWN 일때 처리 필요
        if isLineStatus:
            visibleName = '회선연결상태'

        valueType = 'status'
        if valueType == 'status':
            valueTypeName = '상태'
        else:
            valueTypeName = '성능'
            valueType = 'perf'

        customerName = ret[0]['servername']
        if customerName == None:
            customerName = ArubaData['body']['host']['name']

        # if isResolve:
        #     curAlarmSeq = ret[0]['curalarmseq']

        # 2017. 9.18 - lsh
        # 문자발송은 지정한 장애등급, 그룹 스케쥴에 해당할경우 발송 한다.
        grade = sa.getGrade(alertGrade)  # 발생한 장애/해제 등급.

        bSendSMS = True

        # 추가 요청 사항
        # 요일별 시간대별 발송 금지 처리
        # 요일 : 월(0), 화(1), 수(2), 목(3), 금(4), 토(5), 일(6)
        # 시간 :
        targetday = datetime.today().weekday()

        if targetday == 5 or targetday == 6:
            bSendSMS = False
        else:
            now = str(datetime.now())
            now = now.split('.')
            nowTime = now[0].split(' ')
            nTime = nowTime[1].replace(':', '')

            # 08 시 이전이면 발송 금지
            if int(nTime) < 80000:
                bSendSMS = False

            # 22 시 이후면 발송 금지
            if int(nTime) > 220000:
                bSendSMS = False

        # # todo : 문자 발송 먼저 개발, 차후 인지처리 개발
        # # Column 이름 조립.
        # fault_name = str(grade).lower() + '_' + valueType + '_yn'
        #
        # # 요일별, 그레이드별 조회.
        # # 우선순위별 Onebox, Group, All 로 3개의 ROW 를 가져온다. (DB 값이 없을 경우 표시안됨)
        # #  3 Row 중 첫줄만 체크한다.  (값이 있는건 우선 순위라는 뜻)
        # ret_info = dbm.select(db_sql.GET_SMS_WEEK_FAULT_INFO(svrSeq, group_seq, fault_name))
        #
        # if ret_info == None or len(ret_info) < 1:
        #     if ret_info == None:
        #         rc = rrl.RS_FAIL_DB
        #         err = 'Fail to GET_SMS_WEEK_FAULT_INFO Info'
        #     else:
        #         rc = rrl.RS_NO_DATA
        #         err = None
        #     rres = rrl.rFa(None, rc, err, ret_info,
        #                    {'svrSeq': svrSeq, 'group_seq': group_seq, 'fault_name': fault_name})
        #     logger.error(rres.lF(FNAME))
        #     web_api.notiInternalError(rres)
        #     return rres
        #
        # # 발송금지 이면 제외
        # bDeny = False
        # if ret_info[0]['deny_yn'] == 'Y':
        #     # 날짜조건 계산
        #     today = datetime.today().date()
        #     deny_sdt = ret_info[0]['deny_sdt']
        #     deny_edt = ret_info[0]['deny_edt']
        #
        #     # 발송금지 기간이다.
        #     if today >= deny_sdt and today <= deny_edt:
        #         bDeny = True
        #
        # # 조건에 만족하면 SMS 발송.
        # # 발송금지기간 아니고,  요일, 장애등급 == Y
        # if not bDeny and (ret_info[0]['today_yn'] == 'Y' and ret_info[0]['fault_yn'] == 'Y'):
        #     # 발송시간 체크해서 발송유무 확정.
        #     allow_stm = ret_info[0]['allow_stm']
        #     allow_etm = ret_info[0]['allow_etm']
        #
        #     # 발송시간 입력 없으면
        #     if allow_stm.strftime('%H:%M:%S') == '00:00:00' and allow_etm.strftime('%H:%M:%S') == '00:00:00':
        #         bSendSMS = True  # SMS 발송한다.
        #     else:
        #         # 발송시간이 입력 되어있을 경우 오늘[날짜] 더하기 발송 가능 [시간].
        #         current_date = datetime.today().date()
        #         stime = datetime.combine(current_date, allow_stm)
        #         etime = datetime.combine(current_date, allow_etm)
        #
        #         # 시간 범위가 종료가 작을경우 하루를 더해준다.
        #         if allow_stm > allow_etm:
        #             etime = etime + timedelta(days=1)
        #
        #         # 뒷부분 시간을 59분 59초로
        #         etime = etime.replace(minute=59, second=59)
        #
        #         # 현재 시간이 발송시간 범위 안에 있나?
        #         if datetime.now() >= stime and datetime.now() <= etime:
        #             bSendSMS = True  # SMS 발송한다.

        ## SMS 전송 문자열 생성
        subject = ''  # trig_name
        if isResolve:
            resolve_mon_gap = ret[0]['resolve_mon_gap'].split('.')
            msg = _getResolveMsg_Aruba(orgName, ret[0]['servername'], 'ARUBA SVR', 'SVR Connection',
                                 '', '',
                                 alertGrade, visibleName, valueTypeName, 'ARU', customerName,
                                 resolve_mon_gap[0], '', itemVal)
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_7] ==========> msg : %s' % str(msg))
        else:
            msg = _toSmsMsg_Aruba(orgName, ret[0]['servername'], 'ARUBA SVR', 'v1.1',
                            'SVR Connection',
                            '', '', itemVal, alertGrade, dttm,
                            trig_name, visibleName, valueTypeName, 'ARU', customerName)

        # 18. 4.16 - kt 요구 사항
        # "연결" 문자열이 없으면 발송 취소
        if bSendSMS:
            if visibleName.find('연결') == -1:
                logger.info('SMS [연결] 문자열 없음. 발송취소 ')
                bSendSMS = False

            # if msg.find('회선') > 0:
            #     logger.info('SMS [회선] 문자열 있으면. 발송취소 ')
            #     bSendSMS = False

            # 19. 4. 5 - kt 요구 사항
            # "VPN" 문자열이 있으면 전송
            if msg.find('VPN') > 0 or msg.find('vpn') > 0:
                # logger.info('msg : %s ' % msg)
                # logger.info('SMS [VPN] 문자열 있음. 발송 ')
                bSendSMS = True

        if bSendSMS:
            msg_copy = msg
            # 20. 5.12 - lsh
            # 운영진 요구사항, SMS 중복발송 표시.
            # 발생만 누적, 해제는 지속시간 때문에 중복처리 안되어 제외함.
            if msg.find('[발/') > -1:
                # redis 에 카운터 증가, Key 없으면 1로 리턴됨.
                sms_count = redis.incr(msg)

                # SMS 중복체크 유지기간 24시간.
                redis.expire(msg, 86400)

                if sms_count > 1:
                    # [발  --> [발2회 .. [발3회 .. [발4회
                    # 예)  [발4회/C]1. LTEPNF0310,본사,Daemon-vpn 상태 DOWN
                    msg = msg.replace('[발', '[발%s회' % sms_count)

            # logger.info("Send MSG : %s " % msg)

            ## SMS 전송 리스트 조회
            if DEBUG_LOG_YN == 'y': logger.info(
                '[_notifySms_5] ==========> orgName : %s, svrSeq : %s' % (str(orgName), str(svrSeq)))
            smsUserList = dbm.select(db_sql.GET_SMSUSERS(orgName, svrSeq))

            if DEBUG_LOG_YN == 'y': logger.info(
                '[_notifySms_6] ==========> smsUserList : %s' % sa.myPrettyPrinter().pformat(smsUserList))

            if len(smsUserList) < 1:
                rres = rrl.rSc(None, smsUserList, {'orgName': orgName, 'svrSeq': svrSeq}, _msg='No SMS User')
                logger.warning(rres.lL(FNAME))
                web_api.notiInternalError(rres)
                return rres
            #             return True

            # 2021. 3. 8 - KT 요구사항, UTM 연결상태 DOWN 일때 TCP Ping 체크
            if msg.find('UTM 연결상태 DOWN') > 0:
                # 2021. 3.26 - 추가
                # KT-VNF 는 체크 안함.
                isKT_VNF = dbm.select(db_sql.IS_KT_VNF(svrSeq))

                # 결과 없으면 KT-VNF 아님 -> AXGATE
                if len(isKT_VNF) < 1:
                    smsUserList_copy = copy.deepcopy(smsUserList)
                    tcpping = TcpPingChecker(onebox_ip, logger, cfg, smsID, subject, msg_copy, callback,
                                             smsUserList_copy, sms_mng.saveSms)
                    tcpping.start()

            # SMS 전송
            ret = sms_mng.saveSms(logger, mysql, smsID, subject, msg, callback, smsUserList)
            if DEBUG_LOG_YN == 'y': logger.info('[_notifySms_9] ==========> ret : %s' % str(ret))
            _param = {'smsid': smsID, 'subject': subject, 'msg': msg, 'callback': callback, 'user_list': smsUserList}
            if DEBUG_LOG_YN == 'y': logger.info(
                '[_notifySms_10] ==========> _param : %s' % sa.myPrettyPrinter().pformat(_param))  # str(_param)

            if ret == None:
                rres = rrl.rFa(None, rrl.RS_API_SMS_ERR, None, ret, _param)
                logger.error(rres.lF(FNAME))
                web_api.notiInternalError(rres)
                # SMS 전송 이력 저장
                _saveSmsHist_Aruba(dbm, True, itemSeq, 'FAIL', 'SMS-SEND REQ FAIL', curAlarmSeq)
                return rres

            rres = rrl.rSc(None, ret, _param)
            # logger.info( rres.lL(FNAME) )
            # SMS 전송 이력 저장
            _saveSmsHist_Aruba(dbm, False, itemSeq, 'SENDING', 'SMS-SEDNING', curAlarmSeq, smsUserList, ret)

            ## SMS 전송 결과 확인 및 이력 저장
            smsChk = smsRecvChecker(cfg, curAlarmSeq, ret, smsUserList, isAruba=True)
            smsChk.start()
        else:
            rres = rrl.rSc(None, ret, {'svrSeq': svrSeq})

        return rres
    #         return True
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        # SMS 전송 이력 저장
        _saveSmsHist_Aruba(dbm, True, itemSeq, 'FAIL', 'INTERNAL_EXCEPTION', curAlarmSeq)
        return rres


def _notifyAlarm(dbm, mysql, cfg, smsID, callback, itemSeq, itemVal, alertGrade, trig_name, dttm, curAlarmSeq, isLineStatus):
    """
    - FUNC: SMS로 장애 발생 정보 전송
    - INPUT
        dbm(M): DB 연결 객체
        mysql(M): SMS DB 연결 객체
        cfg(M): Orch-M 설정 정보
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
        itemSeq(M): 장애 헤제 시간
        itemVal(O): 장애 헤제 시간
        alertGrade(O): 장애 헤제 시간
        trig_name(O): 장애 헤제 시간
        dttm(O): 장애 헤제 시간
        curAlarmSeq(O): 장애 헤제 시간
    - OUTPUT : SMS 장애 발생 메시지 전송 결과
        result: rrl_handler._ReqResult
    """

    return _notifySms(False, dbm, mysql, cfg, smsID, callback, itemSeq, itemVal, alertGrade, trig_name, dttm, curAlarmSeq, isLineStatus)


def _notifyAlarm_Aruba(dbm, mysql, cfg, smsID, callback, itemSeq, itemVal, alertGrade, trig_name, dttm, curAlarmSeq,
                 isLineStatus, ArubaData={}):
    """
    - FUNC: SMS로 장애 발생 정보 전송
    - INPUT
        dbm(M): DB 연결 객체
        mysql(M): SMS DB 연결 객체
        cfg(M): Orch-M 설정 정보
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
        itemSeq(M): 장애 헤제 시간
        itemVal(O): 장애 헤제 시간
        alertGrade(O): 장애 헤제 시간
        trig_name(O): 장애 헤제 시간
        dttm(O): 장애 헤제 시간
        curAlarmSeq(O): 장애 헤제 시간
    - OUTPUT : SMS 장애 발생 메시지 전송 결과
        result: rrl_handler._ReqResult
    """

    return _notifySms_Aruba(False, dbm, mysql, cfg, smsID, callback, itemSeq, itemVal, alertGrade, trig_name, dttm,
                                curAlarmSeq, isLineStatus, ArubaData)


def _notifyResolve(dbm, mysql, cfg, smsID, callback, itemSeq, alertGrade=None, itemVal=None, isLineStatus=None):
    """
    - FUNC: SMS로 장애 해제 정보 전송
    - INPUT
        dbm(M): DB 연결 객체
        mysql(M): SMS DB 연결 객체
        cfg(M): Orch-M 설정 정보
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
        itemSeq(M): 장애 헤제 시간
    - OUTPUT : SMS 장애 해제 메시지 전송 결과
        result: rrl_handler._ReqResult
    """
    if DEBUG_LOG_YN == 'y': logger.info("""[_notifyResolve] ==========> cfg : %s, smsID : %s, callback : %s, itemSeq : %s, alertGrade : %s  
                """ % (str(cfg), str(smsID), str(callback), str(itemSeq), str(alertGrade)))
    # 2017.03.29 alertGrade 추가.
    #return _notifySms(True, dbm, mysql, cfg, smsID, callback, itemSeq)
    return _notifySms(True, dbm, mysql, cfg, smsID, callback, itemSeq, itemVal, alertGrade, None, None, None, isLineStatus)


def _notifyResolve_Aruba(dbm, mysql, cfg, smsID, callback, itemSeq, alertGrade=None, itemVal=None, isLineStatus=None, ArubaData={}):
    """
    - FUNC: SMS로 장애 해제 정보 전송
    - INPUT
        dbm(M): DB 연결 객체
        mysql(M): SMS DB 연결 객체
        cfg(M): Orch-M 설정 정보
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
        itemSeq(M): 장애 헤제 시간
    - OUTPUT : SMS 장애 해제 메시지 전송 결과
        result: rrl_handler._ReqResult
    """
    if DEBUG_LOG_YN == 'y': logger.info("""[_notifyResolve] ==========> cfg : %s, smsID : %s, callback : %s, itemSeq : %s, alertGrade : %s  
                """ % (str(cfg), str(smsID), str(callback), str(itemSeq), str(alertGrade)))
    # 2017.03.29 alertGrade 추가.
    #return _notifySms(True, dbm, mysql, cfg, smsID, callback, itemSeq)
    return _notifySms_Aruba(True, dbm, mysql, cfg, smsID, callback, itemSeq, itemVal, alertGrade, None, None, None, isLineStatus, ArubaData)


def _notifyAlarmToWeb(itemSeq, alertGrade, isAlert, dttm, trig_name=None, itemVal=None):
    """
    - FUNC: WEB으로 장애 정보 Noti
    - INPUT
        itemSeq(M): 감시 아이템 Seq
        alertGrade(M): 장애 등급
        isAlert(M): 장애 발생/해제 여부
        dttm(M): 발생/해제 시간
        trig_name(M): 장애 정보 요약
        itemVal(M): 측정 값
    """
    web_api.notiAlarmWeb(itemSeq, alertGrade, isAlert, dttm, trig_name, itemVal)

def refreshFault(dbm, cfg):
    """
    - FUNC: ZB와 장애 데이터 동기화
    - INPUT
        dbm(M): DB 연결 객체
        cfg(M): Orch-M 설정 정보
    - OUTPUT : ZB 데이터 동기화 처리 수
        result: rrl_handler._ReqResult
    """
    FNAME = 'REFRESH FAULT'
    zbConnNum = (lambda x: x['zb_db_conn_num'] if x.has_key('zb_db_conn_num') else 1 )(cfg)
    zbDbm = dbManager( 'zbs', cfg['zb_db_name'], cfg['zb_db_user'], cfg['zb_db_passwd'],
                    cfg['zb_db_addr'], int(cfg['zb_db_port']), connCnt=zbConnNum, _logger=logger )

    ## ZB DB에서 발생 중인 장애 정보 조회
    isSucc, zbAlarmList = zb.getAlarmList(zbDbm, logger)
    if not isSucc :
        rres = rrl.rFa(None, rrl.RS_API_ZBS_ERR, zbAlarmList, None, None)
        logger.error(rres.lF(FNAME))
        return rres

    ## OrchM DB에서 발생 중인 장애 정보 조회
    omAlarmList = dbm.select( db_sql.GET_CURR_ALARM_FOR_REFRESH() )

    insertCnt = resolveCnt = errParsingCnt = errInsertCnt = errResolveCnt = errCnt = 0
    fMng = faultm(dbm, cfg)
    for zbAlarm in zbAlarmList:
        alarmMsg = str(zbAlarm['message'])
        try:
            msg = { 'body':json.loads(alarmMsg) }
            isSucc, faultMsg = zb.faultParsing( msg, dbm, logger )
            if not isSucc :
                rres = rrl.rFa(None, rrl.RS_FAIL_ZB_OP, 'Fault MSG Parsing Error', faultMsg, msg)
                logger.warning( rres.lF(FNAME) )
                errParsingCnt += 1
                continue
            if faultMsg == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_ZB_OP, 'Ignore or Pass Fault MSG', faultMsg, msg)
                logger.warning( rres.lL(FNAME) )
                errParsingCnt += 1
                continue

            ## OrchM과 동일한 장애일 경우 OrchM 장애 리스트에서 제거
            isHandled = False
            for omAlarm in omAlarmList:
                # ['itemSeq'], ['itemVal'], ['alertGrade'], ['isAlert'], ['trig_name'], ['dttm']
                if omAlarm['moniteminstanceseq'] == faultMsg['itemSeq'] and sa.getGradeCode(omAlarm['faultgradecode']) == faultMsg['alertGrade'] :
                    omAlarmList.remove(omAlarm)
                    isHandled = True
                    break
            if isHandled :
                continue

            ## OrchM에 없는 장애일 경우 장애 처리 실행
            # logger.info( rrl.rSc(None, None, faultMsg, _msg='Insert Alarm').lL(FNAME) )
#             fMng = faultm(dbm, cfg)
            rres = fMng.saveAndNoti( faultMsg['itemSeq'], faultMsg['itemVal'], faultMsg['alertGrade'],
                                     faultMsg['isAlert'], faultMsg['trig_name'], faultMsg['dttm'] )
            if rres.isSucc() :
                insertCnt += 1
            else:
                errInsertCnt += 1

        except Exception, e:
            logger.warning('Refresh Alarm Exception, alarm=%s'%str(zbAlarm))
            logger.fatal(e)
            errCnt += 1
            continue

    ## ZB에는 없고 OrchM에 발생 중인 장애로 남아있는 항목은 장애 해제 처리
    if len(omAlarmList) > 0 :
        for omAlarm in omAlarmList:
            ## zabbix-server 프로세스 감시는 orch-m에서 직접하므로 zb db에 남지 않음
            if str(omAlarm['monitorobject']).lower() != 'zabbix-server':
                # logger.info( rrl.rSc(None, None, omAlarm, _msg='Resolve Alarm').lL(FNAME) )
    #             fMng = faultm(dbm, cfg)

                # from datetime import datetime
                dttm = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
                rres = fMng.saveAndNoti( omAlarm['moniteminstanceseq'], None, sa.getGradeCode(omAlarm['faultgradecode']), False, None, dttm, True )
                if rres.isSucc() :
                    resolveCnt += 1
                else:
                    errResolveCnt += 1

    rres = rrl.rSc(None, {'insert':insertCnt, 'resolve':resolveCnt, 'err_parsing':errParsingCnt, 'err_insert':errInsertCnt, 'err_resolve':errResolveCnt, 'err_etc':errCnt}, None)
    logger.info( rres.lS(FNAME) )
    return rres

class smsRecvChecker(threading.Thread):
    """
    - FUNC: SMS 전송 후 정상적으로 전송되었는지 일정 시간 동안 응답 체크
    - INPUT
        cfg(M): Orch-M 설정 정보
        curAlarmSeq(M): 장애 발생 Seq
        smsMsgID(M): SMS 메시지 ID
        smsUserList(M): SMS 수신자 리스트
    """

    def __init__(self, cfg, curAlarmSeq, smsMsgID, smsUserList, isAruba=False ):
        threading.Thread.__init__(self)
        self.cfg = cfg

        self.duration = cfg['sms_report_chk']
        self.curAlarmSeq = curAlarmSeq
        self.smsMsgID = smsMsgID
        self.smsUserList = smsUserList
        self.isAruba = isAruba

    def run(self):
        FNAME = 'SMS Report Check'
        try:
            cnt = 0
            while True:
                cnt += 1

                mysql = MySQLdb.connect( db=self.cfg['mysql_name'], user=self.cfg['mysql_user'], passwd=self.cfg['mysql_passwd'],
                              host=self.cfg['mysql_addr'], port=self.cfg['mysql_port'] )

                ## SDK_SMS_REPORT_DETAIL 테이블에서 전송 결과 확인
                dic = sms_mng.getSmsReport( logger, mysql, self.smsMsgID )
                if dic == None or type(dic) != list :
                    rres = rrl.rFa(None, rrl.RS_API_SMS_ERR, 'Invalid Return Value', dic, {'sms_msg_id':self.smsMsgID})
                    logger.error( rres.lF(FNAME) )
                    self._saveReport( 'FAIL', 'SMSReport OP Error' )
                    return

                ## 전송결과 있으면 orch DB에 저장
                for dicReport in dic :
                    pNum = dicReport['PHONE_NUMBER']
                    sendResult = dicReport['SEND_RESULT']
                    sendError = dicReport['SEND_ERROR']
                    for user in self.smsUserList :
                        if pNum == user['phone_num'] :
                            self._saveReport(sendResult, sendError, user)
                            self.smsUserList.remove(user)
                            break

                ## 모든 smsuser에게 전송 시 종료
                if len(self.smsUserList) < 1:
                    rres = rrl.rSc(None, None, None)
                    logger.info( rres.lS(FNAME) )
                    return

                ## 전송결과 대기 시간 지나면 timeOut 처리
                if cnt > self.duration :
                    rres = rrl.rFa(None, rrl.RS_TIMEOUT, None, None, {'remain_sms_user':self.smsUserList, 'timeout':self.duration})
                    # logger.error( rres.lF(FNAME) )
                    self._saveReport( 'FAIL', 'INTERNAL_TIMEOUT' )
                    return

                mysql.close()
                sleep( 1 )

        except Exception, e:
            self._saveReport('FAIL', 'SMSReport Chk Exception' )
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'sms_msg_id':self.smsMsgID, 'alarm_seq':self.curAlarmSeq})
            logger.error( rres.lF(FNAME) )
            logger.fatal(e)
            web_api.notiInternalError( rres )
        finally:
            mysql.close()

    def _saveReport(self, result, error, smsUser=None ):
        """
        - FUNC: SMS 전송 결과 저장
        - INPUT
            result(M): SMS 전송 결과(SUCC/FAIL)
            error(M):SMS 전송 실패 원인
            smsUser(O): SMS 수신자 리스트(None일 경우 아직 처리 못한 모든 수신자 일괄 처리)
        """
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(self.cfg)
        dbm = dbManager( 'orchm-fault', self.cfg['db_name'], self.cfg['db_user'], self.cfg['db_passwd'],
                    self.cfg['db_addr'], int(self.cfg['db_port']), connCnt=connNum, _logger=logger )
        if smsUser == None :
            for user in self.smsUserList :
                if self.isAruba:
                    dbm.execute( db_sql.UPDATE_SMS_REPORT_ARUBA( result, error, user['smsuserseq'], self.smsMsgID ) )
                else:
                    dbm.execute( db_sql.UPDATE_SMS_REPORT( result, error, self.curAlarmSeq, user['smsuserseq'], self.smsMsgID ) )
        else :
            if self.isAruba:
                dbm.execute( db_sql.UPDATE_SMS_REPORT_ARUBA( result, error, smsUser['smsuserseq'], self.smsMsgID ) )
            else:
                dbm.execute( db_sql.UPDATE_SMS_REPORT( result, error, self.curAlarmSeq, smsUser['smsuserseq'], self.smsMsgID ) )

class resolveChecker(threading.Thread):
    """
    - FUNC: 장애 해제 처리하는 쓰레드( zabbix로부터 중복 메시지 처리하기 위해 1초 대기 후 처리)
    - INPUT
        cfg(M): Orch-M 설정 정보
        itemSeq(M): 감시 아이템 Seq
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
    """

    def __init__(self, cfg, itemSeq, smsID, callback ):
        threading.Thread.__init__(self)
        self.cfg = cfg
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        self.dbm = dbManager( 'orchm-fault', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                    cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )
        self.mysql = MySQLdb.connect( db=self.cfg['mysql_name'], user=self.cfg['mysql_user'], passwd=self.cfg['mysql_passwd'],
                              host=self.cfg['mysql_addr'], port=self.cfg['mysql_port'] )
        self.itemSeq = itemSeq
        self.smsID = smsID
        self.callback = callback

    def run(self):
        sleep(1)
        try:
            rres = _notifyResolve(self.dbm, self.mysql, self.cfg, self.smsID, self.callback, self.itemSeq )
            if rres.isFail():
                logger.error( rres.lF('SMS Resolve Noti') )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'sms_msg_id':self.smsID, 'item_seq':self.itemSeq})
            logger.error( rres.lF('SMS Resolve Noti') )
            logger.fatal(e)


def resolveChecker2(self, itemSeq, alertGrade, itemVal, isLineStatus, ArubaData={}):
    """
    - FUNC: 장애 해제 처리
    - INPUT
        cfg(M): Orch-M 설정 정보
        itemSeq(M): 감시 아이템 Seq
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
    """
    #self.cfg = cfg
    connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1)(self.cfg)
    self.dbm = dbManager('orchm-fault', self.cfg['db_name'], self.cfg['db_user'], self.cfg['db_passwd'],
                         self.cfg['db_addr'], int(self.cfg['db_port']), connCnt=connNum, _logger=logger)
    self.mysql = MySQLdb.connect(db=self.cfg['mysql_name'], user=self.cfg['mysql_user'],
                                 passwd=self.cfg['mysql_passwd'],
                                 host=self.cfg['mysql_addr'], port=self.cfg['mysql_port'])
    self.itemSeq = itemSeq
    #self.smsID = smsID
    #self.callback = callback

    try:
        if ArubaData:
            rres = _notifyResolve_Aruba(self.dbm, self.mysql, self.cfg, self.smsID, self.callback, self.itemSeq, alertGrade,
                                  itemVal, isLineStatus, ArubaData)
            if rres.isFail():
                logger.error(rres.lF('SMS Resolve Noti'))
        else:
            rres = _notifyResolve(self.dbm, self.mysql, self.cfg, self.smsID, self.callback, self.itemSeq, alertGrade, itemVal, isLineStatus)
            if rres.isFail():
                logger.error(rres.lF('SMS Resolve Noti'))

        return rres
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'sms_msg_id': self.smsID, 'item_seq': self.itemSeq})
        logger.error(rres.lF('SMS Resolve Noti'))
        logger.fatal(e)

        return rres


class TcpPingChecker(threading.Thread):
    """
    - FUNC: UTM 연결상태 장애일 때 TcpPing 체크 
    - 예제 SMS) [발/C]2. OPENAPI,VNF-UTM,UTM 연결상태 DOWN
    - 1분후 체크+1, 30초 후 체크+1  총 2회 체크후 장애일때 SMS 발송
    - 10 분 단위로 반복.
    - 1시간 후 종료. 1시간 이내 up 일때 up 문자 발송후 종료.
    - INPUT 
        ip : onebox IP
        SMS 발송관련 = logger, mysql, smsID, subject, msg_copy, callback, smsUserList
    """

    def __init__(self, ip, logger, cfg, smsID, subject, msg, callback, smsUserList, saveSms ):
        threading.Thread.__init__(self)
        self.ip = ip
        self.logger = logger
        self.mysql = MySQLdb.connect( db=cfg['mysql_name'], user=cfg['mysql_user'], passwd=cfg['mysql_passwd'],
                                      host=cfg['mysql_addr'], port=cfg['mysql_port'] )
        self.smsID = smsID
        self.subject = subject
        # UTM 연결상태 DOWN 문자열을 공백으로 치환
        self.msg = msg.replace("UTM 연결상태 DOWN", "")
       
        self.callback = callback
        self.smsUserList = smsUserList
        self.saveSms = saveSms

    def __del__(self):
        if self.mysql != None :
            self.mysql.close()

    def SendSMS (self, status) :
        # 문자 발송
        str_status = "UP " if status == 0 else "DOWN "
        msg = self.msg + "TCP Ping " + str_status
        # redis 에 카운터 증가, Key 없으면 1로 리턴됨.
        sms_count = redis.incr (msg)
        # SMS 중복체크 유지기간 24시간.
        redis.expire (msg, 86400) 

        # 정상이면 [해 로 변경
        if status == 0 : 
            msg = msg.replace ('[발', '[해')
        else :
            if sms_count > 1 : 
                # [발  --> [발2회 .. [발3회 .. [발4회
                # 예)  [발4회/C]1. LTEPNF0310,본사,Daemon-vpn 상태 DOWN 
                msg = msg.replace ('[발', '[발%s회' % sms_count )

        logger.info( "== TcpPingCheck Send SMS : %s " % msg  )
        ret = self.saveSms( self.logger, self.mysql, self.smsID, self.subject, msg, self.callback, self.smsUserList )

    def run(self):
       
        logger.info( "== tcp ping check Start" )

        # 최초 1분 대기.
        sleep(60)

        port = 2233

        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)

        # 10분마다 문자전송, 첫회는 그냥 전송
        ten_minutes_later = datetime.now()
        try :
            # 1 시간 보다 크면 종료
            while now < one_hour_later:
                now = datetime.now()
                if now.strftime('%S') in ['00', '30'] :
                    status = 0
                    for i in range(2) :
                        # 0 정상, 0 <> 비정상
                        try :
                            status = self.tcpping ( self.ip, port)
                        except :
                            status = 1
                           
                        logger.info( "tcp ping check result : %s " % status)
                        
                        port_status = 'UP' if status == 0 else 'Down'
                        logger.info( "tcp ping check, ip : %s, Port : %s,  status : %s " % (self.ip , port, port_status ))

                        # 포트 정상이면 SMS 발송후 종료.
                        if status == 0 :
                            self.SendSMS(status)
                            return

                        # i 가 처음일때 30초 쉰다. 
                        if i==0 :
                            sleep(30)

                    # 처음엔 문자 발송, 그후 10분 마다 발송.
                    if now >= ten_minutes_later : 
                        ten_minutes_later = datetime.now() + timedelta(minutes=10)
                        self.SendSMS(status)

                sleep(1)

        except Exception, e:
            logger.fatal(e)
        

    def tcpping ( self, ip, port ) :
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a_socket.settimeout(5)
        location = (ip, port)
        result_of_check = a_socket.connect_ex(location)
        a_socket.close()    
        return result_of_check

class faultm :
    """
    - FUNC: 장애 정보 수신 처리 클래스
    - INPUT
        dbm(M): DB 연결 객체
        cfg(M): Orch-M 설정 정보
    """

    def __init__(self, dbm, cfg ):
        self.dbm = dbm
        self.cfg = cfg
        self.mysql = MySQLdb.connect( db=cfg['mysql_name'], user=cfg['mysql_user'], passwd=cfg['mysql_passwd'],
                              host=cfg['mysql_addr'], port=cfg['mysql_port'] )
        self.smsID = cfg['sms_id']
        self.callback = cfg['sms_callback']

    def __del__(self):
        if self.mysql != None :
            self.mysql.close()

    def updateRealtimeperfForSync(self, itemSeq, itemVal):
        realtimeperf_update = db_sql.UPDATE_REALTIMEPERF_FOR_SYSC(str(itemSeq), str(itemVal))
        self.dbm.execute(realtimeperf_update)

    def saveAndNoti( self, itemSeq, itemVal, alertGrade, isAlert, trig_name, dttm, isSync=False, isLineStatus=False, ArubaData={} ):
        """
        - FUNC: 장애 정보 저장 및 SMS/WEB 전송 처리
        - INPUT
            itemSeq(M): 감시 아이템 Seq
            itemVal(M): 측정 값
            alertGrade(M): 장애 등급(text)
            isAlert(M): 장애 발생/해제 여부
            trig_name(M): 장애 메시지 요약
            dttm(M): 장애 메시지 생성 시간
        - OUTPUT : 처리 결과(성공/실패)
            result: rrl_handler._ReqResult
        """
        FNAME = 'Save and Noti Alarm'
        _param = {'sms_user_id':self.smsID, 'item_seq':itemSeq, 'grade':alertGrade}

        # 18. 4.18 - lsh
        # CPU 값 소수 두자리로
        if "CPU" in trig_name:
            itemVal=round(float(itemVal), 2)

        if isAlert:
            if ArubaData is not None:
                curAlarmSeq = ArubaData['body']['item'][0]['id']

                rres = _notifyAlarm_Aruba(self.dbm, self.mysql, self.cfg, self.smsID, self.callback,
                                    itemSeq, itemVal, alertGrade, trig_name, dttm, curAlarmSeq, isLineStatus, ArubaData)
            else:
                rres = self.insertAlarm( itemSeq, itemVal, alertGrade, isAlert, trig_name, dttm )
                if rres.isFail()  :
                    rres.setParam(_param)
                    logger.error( rres.lF(FNAME) )
                    return rres

                # 2017.04.13 tb_realtimeperf update
                if itemVal != None or itemVal != '':
                    self.updateRealtimeperfForSync(itemSeq, itemVal)

                curAlarmSeq = rres.ret()
           
                rres = _notifyAlarm( self.dbm, self.mysql, self.cfg, self.smsID, self.callback,
                                 itemSeq, itemVal, alertGrade, trig_name, dttm, curAlarmSeq, isLineStatus )

            if rres.isFail():
                logger.error( rres.lF(FNAME) )
                return rres

            return rres
        else :
            if ArubaData is not None:
                rc = resolveChecker2(self, itemSeq, alertGrade, itemVal, isLineStatus, ArubaData)
                if rc.isFail():
                    logger.error(rc.lF(FNAME))
            else:
                if DEBUG_LOG_YN == 'y': logger.info("""[saveAndNoti_2] ==========> itemSeq : %s, alertGrade : %s, isAlert : %s, dttm : %s, isSync : %s, itemVal : %s
                """ % (str(itemSeq), str(alertGrade), str(isAlert), str(dttm), str(isSync), str(itemVal)))
                rres = self.resolveAlarm( itemSeq, alertGrade, isAlert, dttm, isSync )
                if rres.isFail() :
                    rres = rres.setParam(_param)
                    logger.error( rres.lF(FNAME) )
                    return rres

                # 2017.04.13 tb_realtimeperf update
                if itemVal != None or itemVal != '':
                    self.updateRealtimeperfForSync(itemSeq, itemVal)

                if rres.ret() > 0 :
                    # rc = resolveChecker(self.cfg, itemSeq, self.smsID, self.callback)
                    # rc.start()
                    rc = resolveChecker2(self, itemSeq, alertGrade, itemVal, isLineStatus)
                    if rc.isFail():
                        logger.error(rc.lF(FNAME))

            return rrl.rSc(None, None, _param)


    def insertAlarm( self, itemSeq, itemVal, alertGrade, isAlert, trig_name, dttm ):
        """
        - FUNC: 장애 발생 정보 저장 및 SMS/WEB 전송 처리
        - INPUT
            itemSeq(M): 감시 아이템 Seq
            itemVal(M): 측정 값
            alertGrade(M): 장애 등급(text)
            isAlert(M): 장애 발생/해제 여부
            trig_name(M): 장애 메시지 요약
            dttm(M): 장애 메시지 생성 시간
        - OUTPUT : 처리 결과(성공/실패)
            result: rrl_handler._ReqResult
        """
        FNAME = 'Insert Alarm'
        try:
            if alertGrade < 2 :
                rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Invalid Alarm Grade', None, {'trig_name':trig_name, 'grade':alertGrade})
                logger.warning( rres.lL(FNAME) )
                return rres

            ## 기존 알람 장애 등급 일괄 업데이트
            alarm_update = db_sql.UPDATE_CURR_ALARM_SYNC( str(itemSeq), str('등급 변경'), sa.getState(0) )
            self.dbm.execute( alarm_update )
            self.dbm.execute( db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE() )

            ## 서비스 넘버 불러오기
            tmp = self.dbm.select( db_sql.GET_SERVICE_NUMBER_BY_ITEMSEQ(itemSeq) )
            if len(tmp) > 0:
                service_number = tmp[0]['service_number']
            else:
                service_number = None

            ## 신규 장애 추가
            alert_insert = db_sql.INSERT_CURR_ALARM( str(dttm), itemVal, sa.getGrade(alertGrade), sa.getState(isAlert), trig_name, str(itemSeq), service_number)
            currSeq = self.dbm.execute( alert_insert, True )
            if currSeq == None :
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, None, None, {'item_seq':itemSeq, 'grade':alertGrade})
                logger.error( rres.lF(FNAME) )
                web_api.notiInternalError(rres)
                return rres

            hist_insert = db_sql.INSERT_HIST_ALARM(currSeq)
            histSeq = self.dbm.execute( hist_insert )
            if histSeq == None :
                logger.warning(rrl.rFa(None, rrl.RS_FAIL_DB, 'CurrAlarm Copy Error', None, hist_insert).lF(FNAME))
                ret = self.dbm.execute( db_sql.UPDATE_HIST_ALARM_FOR_SYNC_INSERT() )
                if ret == None :
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Curr-Hist Alarm Sync Error', None, {'item_seq':itemSeq, 'grade':alertGrade})
                    logger.error( rres.lF(FNAME) )
                    _notifyAlarmToWeb(itemSeq, alertGrade, isAlert, dttm, trig_name, itemVal)
                    return rres
                else:
                    logger.info( rrl.rSc(None, {'new_alarm_sync_cnt':ret}, None).lL(FNAME) )

            _notifyAlarmToWeb(itemSeq, alertGrade, isAlert, dttm, trig_name, itemVal)
            return rrl.rSc(None, currSeq, None)
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'item_seq':itemSeq, 'grade':alertGrade})
            logger.error( rres.lF(FNAME) )
            logger.fatal(e)
            return rres

    def resolveAlarm( self, itemSeq, alertGrade, isAlert, dttm, isSync=False):
        """
        - FUNC: 장애 해제 정보 저장 및 SMS/WEB 전송 처리
        - INPUT
            itemSeq(M): 감시 아이템 Seq
            alertGrade(M): 장애 등급(text)
            isAlert(M): 장애 발생/해제 여부
            dttm(M): 장애 메시지 생성 시간
        - OUTPUT : 처리 결과(성공/실패)
            result: rrl_handler._ReqResult
        """
        FNAME = 'Resolve Alarm'
        try:
            resolveMsg = '자동 조치'
            if isSync :
                resolveMsg = '동기화'
            alarm_update = db_sql.UPDATE_CURR_ALARM_RESOLVE( str(dttm), str(resolveMsg), sa.getState(0),
                                                             str(itemSeq), sa.getGrade(alertGrade))

            ret = self.dbm.execute( alarm_update )
            if ret < 1 :
                rres = rrl.rFa(None, rrl.RS_NO_DATA, 'No Alarm Info', ret, {'item_seq':itemSeq, 'grade':alertGrade})
                #logger.warning(rres.lL(FNAME))
            else:
                hist_alarm = db_sql.UPDATE_HIST_ALARM_RESOLVE(str(dttm), str(resolveMsg), sa.getState(0),
                                                              str(itemSeq), sa.getGrade(alertGrade))
                histRet = self.dbm.execute( hist_alarm )
                if histRet < 1 :
                    logger.warning( rrl.rFa(None, rrl.RS_FAIL_DB, 'Update Resolve HistAlarm Error', None, hist_alarm).lF(FNAME) )
                    histRet = self.dbm.execute( db_sql.UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE() )
                    if histRet == None :
                        _notifyAlarmToWeb(itemSeq, alertGrade, isAlert, dttm)
                        rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Sync Alarm Resolve Error', None, {'item_seq':itemSeq, 'grade':alertGrade})
                        logger.error( rres.lF(FNAME))
                        return rres
                    else:
                        logger.info( rrl.rSc(None, {'resolve_alarm_sync_cnt':histRet}, None).lL(FNAME) )

                _notifyAlarmToWeb(itemSeq, alertGrade, isAlert, dttm)

            return rrl.rSc(None, ret, {'item_seq':itemSeq, 'grade':alertGrade})
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'item_seq':itemSeq, 'grade':alertGrade})
            logger.error( rres.lF('Resolve Alarm') )
            logger.fatal(e)
            return rres

class alarmAckManager(threading.Thread):
    """
    - FUNC: 장애 인지 처리 후 인지 유지 시간이 넘어도 장애 해결이 되지 않으면 인지 해제시키는 스케줄러
    - INPUT
        cfg(M): Orch-M 설정 정보
    """

    def __init__(self, cfg ):
        threading.Thread.__init__(self)
        self.period = cfg['fault_ack_chk']
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        self.dbm = dbManager( 'orchm-alarm', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                    cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )

    def run(self):

        while True:
            try:

                updateAckSql = db_sql.UPDATE_CURR_ALARM_ACK_RELEASE()
                ret = self.dbm.execute( updateAckSql )
                self.dbm.execute( db_sql.UPDATE_HIST_ALARM_SYNC_ACK() )
                if ret > 0 :
                    rres = rrl.rFa(None, rrl.RS_TIMEOUT, 'Alarm Ack Release', ret, None)
                    logger.warning( rres.lL('Alarm Ack Check') )

                sleep( self.period )
            except Exception, e:
                rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
                logger.error( rres.lF('Alarm Ack Check') )
                logger.fatal(e)
                sleep( self.period )

class curAlarmRemover(threading.Thread):
    """
    - FUNC: tb_curalarm 테이블에서 하루 지난 항목을 제거
    - INPUT
        cfg(M): Orch-M 설정 정보
        itemSeq(M): 감시 아이템 Seq
        smsID(M): SMS 메시지 ID
        callback(M): SMS 회신 번호
    """

    def __init__(self, cfg ):
        threading.Thread.__init__(self)
        self.cfg = cfg

    def run(self):
        while True:
            try:
                connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(self.cfg)
                dbm = dbManager( 'orchm-fault-chk', self.cfg['db_name'], self.cfg['db_user'], self.cfg['db_passwd'],
                            self.cfg['db_addr'], int(self.cfg['db_port']), connCnt=connNum, _logger=logger )

                uSyncCnt = dbm.execute( db_sql.UPDATE_HIST_ALARM_FOR_SYNC_ALL() )
                iSyncCnt = dbm.execute( db_sql.INSERT_HIST_ALARM_FOR_SYNC_ALL() )
                currCnt = dbm.execute( db_sql.REMOVE_CURR_ALARM() )
                rres = rrl.rSc(None, {'remove_curr_alarm':currCnt, 'update_hist_alarm':uSyncCnt, 'insert_hist_alarm':iSyncCnt}, None)
                logger.info( rres.lS('CurrAlarm Remove') )
                dbm = None
            except Exception, e:
                rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
                logger.error( rres.lF('CurrAlarm Remove') )
                logger.fatal(e)
                dbm = None
            sleep(3600)



NOTI = 'FAULT-NOTI'
REFRESH = 'FAULT-REFRESH'
TEST = 'FAULT-TEST'

class FaultHandler(RequestHandler):
    """
    - FUNC: 장애 메시지 수신 API 생성 및 처리하는 클래스
    - INPUT
        opCode(M): 요청 서비스 이름
        cfg(M): Orch-M 설정 정보
    """

    def initialize(self, opCode, cfg):
        self.opCode = opCode
        self.cfg = cfg
        self.gVar = cfg['gVar']
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        self.dbm = dbManager( 'orchm-fault', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                    cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )
        self.mysqlDB = MySQLdb.connect( db=cfg['mysql_name'], user=cfg['mysql_user'], passwd=cfg['mysql_passwd'],
                              host=cfg['mysql_addr'], port=cfg['mysql_port'] )
        self.faultm = faultm( self.dbm, cfg )

    def post(self):
        reqdata = self.request.body
        self.src = self.request.remote_ip
        # logger.info( rrl.lRReq(self.src, 'FaultHandler', self.opCode, None) )
        # fLogger.info( rrl.lRReq(self.src, 'FaultHandler', self.opCode, reqdata) )
        # logger.info( rrl.lRReq(self.src, 'FaultHandler', self.opCode, reqdata) )
        apiLogger.info( rrl.lRReq(self.src, 'FaultHandler', self.opCode, reqdata) )

        if self.opCode == NOTI:
            return self.noti()
        elif self.opCode == REFRESH:
            return self.refresh()
        elif self.opCode == TEST:
            return self.test()

    def noti(self):
        """
        - FUNC: 장애 메시지 수신 API 처리
        """
        self.write( {"result":"ok"} )
        self.flush()

        try:
            # 22. 6.15 - lsh
            # SNMP 개발중 아래 key 에서 JSON 변환 오류 발생
            # "key": "vpnstatus.sh["mokforti.OB1"]",
            jstr = self.request.body
            jstr = jstr.replace('.sh["', '.sh(')
            jstr = jstr.replace('"]', ')' )
            
            reqdata = json.loads( jstr )

            ArubaData = None

            # aruba 분기
            if reqdata.get('to') == 'aruba':
                isSucc, ret = True, {}

                ret['itemSeq'] = reqdata.get('body').get('item')[0]['id']
                ret['alertGrade'] = int(reqdata['body']['trigger']['grade_code'])

                ret['itemVal'] = 0
                ret['isAlert'] = True
                itemStatus = reqdata['body']['trigger']['status_code']
                if int(itemStatus) == 0:
                    ret['itemVal'] = 1
                    ret['isAlert'] = False

                ret['trig_name'] = ""
                strDate = reqdata['body']['event']['date'] + " " + reqdata['body']['event']['time']
                dttm = datetime.strptime(strDate, "%Y.%m.%d %H:%M:%S")
                ret['dttm'] = dttm
                ret['isLineStatus'] = False

                ArubaData = reqdata
            else:
                # logger.debug("#################  fault noti start    #################################")
                # logger.debug(" noti reqdata : %s " % reqdata )

                isSucc, ret = zb.faultParsing( reqdata, self.dbm, logger )

            # logger.debug(" isSucc = %s : ret = %s " % (str(isSucc), str(ret)))

            if not isSucc :
                rres = rrl.rFa(None, rrl.RS_FAIL_ZB_OP, 'Fault MSG Parsing Error', ret, reqdata)
                logger.error( rres.lF(self.opCode) )
                return
            if ret == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_ZB_OP, 'Ignore or Pass Fault MSG', ret, reqdata)
                logger.warning( rres.lL(self.opCode) )
                return

            # logger.debug('ret = %s' % str(ret))

            """
            2016-08-10
            장애 문자 발송시 대역폭 사용량은 MBps 기준으로 환산하여 발송하도록 수정
            자빅스에서 unit 단위를 전송해 주지 않기 때문에 무엇에 대한 장애인지 식별할 필요가 있다.
            DB를 조회하여 장애 유형이 무엇인지 판별하고 unit 단위가 bps 인 경우에는 Mbps 로 환산하도록 한다.
            """
            # qry = """
            # SELECT unit FROM tb_moniteminstance WHERE moniteminstanceseq = '%s'
            # """ % str(ret['itemSeq'])
            # unit = self.dbm.select(qry)
            # if unit[0]['unit'] == "bps":
            #     ret['itemSeq'] = ret['itemSeq'] / 1000 # 단위는 1,000 으로 나눔

            # 발송 장애 등급 정보를 읽고 해당 장애 등급만 문자 발송


            # 20. 6.25 - lsh
            # 회선상태 인자 추가.  isLineStatus
            rres = self.faultm.saveAndNoti( ret['itemSeq'], ret['itemVal'], ret['alertGrade'],
                                     ret['isAlert'], ret['trig_name'], ret['dttm'], False, ret['isLineStatus'], ArubaData=ArubaData )
            if rres.isFail() :
                logger.error( rres.lF(self.opCode) )
                return
        except (ValueError, TypeError), e:
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            web_api.notiInternalError( rres.toWebRes() )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            web_api.notiInternalError( rres.toWebRes() )

    def refresh(self):
        """
        - FUNC: ZB 장애 데이터 sync
        """
        try:
            rres = refreshFault(self.dbm, self.cfg)
            if rres.isFail() :
                logger.error( rres.ltF(self.opCode) )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            web_api.notiInternalError( rres.toWebRes() )

        self.write( rres.toWebRes() )
        self.flush()

    def test(self):
        try:
            reqdata = json.loads( self.request.body )
            ret = sms_mng.saveSms( logger, self.mysqlDB, 'test1onebox', reqdata['subject'], reqdata['msg'], '0428708729', reqdata['user_list']  )
        except (ValueError, TypeError):
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            web_api.notiInternalError( rres.toWebRes() )
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            web_api.notiInternalError( rres.toWebRes() )

        self.write( {"result":str(ret)} )
        self.flush()

    def __del__(self):
        self.mysqlDB.close()


def url( _cfg ):
    """
    - FUNC: FaultManager의 URL 및 API Handler, 인자 관리
    - INPUT
        _cfg(M): Orch-M 설정 정보
    - OUTPUT : API에 대한 URL, Handler, 인자 리스트
    """
    url = [ ('/fault', FaultHandler, dict(opCode=NOTI, cfg=_cfg)),
            ('/fault/refresh', FaultHandler, dict(opCode=REFRESH, cfg=_cfg)),
            ('/fault/test', FaultHandler, dict(opCode=TEST, cfg=_cfg))
            ]
    return url


def onStart(cfg):
    """
    - FUNC: FaultManager 시작 시 실행해야할 기능 구현
    - INPUT
        cfg(M): Orch-M 설정 정보
    """
    ## SMS 전송 체크
    try:
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        dbm = dbManager( 'orchm-fault', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                        cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )

        ret = dbm.select( db_sql.GET_SMSSTATUS_FOR_HA() )
        for smsInfo in ret:
            curAlarmSeq = smsInfo['curalarmseq']
            smsMsgID = smsInfo['smsmsgid']
            smsUserList = [{ 'phone_num': str(smsInfo['userhpnum']).replace('-', ''), 'smsuserseq':smsInfo['smsuserseq'] }]
            tmp = smsRecvChecker( cfg, curAlarmSeq, smsMsgID, smsUserList)
            tmp.start()
            rres = rrl.rSc(None, None, smsInfo)
            logger.info( rres.lS('OnStart SMS-Report Checker') )
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF('OnStart SMS-Report Checker'))
        logger.fatal(e)

    ## 장애 데이터 통기화
    try:
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        dbm = dbManager( 'orchm-fault', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                        cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )

        rres = refreshFault(dbm, cfg)
        if rres.isSucc() :
            logger.info( rres.lS('OnStart Alarm-Sync') )
        else:
            logger.error( rres.lF('OnStart Alarm-Sync') )
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error(rres.lF('OnStart Alarm-Sync'))
        logger.fatal(e)

    return
