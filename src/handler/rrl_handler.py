#-*- coding: utf-8 -*-

#############
## Request, Result, Log Manager
###############

import httplib

### res.body의 status_code 로 결과 확인, sc는 200
### error일 경우 error:{code, type, description(UI에서 보여지는 값)}
    ## http status code: 2xx 성공, 4xx 실패(클라이언트 fail), 5xx 실패(서버 fail)
    ## 나중에 .. ob-specific status code: 7xx
## 에러코드 res 헤더에 넣을 수 있나.



## Result Code
RS_SUCC = 0
RS_INVALID_PARAM = -1
RS_INVALID_DATA = -2
RS_NO_PARAM = -10
RS_NO_DATA = -11
RS_DUPLICATE_DATA = -21
RS_ALREADY_EXIST = -22
RS_INUSE_DATA = -31
RS_EXCP = -41
RS_FAIL_OP = -51
RS_FAIL_ZB_OP = -52
RS_FAIL_DB = -53
RS_FAIL_SHELL = -54
RS_API_ZBS_ERR = -61
RS_API_OBA_ERR = -62
RS_API_PRV_ERR = -63
RS_API_WEB_ERR = -64
RS_API_SMS_ERR = -65
RS_UNKNOWN_REQ = -71
RS_UNKNOWN_PARAM = -72
RS_UNSUPPORTED_FUNC = -81
RS_UNSUPPORTED_PARAM = -82
RS_TIMEOUT = -91
RS_IN_PROGRESS = -92
RS_HTTP_RES_ERR = -101

def resStr( resCode ):
    """
    - FUNC: 결과코드를 텍스트로 변환
    - INPUT
        resCode(M): 결과 코드
    - OUTPUT
        result: 결과 코드 텍스트
    """
    if resCode == RS_SUCC : return 'SUCC'
    elif resCode == RS_INVALID_PARAM : return 'INVALID_PARAM'
    elif resCode == RS_INVALID_DATA : return 'INVALID_DATA'
    elif resCode == RS_NO_PARAM : return 'NO_PARAM'
    elif resCode == RS_NO_DATA : return 'NO_DATA'
    elif resCode == RS_DUPLICATE_DATA : return 'DUPLICATE_DATA'
    elif resCode == RS_ALREADY_EXIST : return 'ALREADY_EXIST'
    elif resCode == RS_INUSE_DATA : return 'INUSE_DATA'
    elif resCode == RS_EXCP : return 'EXCP'
    elif resCode == RS_FAIL_OP : return 'FAIL_OP'
    elif resCode == RS_FAIL_ZB_OP : return 'FAIL_ZB_OP'
    elif resCode == RS_FAIL_DB : return 'FAIL_DB'
    elif resCode == RS_FAIL_SHELL : return 'FAIL_SHELL'
    elif resCode == RS_API_ZBS_ERR : return 'API_ZBS_ERR'
    elif resCode == RS_API_OBA_ERR : return 'API_OBA_ERR'
    elif resCode == RS_API_PRV_ERR : return 'API_PRV_ERR'
    elif resCode == RS_API_WEB_ERR : return 'API_WEB_ERR'
    elif resCode == RS_API_SMS_ERR : return 'API_SMS_ERR'
    elif resCode == RS_UNKNOWN_REQ : return 'UNKNOWN_REQ'
    elif resCode == RS_UNSUPPORTED_FUNC : return 'UNSUPPORTED_FUNC'
    elif resCode == RS_UNSUPPORTED_PARAM : return 'UNSUPPORTED_PARAM'
    elif resCode == RS_TIMEOUT : return 'TIMEOUT'
    elif resCode == RS_IN_PROGRESS : return 'IN_PROGRESS'
    elif resCode == RS_HTTP_RES_ERR : return 'HTTP_RES_ERR'
    else : return 'UNKNOWN_ERR_CODE'


