#-*- coding: utf-8 -*-

from datetime import datetime
from util import db_sql

# 개발시 로그표시 유무.
DEBUG_LOG_YN = 'n'

def saveSms( logger, mysqlDb, smsID, subject, msg, smsCallback, userList ):
    try:
        return _saveSMS(logger, mysqlDb, smsID, subject, msg, smsCallback, userList )
    except Exception, e:
        logger.fatal(e)
    
    return None

## scheduleType : 0->즉시, 1-> 예약
## userList : name, phone_num
def _saveSMS( logger, mysqlDb, userID, subject, msg, callBack, destList, callbackUrl=None, nowDate=None, 
               scheduleType=0, sendDate=None, ktOfficeCode=None, cdrID=None ):
    
    ## DEST_INFO: 홍길동^01011112222|개똥이^01043211234
    destCount = len(destList)
    destInfo = ''
    isFirst = True
    for dest in destList :
        if isFirst :
            destInfo += ( str(dest['name']) + '^' + str(dest['phone_num']) )
            isFirst = False
        else:
            destInfo += ( '|' + str(dest['name']) + '^' + str(dest['phone_num']) )
    
    ## Now Date: YYYYMMDDHHMMSS
    if nowDate == None :
        nowDate = datetime.now()
    _nowDate = nowDate.strftime('%Y%m%d%H%M%S')
    
    ## Schedule
    _sendDate = _nowDate
    if scheduleType == 1 :
        _sendDate = sendDate.strftime('%Y%m%d%H%M%S')
    
    sql = db_sql.INSERT_SMS_MSG( userID, subject, msg, callBack, destInfo, destCount, _nowDate, 
                    scheduleType, _sendDate, callbackUrl, ktOfficeCode, cdrID)

    if DEBUG_LOG_YN == 'y': logger.info('[_saveSMS] ==========> sql : %s' % str(sql))
#     logger.debug(sql)
    try:
        mysqlDb.set_character_set('utf8')
        cur = mysqlDb.cursor()
        ret = cur.execute( sql )

        if ret < 1: 
            mysqlDb.rollback()
            cur.close()         # 2017.04.13 김승주전임 추가 요청, connection 문제
            return None
        else:
            mysqlDb.commit()
            cur.close()         # 2017.04.13 김승주전임 추가 요청, connection 문제
            return cur.lastrowid
    except Exception, e:
        logger.fatal(e)
        mysqlDb.rollback()
        return None
    finally:
        cur.close()
    

