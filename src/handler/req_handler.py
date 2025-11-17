#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''

from util import db_sql
from handler import rrl_handler as rrl

TITLE = 'orchm'

import logging
logger = logging.getLogger(TITLE)


## status
DOING = 'DOING'
DONE = 'DONE'
FAIL = 'FAILED'

TEST_IP= 'localhost'

def saveRequest( dbm, src, tid, reqType, _reqBody, status, state, progress=0 ):
    """
    - FUNC: 요청 내용 저장
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
        reqType(M): 요청 서비스 타입
        _reqBody(M): 요청 파라미터
        status(M): 요청 처리 과정/단계
        state(M): 각 과정의 진행 상태
        progress(O): 요청 진행률
    - OUTPUT: 저장 성공 여부(True/False)
    """
    if src==TEST_IP: return True
    
    reqBody = str(_reqBody).replace("""'""", '"')
    ret = dbm.execute( db_sql.INSERT_REQ( src, str(tid), reqType, reqBody, status, state, str(progress) ) )
    if ret == None or ret != 1 :
        logger.warning( 'Save Request Error' )
        return False
    return True

def saveRequestStatus( dbm, src, tid, status, state, progress ):
    """
    - FUNC: 요청 status 변경 저장
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
        status(M): 요청 처리 과정/단계
        state(M): 각 과정의 진행 상태
        progress(M): 요청 진행률
    - OUTPUT: 저장 성공 여부(True/False)
    """
    if src==TEST_IP: return True
    
    ret = dbm.execute( db_sql.UPDATE_REQ_STATUS(src, tid, status, state, progress) )
    if ret == None or ret < 1:
        logger.warning( 'Save Request Status Error' )
        return False
    return True

def saveRequestState( dbm, src, tid, state, progress ):
    """
    - FUNC: 요청 status의 진행상태 변경 저장
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
        state(M): 각 과정의 진행 상태
        progress(M): 요청 진행률
    - OUTPUT: 저장 성공 여부(True/False)
    """
    if src==TEST_IP: return True
    
    ret = dbm.execute( db_sql.UPDATE_REQ_STATE(src, tid, state, progress) )
    if ret == None or ret < 1:
        logger.warning( 'Save Request State Error' )
        return False
    return True

def saveRequestProg( dbm, src, tid, progress ):
    """
    - FUNC: 요청 진행률 변경 저장
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
        progress(M): 요청 진행률
    - OUTPUT: 저장 성공 여부(True/False)
    """
    if src==TEST_IP: return True
    
    ret = dbm.execute( db_sql.UPDATE_REQ_PROG(src, tid, progress) )
    if ret == None or ret < 1:
        logger.warning( 'Save Request Progress Error' )
        return False
    return True

def saveRequestComplete( dbm, src, tid ):
    """
    - FUNC: 요청 완료 저장
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
    - OUTPUT: 저장 성공 여부(True/False)
    """
    if src==TEST_IP: return True
    
    ret = dbm.execute( db_sql.UPDATE_REQ_COMPLETE(src, tid, 'SUCC', 'COMPLETE', 'COMPLETE') )
    if ret == None or ret < 1:
        logger.warning( 'Save Request Complete Result Error' )
        return False
    return True

def saveRequestFail( dbm, src, tid, error ):
    """
    - FUNC: 요청 실패 저장
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
        error(M): 요청 실패 원인 저장
    - OUTPUT: 저장 성공 여부(True/False)
    """
    if src==TEST_IP: return True
    
    ret = dbm.execute( db_sql.UPDATE_REQ_FAIL(src, tid, 'FAIL', str(error).replace("'", '"')) )
    if ret == None or ret < 1:
        logger.warning( 'Save Request Fail Result Error' )
        return False
    return True

## status, progress
def getRequestStatus( dbm, src, tid, opCode ):
    """
    - FUNC: 요청 진행 상태 반환
    - INPUT
        dbm(M): DB 연결 객체
        src(M): 요청 호스트 IP(Test IP 등록된 것은 저장하지 않음)
        tid(M): 요청 TID
        opCode(M): 요청 서비스 코드
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    if src==TEST_IP: return True
    
    _param = {'tid':tid, 'opcode':opCode, 'src':src}
    
    reqStatus = dbm.select( db_sql.GET_REQSTATUS( src, tid ) )
    if reqStatus == None or len(reqStatus) < 1:
        if reqStatus == None:
            resCode = rrl.RS_FAIL_DB
        else:
            resCode = rrl.RS_NO_DATA
        return rrl.rFa(tid, resCode, None, reqStatus, _param)
    elif len(reqStatus) > 1:
        return rrl.rFa(tid, rrl.RS_DUPLICATE_DATA, 'Duplicated TID', reqStatus, _param)
    
    ret = { 'tid':tid }
    if reqStatus[0]['result'] == None or reqStatus[0]['result'] == '':
        ret['status'] = DOING
        ret['progress'] = reqStatus[0]['progress']
    elif reqStatus[0]['result'] == 'SUCC' :
        ret['status'] = DONE
        ret['progress'] = reqStatus[0]['progress']
    else :
        ret['status'] = FAIL
        ret['progress'] = reqStatus[0]['progress']
        ret['error'] = reqStatus[0]['error']
        
    return rrl.rSc(tid, ret, _param)
    