class _ReqResult():
    """
    - FUNC: Orch-M의 처리 결과 반환 클래스
    - INPUT
        tid(M): 요청 TID
        ret(M): 요청 결과 값
        param(M): 요청 파라미터
        resCode(M): 요청 결과 코드
        err(M): 에러 설명
    """
    def __init__(self, tid, ret, param, resCode=RS_SUCC, err=None, msg=None):
        self._tid = tid
        self._ret = ret
        self._param = param
        self._resCode = resCode
        self._err = []
        if err != None :
            self._err.append(err)
        self._msg = msg
        self._reqName = []
    def tid(self):
        return self._tid
    def ret(self):
        return self._ret
    def param(self):
        return self._param
    def resCode(self):
        return self._resCode
    def resCodeStr(self):
        return resStr(self._resCode)
    def err(self):
        return self._err
    def errStr(self):
        errTxt = ''
        isFisrt = True
        for err in self._err:
            if isFisrt :
                errTxt = str(err)
                isFisrt = False
            else:
                errTxt += ( ' > ' + str(err) )
        return errTxt
    def msg(self):
        return self._msg
    
    def isSucc(self):
        if self._resCode >= RS_SUCC:
            return True
        else:
            return False
    
    def isFail(self):
        return not self.isSucc()
    
    def eqErr(self, resCode):
        return self._resCode == resCode
    
    def setParam(self, param):
        self._param = param
        return self
    
    def setMsg(self, msg):
        self._msg = msg
        return self
    
    def setErr(self, err):
        self._err.append(err)
        return self
    
    def __str__(self):
        if self._resCode >= RS_SUCC:
            ret = "msg=%s:: ret=%s:: param=%s:: tid=%s"%(str(self._msg), str(self._ret), str(self._param), str(self._tid))
        else:
            ret = "resCode=%s:: err=%s:: ret=%s:: param=%s:: tid=%s"%(resStr(self._resCode), self.errStr(), str(self._ret), str(self._param), str(self._tid))
        return ret
    
    def lF( self, reqName ):
        """
        - FUNC: 실패 로그 텍스트 반환
        - INPUT
            reqName(M): 로그 타이틀
        - OUTPUT : 로그 텍스트 반환
        """
        self._reqName.append( reqName )
        return "FA:: %s:: %s"%(str(reqName), str(self))

    def lS( self, reqName ):
        """
        - FUNC: 성공 로그 텍스트 반환
        - INPUT
            reqName(M): 로그 타이틀
        - OUTPUT : 로그 텍스트 반환
        """
        self._reqName.append( reqName )
        return "SC:: %s:: %s"%(str(reqName), str(self))
    
    def lL( self, reqName ):
        """
        - FUNC: 일반 로그 텍스트 반환
        - INPUT
            reqName(M): 로그 타이틀
        - OUTPUT : 로그 텍스트 반환
        """
        self._reqName.append( reqName )
        return "--:: %s:: %s"%(str(reqName), str(self))
    
    def _lTrace(self, lastReqName):
        """
        - FUNC: 거쳐간 메소드 Trace
        - INPUT
            reqName(M): 로그 타이틀
        - OUTPUT : 로그 텍스트 반환
        """
        if len(self._reqName) > 0 :
            trace = str(lastReqName)
            for tmp in self._reqName :
                trace = trace + ' > %s'%str(tmp)
            return ':: LogTrace=' + trace
        else:
            return ''
        
    def ltF(self, reqName):
        """
        - FUNC: 실패 Trace 용 로그 텍스트 반환
        - INPUT
            reqName(M): 로그 타이틀
        - OUTPUT : 로그 텍스트 반환
        """
        lastLog = "FA:: %s:: %s"%(str(reqName), str(self))
        return lastLog + self._lTrace(reqName)
    
    def ltL(self, reqName):
        """
        - FUNC: 일반 Trace 용 로그 텍스트 반환
        - INPUT
            reqName(M): 로그 타이틀
        - OUTPUT : 로그 텍스트 반환
        """
        lastLog = "--:: %s:: %s"%(str(reqName), str(self))
        return lastLog + self._lTrace(reqName)
    
    def toHttpErr( self, requestHandler ):
        """
        - FUNC: HTTP 에러 코드로 변환
        - INPUT
            requestHandler(M): HTTP 요청 Handler 객체
        - OUTPUT : HTTP 에러 코드 변환 결과
            code: HTTP 에러 코드
            type: HTTP 에러 코드 이름
            description: 에러 설명 
        """
        eCode = self._resCode
        if eCode == RS_INVALID_PARAM or eCode == RS_NO_PARAM or eCode == RS_INVALID_DATA :
            httpCode = httplib.BAD_REQUEST
        elif eCode == RS_NO_DATA:
            httpCode = httplib.NOT_FOUND
        elif eCode == RS_DUPLICATE_DATA or eCode == RS_ALREADY_EXIST:
            httpCode = httplib.CONFLICT
        elif eCode == RS_INUSE_DATA:
            httpCode = httplib.FAILED_DEPENDENCY
        elif (eCode == RS_EXCP or eCode == RS_FAIL_OP or eCode == RS_FAIL_ZB_OP or eCode == RS_FAIL_DB 
              or eCode == RS_HTTP_RES_ERR or eCode == RS_API_ZBS_ERR or eCode == RS_FAIL_SHELL):
            httpCode = httplib.INTERNAL_SERVER_ERROR
        elif eCode == RS_UNKNOWN_REQ :
            httpCode = httplib.NOT_IMPLEMENTED
        elif eCode == RS_UNSUPPORTED_FUNC or eCode == RS_UNSUPPORTED_PARAM :
            httpCode = httplib.NOT_IMPLEMENTED
        else :
            httpCode = httplib.INTERNAL_SERVER_ERROR
        
        requestHandler.set_status(httpCode)
        ret = {}
        ret['code'] = httpCode
        ret['type'] = httplib.responses[httpCode]
        ret['description'] = self.errStr()
        return ret
    
    def toOrchFRes( self, requestHandler ):
        """
        - FUNC: Orch-F 형식으로 결과 변환
        - INPUT
            requestHandler(M): HTTP 요청 Handler 객체
        - OUTPUT : Orch-F 변환 결과
        """
        if self.isSucc():
            requestHandler.set_status( httplib.OK )
            return self._ret
        else:
            return self.toHttpErr(requestHandler)

    def toWebRes(self, returnReq=False):
        """
        - FUNC: WEB-UI 형식으로 결과 변환
        - INPUT
            returnReq(O): 에러 시 요청 파라미터의 반환 여부
        - OUTPUT : WEB-UI 반환 결과
            result(M): SC/FA
            response(O): 성공 결과
            error(O): 에러 표시
                name(M): 에러 코드 이름
                message(M): 에러 내용
                req(O): 요청 파라미터
        """
        ret = {}
        if self.isSucc():
            ret['result'] = 'SC'
            ret['response'] = self._ret
        else:
            ret['result'] = 'FA'
            ret['error'] = { 'name':resStr(self._resCode), 'message': self.errStr() }
            if returnReq:
                ret['error']['req'] = self._param
        return ret