def getResult( resultCode ):
    if resultCode == 0 :        return 'WAIT_SEND'              ## 전송 대기중
    elif resultCode == 1 :      return 'WAIT_CONN'              ## 전송 대기중(호연결중)
    elif resultCode == 2 :      return 'SUCC'                   ## 성공
    elif resultCode == 3 :      return 'ETC_ERR'                ## 전송 실패
    elif resultCode == 4 :      return 'NO_RES'                 ## 무등답
    elif resultCode == 5 :      return 'ON_CALL'                ## 통화중
    elif resultCode == 6 :      return 'NO_NUMBER'              ## 결번
    elif resultCode == 8 :      return 'SUCC'                   ## 성공(전송은 성공이나, 답변 없음)
    elif resultCode == 20 :     return 'NO_MSG'                 ## 전달메시지 없음
    elif resultCode == 21 :     return 'DENY_LISTEN'            ## 청취거부
    elif resultCode == 22 :     return 'DENY_RECV'              ## 수신거부
    elif resultCode == 23 :     return 'FAIL_TTS'               ## 음성변환 실패
    elif resultCode == 24 :     return 'FAIL_TTF'               ## 문서변환 실패
    elif resultCode == 25 :     return 'FAIL_INTEROPER_TELCO'   ## 이통사 연동 실패
    elif resultCode == 32 :     return 'FAIL_INTEROPER_NET'     ## 망 연동 실패
    elif resultCode == 33 :     return 'OVER_SEND_PER_TIME'     ## 시간당 전송 건수 초과
    elif resultCode == 34 :     return 'OVER_SEND_PER_SUBS'     ## 가입자당 전송 건수 초과
    elif resultCode == 36 :     return 'INVALID_INPUT_DATA'     ## 입력 데이터 오류
    elif resultCode == 37 :     return 'FAIL_DB_OP'             ## DB 작업 오류
    elif resultCode == 38 :     return 'EXPIRED'                ## 전송시간 만료
    elif resultCode == 39 :     return 'FORCED_REMOVE_BY_MNGR'  ## 관리자 삭제
    elif resultCode == 40 :     return 'FAIL_ALLOCATE_CHANNEL'  ## 채널 부족(채널 할당받지 못함)
    elif resultCode == 41 :     return 'DO_NOT_CALL_REGISTRY'   ## 수신거부 번호
    elif resultCode == 42 :     return 'INSUFFICIENT_CHANNEL'   ## 채널 부족(대국 채널 부족)
    elif resultCode == 43 :     return 'WAIT_REPORT'            ## 이통사 전송 후 결과 대기
    elif resultCode == 44 :     return 'SPAM_XROSHOT'           ## 스팸 처리(크로샷)
    elif resultCode == 45 :     return 'FAIL_REGISTER'          ## 크로샷 서버 등록 실패
    elif resultCode == 46 :     return 'NO_AGENT_NUMBER'        ## 상담원 연결번호 오류
    elif resultCode == 47 :     return 'LIMIT_SAME_MSG'         ## 동일메시지 제한(1시간 당 20건)
    elif resultCode == 49 :     return 'OVER_TERM_STORAGE_CAPA' ## 단말기 저장 건수 초과
    elif resultCode == 50 :     return 'TERMINAL_SUSPEND'       ## 단말기 일시정지
    elif resultCode == 51 :     return 'TERMINAL_ERROR'         ## 단말기 오류
    elif resultCode == 52 :     return 'INVALIDE_TERMINAL'      ## 서비스 불가 단말
    elif resultCode == 53 :     return 'LACK_XROSHOT_BALANCE'   ## 크로샷 잔액 부족
    elif resultCode == 54 :     return 'NOT_XROSHOT_SUBS'       ## 크로샷 비가입자
    elif resultCode == 55 :     return 'XROSHOT_SUBS_SUSPEND'   ## 크로샷 일시 정지 가입자
    elif resultCode == 56 :     return 'LIMIT_LOCAL_THRESHOLD'  ## 로컬 임계치 제한
    elif resultCode == 57 :     return 'BIND_ERROR'             ## BIND 오류
    elif resultCode == 58 :     return 'SPAM'                   ## 스팸
    elif resultCode == 59 :     return 'SPAM_CALLBACK_URL'      ## 회신 URL 스팸
    elif resultCode == 60 :     return 'SPAM_CALLBACK_NUMBER'   ## 회신 번호 스팸
    elif resultCode == 61 :     return 'SPAM_CALLER_NUMBER'     ## 발신 번호 스팸
    elif resultCode == 62 :     return 'OVER_SMSC_CAPA'         ## SMSC 용량 초과
    elif resultCode == 63 :     return 'OVER_SEND_PER_MONTH'    ## 월간 전송건수 초과
    elif resultCode == 64 :     return 'INVALID_MSG_LENGTH'     ## 메시지 길이 오류
    elif resultCode == 65 :     return 'OVER_BROADCAST_NUMBER'  ## 동보 건수 초과
    elif resultCode == 66 :     return 'INVALID_TEMPLATE_FORMAT'## 템플릿 형식 오류
    elif resultCode == 67 :     return 'NOT_SUPPORTED_VERSION'  ## 지원하지 않는 버전
    elif resultCode == 68 :     return 'FORCED_REMOVE_BY_CP'    ## CP의 삭제 요청
    else:                       return 'UNKNOWN_RESULT'

