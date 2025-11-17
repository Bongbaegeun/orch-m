#-*- coding: utf-8 -*-
import httplib
import logging
TITLE = 'orchm'
logger = logging.getLogger(TITLE)

### res.body의 status_code 로 결과 확인, sc는 200
### error일 경우 error:{code, type, description(UI에서 보여지는 값)}
    ## http status code: 2xx 성공, 4xx 실패(클라이언트 fail), 5xx 실패(서버 fail)
    ## 나중에 .. ob-specific status code: 7xx
## 에러코드 res 헤더에 넣을 수 있나.


class MonResp():
    def __init__(self, tid, ret, param, errCode=None, err=None):
        self.tid = tid
        self.ret = ret
        self.param = param
        self.errCode = errCode
        self.err = err
    def tid(self):
        return self.tid
    def ret(self):
        return self.ret
    def param(self):
        return self.param
    def errCode(self):
        return self.errCode
    def err(self):
        return self.err
    def __str__(self):
        if self.errCode == None:
            ret = "ret=%s:: param=%s:: tid=%s"%(str(self.ret), str(self.param), str(self.tid))
        else:
            ret = "errCode=%s:: err=%s:: ret=%s:: param=%s:: tid=%s"%(str(self.errCode), str(self.err), str(self.ret), str(self.param), str(self.tid))
        return ret

def eFail( reqName, monResp ):
    msg = "FA:: %s:: %s"%(reqName, str(monResp))
    logger.error(msg)

def eSucc( reqName, monResp ):
    msg = "SC:: %s:: %s"%(reqName, str(monResp))
    logger.info(msg)

def eInfo( reqName, monResp ):
    msg = "--:: %s:: %s"%(reqName, str(monResp))
    logger.info(msg)

def eWarn( reqName, monResp):
    msg = "--:: %s:: %s"%(reqName, str(monResp))
    logger.warning(msg)

def eDebg( reqName, info):
    msg = "--:: %s:: %s"%(reqName, str(info))
    logger.debug(msg)



def eFa( tid, errCode, err, ret, param ):
    """
    - FUNC: Orch-M 내부 요청 에러 형식으로 변환
    - INPUT
        tid(M): 요청 받은 TID
        errCode(M): 에러 코드
        err(M): 에러 발생 원인
        ret(M): 실행 반환값
        param(M): 요청 파라미터
    - OUTPUT
        isSucc(M): 변환 성공/실패
        result(M): 변환 결과(에러)
    """
    return False, MonResp(tid, ret, param, errCode, err)

def eSc( tid, ret, param ):
    """
    - FUNC: Orch-M 내부 요청 성공 형식으로 변환
    - INPUT
        tid(M): 요청 받은 TID
        ret(M): 실행 반환값
        param(M): 요청 파라미터
    - OUTPUT
        isSucc(M): 변환 성공/실패
        result(M): 변환 결과
    """
    return True, MonResp(tid, ret, param)



def getErr( code, msg, req=None ):
    if req == None:
        return { 'result':'FA', 'error':{'name':code, 'message': str(msg)} }
    else:
        return { 'result':'FA', 'error':{'name':code, 'message': str(msg), 'req':req} }

def getOK( msg=None ):
    msg = ( lambda x : x if msg != None else '' )(msg)
    return { 'result':'SC', 'response':msg }

def isSucc( ret ):
    try:
        if ret == None or ret.has_key('error'):
            return False
        else:
            return True
    except Exception:
        return False

## NAME
INVALID_PARAM = 'Invalid Parameter'
NO_PARAM = 'No Parameter'
INVALID_DATA = 'Invalid Data'
NO_DATA = 'No Data'
DUPLICATE_DATA = 'Duplicated Data'
DATA_INUSE = "Data In Use"
EXCP = 'Exception'
OP_FAIL = 'Operation Fail'
ZB_OP_FAIL = 'ZB Operation Fail'
DB_FAIL = 'DB Operation Fail'
HTTP_RES_ERR = 'HTTP Response Error'
ZBAPI_ERR = 'Zabbix Server Manager API Error'
UNKNOWN_REQ = 'Unknown Request'
SHELL_FAIL = 'Shell EXEC FAIL'
NO_IMPL = 'Not Implement'

## Message

def getHttpErr( requestHandler, _ret ):
    eType = _ret['error']['name']
    if eType == INVALID_PARAM or eType == NO_PARAM or eType == INVALID_DATA :
        httpCode = httplib.BAD_REQUEST
    elif eType == NO_DATA:
        httpCode = httplib.NOT_FOUND
    elif eType == DUPLICATE_DATA:
        httpCode = httplib.CONFLICT
    elif eType == DATA_INUSE:
        httpCode = httplib.FAILED_DEPENDENCY
    elif eType == EXCP or eType == OP_FAIL or eType == ZB_OP_FAIL or eType == DB_FAIL or eType == HTTP_RES_ERR or eType == ZBAPI_ERR or eType == SHELL_FAIL:
        httpCode = httplib.INTERNAL_SERVER_ERROR
    elif eType == UNKNOWN_REQ :
        httpCode == httplib.NOT_IMPLEMENTED
    elif eType == NO_IMPL :
        httpCode == httplib.NOT_IMPLEMENTED
    else :
        httpCode == httplib.INTERNAL_SERVER_ERROR
    
    requestHandler.set_status(httpCode)
    ret = {}
    ret['code'] = httpCode
    ret['type'] = httplib.responses[httpCode]
    ret['description'] = _ret['error']['message']
    return ret

def getOrchFResult( requestHandler, ret ):
    if ret['result'] == 'FA':
        return getHttpErr(requestHandler, ret)
    else:
        requestHandler.set_status( httplib.OK )
        return ret['response']