def rFa( tid, resCode, err, ret, param ):
    """
    - FUNC: Orch-M 내부 요청 에러 형식으로 변환
    - INPUT
        tid(M): 요청 받은 TID
        resCode(M): 결과 코드
        err(M): 에러 발생 원인
        ret(M): 실행 반환값
        param(M): 요청 파라미터
    - OUTPUT
        isSucc(M): 변환 성공/실패
        result(M): 변환 결과(에러)
    """
    return _ReqResult(tid, ret, param, resCode, err)

def rSc( tid, ret, param, resCode=RS_SUCC, _msg=None ):
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
    return _ReqResult(tid, ret, param, resCode, msg=_msg)

def lI1(msg):
    """
    - FUNC: Lv1 로그 표시
    - INPUT
        msg(M): 로그 메시지
    - OUTPUT: Lv1 로그
    """
    return '================================> %s '%str(msg)

def lI2(msg):
    """
    - FUNC: Lv2 로그 표시
    - INPUT
        msg(M): 로그 메시지
    - OUTPUT: Lv2 로그
    """
    return '================> %s '%str(msg)

def lI3(msg):
    """
    - FUNC: Lv3 로그 표시
    - INPUT
        msg(M): 로그 메시지
    - OUTPUT: Lv3 로그
    """
    return '======> %s '%str(msg) 

def lRReq( srcIP, recvHandler, recvReq, reqParam=None ):
    """
    - FUNC: 요청 수신 로그 반환
    - INPUT
        srcIP(M): 요청 호스트 주소
        recvHandler(M): 요청 받은 handler 이름
        recvReq(M): 요청 서비스 이름
        reqParam(O): 요청 파라미터
    - OUTPUT: 요청 수신 로그
    """
    msg = 'RecvReq(%s):: %s::%s'%(str(srcIP), str(recvHandler), str(recvReq))
    if reqParam != None:
        msg += '\n<<<<-------------------------------------------------------------'
        msg += '\n%s'%str(reqParam)
        msg += '\n------------------------------------------------------------->>>>'
    return msg

def lSRes( srcIP, recvHandler, recvReq, ResRet=None ):
    """
    - FUNC: 요청 처리 결과 전송 로그 반환
    - INPUT
        srcIP(M): 요청 호스트 주소
        recvHandler(M): 요청 받은 handler 이름
        recvReq(M): 요청 서비스 이름
        ResRet(O): 요청 처리 결과
    - OUTPUT: 요청 처리 결과 전송 로그
    """
    msg = 'SendRes(%s):: %s::%s'%(str(srcIP), str(recvHandler), str(recvReq))
    if ResRet != None:
        msg += '\n<<<<-------------------------------------------------------------'
        msg += '\n%s'%str(ResRet)
        msg += '\n------------------------------------------------------------->>>>'
    return msg