def getTcsResult( tcsCode ):
    if tcsCode == 0 :       return 'SUCC'                   ## 전송 대기중
    elif tcsCode == 1 :     return 'SYS_FAULT'              ## 시스템 장애
    elif tcsCode == 2 :     return 'FAIL_AUTH'              ## 인증 실패
    elif tcsCode == 3 :     return 'INVALID_MSG_FORMAT'     ## 메시지 형식 오류
    elif tcsCode == 5 :     return 'INVALID_AUTH_TICKET'    ## 인증 티켓유효성 오류(비번, SPID 틀린 경우)
    elif tcsCode == 8 :     return 'SP_SUBS_SUSPEND'        ## SP 가입자 일시정지
    elif tcsCode == 9 :     return 'SP_SUBS_CANCEL'         ## SP 가입자 해지
    elif tcsCode == 10 :    return 'NO_SUBS'                ## 가입자 해지
    elif tcsCode == 27 :    return 'NO_SVC'                 ## 가입되지 않은 상품 발송
    elif tcsCode == 33 :    return 'OVER_SEND_PER_MONTH'    ## 월간 전송건수 초과
    elif tcsCode == 101 :   return 'SPAM'                   ## 스팸
    elif tcsCode == 102 :   return 'SPAM_CALLER_NUMBER'     ## 발신 번호 스팸
    elif tcsCode == 103 :   return 'SPAM_RECEIVER_NUMBER'   ## 착신 번호 스팸
    elif tcsCode == 104 :   return 'SPAM_CALLBACK_NUMBER'   ## 회신 번호 스팸
    elif tcsCode == 112 :   return 'EXPIRED_REPORT'         ## Report 수신시간 만료
    elif tcsCode == 200 :   return 'ON_CALL'                ## 전화 중
    elif tcsCode == 201 :   return 'NO_TERMINAL_RESPONSE'   ## 단말기 무응답
    elif tcsCode == 202 :   return 'NO_RECEIVER'            ## 착신 가입자 없음
    elif tcsCode == 203 :   return 'NO_RECEIVER'            ## 비가입자, 결번, 서비스 정지
    elif tcsCode == 204 :   return 'POWER_OFF'              ## 전원 꺼짐
    elif tcsCode == 205 :   return 'UNREACHABLE_AREA'       ## 음영 지역
    elif tcsCode == 206 :   return 'OVER_TERM_STORAGE_CAPA' ## 단말기 메시지 Full
    elif tcsCode == 207 :   return 'INVALID_TERM'           ## 단말기 형식 오류
    elif tcsCode == 208 :   return 'OVERFLOW'               ## 메시지가 overflow되어 받지 못함
    elif tcsCode == 209 :   return 'NUMBER_MOVE'            ## 번호이동된 가입자
    elif tcsCode == 210 :   return 'OVER_INCOMING_TRANSITION' ## SMS 착신전환 회수 초과
    elif tcsCode == 211 :   return 'EXPIRATION'             ## 기간 만료
    elif tcsCode == 212 :   return 'NO_SKT_SUBS'            ## SKT 가입자 없음
    elif tcsCode == 213 :   return 'NPDB_ERR'               ## NPDB 오류
    elif tcsCode == 214 :   return 'SUB_TYPE_ERR'           ## Sub Type 오류
    elif tcsCode == 215 :   return 'INVALID_SUBS_NAME'      ## 한글/영문 외의 가입자일 경우
    elif tcsCode == 216 :   return 'INVALID_RECEIVER_NUMBER'## 수신번호 오류
    
    else :                  return 'UNKNOWN_TCS_RESULT'

def getSmsReport( logger, mysql, smsMsgID ):
    dic = []
    try:
        mysql.set_character_set('utf8')
        mCur = mysql.cursor()
        
        sql = db_sql.GET_SMS_REPORT_DETAIL(smsMsgID)
        mCur.execute( sql )
        rows = mCur.fetchall()
        columns = [desc[0] for desc in mCur.description]

        for row in rows:
            d = dict(zip(columns, row))
            if d['RESULT'] == 0 or d['RESULT'] == 1 :
                continue
            elif d['RESULT'] == 2 or d['RESULT'] == 8 :
                d['SEND_RESULT'] = 'SUCC'
                d['SEND_ERROR'] = ''
            elif d['RESULT'] == 3:
                d['SEND_RESULT'] = 'FAIL'
                d['SEND_ERROR'] = getTcsResult( d['TCS_RESULT'] )
            else:
                d['SEND_RESULT'] = 'FAIL'
                d['SEND_ERROR'] = getResult( d['RESULT'] )
            
            dic.append(d)
        return dic
    except Exception, e:
        logger.fatal(e)
        return None
    finally:
        mCur.close()



