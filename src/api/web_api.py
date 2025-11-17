#-*- coding: utf-8 -*-
import json

from util import db_sql, rest_api
from handler import rrl_handler as rrl


TITLE = 'orchm'

import logging
logger = logging.getLogger(TITLE)

HEADER={"content-type":"application/json-rpc"}
METHOD="POST"


URLS = {
        'noti_alarm':'/dfasdf'
        }


def _changeThrGLE( itemName, thrList, repeat, _type ):
    """
    - FUNC: WEB에서 Item 임계치 정보 수정 시 operator가 이상/이하인 항목에 대해서 Orch-M 용 parameter로 변경
    - INPUT
        itemName(M): 감시항목 이름
        thrList(M): 임계치 설정 정보 리스트
        repeat(M): 동일 임계치 위반이 얼마나 반복할 때 장애로 판단할 것인가.
        _type(M): 이상/이하
    - OUTPUT
        result(M): Orch-M 용 임계치 리스트
    """
    start_value = None
    min_max = []
    
    retList = []
    grdList = [ None, None, None, None ]
    for thr in thrList:
        if str(thr['grade']).lower().find('cri') >= 0 :
            grdList[0] = {'grade':'critical', 'value':thr['value']}
            min_max.append(thr['value'])
        elif str(thr['grade']).lower().find('maj') >= 0 :
            grdList[1] = {'grade':'major', 'value':thr['value']}
            min_max.append(thr['value'])
        elif str(thr['grade']).lower().find('min') >= 0 :
            grdList[2] = {'grade':'minor', 'value':thr['value']}
            min_max.append(thr['value'])
        elif str(thr['grade']).lower().find('warn') >= 0 :
            grdList[3] = {'grade':'warning', 'value':thr['value']}
            min_max.append(thr['value'])
        else :
            logger.error( "Invalid Data, Threshold Grade=%s"%str(thr['grade']) )
            return None
        
    hasCrit = False
    lastVal = None
    eOp = None
    tOp = None
    if _type.upper() == 'GE': # 이상
        eOp = '>='
        tOp = '<'
        if len(min_max):
            start_value = min(min_max)
    elif _type.upper() == 'LE': # 이하
        eOp = '<='
        tOp = '>'
        if len(min_max):
            start_value = max(min_max)
    
    for grd in grdList:
        if grd != None:
            thrName = '[%s] %s Fault'%( grd['grade'], itemName )
            
            if not hasCrit :
                cdt = { 'op':eOp, 'value':str(grd['value']) }
                hasCrit = True
                lastVal = grd['value']
            else:
                cdt = ["and", {"op":eOp, "value":str(grd['value'])}, {"op":tOp, "value":str(lastVal)}]
                lastVal = grd['value']
            
            retList.append( {"grade":grd['grade'], "name":thrName, 'operator':_type.lower(), 
                             'repeat':repeat, 'start_value':start_value, 'conditions':cdt, 'description':''} )
    
    return retList


## grade, name, conditions, operator, repeat, description, alarm_seq
def _changeThrGE( itemName, thrList, repeat ):
    """
    - FUNC: WEB에서 Item 임계치 정보 수정 시 operator가 이상인 항목에 대해서 Orch-M 용 parameter로 변경
    - INPUT
        itemName(M): 감시항목 이름
        thrList(M): 임계치 설정 정보 리스트
        repeat(M): 동일 임계치 위반이 얼마나 반복할 때 장애로 판단할 것인가.
    - OUTPUT
        result(M): Orch-M 용 임계치 리스트
    """
    return _changeThrGLE(itemName, thrList, repeat, 'ge')

## grade, name, conditions, operator, repeat, description, alarm_seq
def _changeThrLE( itemName, thrList, repeat ):
    """
    - FUNC: WEB에서 Item 임계치 정보 수정 시 operator가 이하인 항목에 대해서 Orch-M 용 parameter로 변경
    - INPUT
        itemName(M): 감시항목 이름
        thrList(M): 임계치 설정 정보 리스트
        repeat(M): 동일 임계치 위반이 얼마나 반복할 때 장애로 판단할 것인가.
    - OUTPUT
        result(M): Orch-M 용 임계치 리스트
    """
    return _changeThrGLE(itemName, thrList, repeat, 'le')

def convertThreshold( _params, dbm, bCatalog = False ):
    """
    - FUNC: WEB에서 Item 임계치 정보 수정 시 operator가 이상인 항목에 대해서 Orch-M 용 parameter로 변경
    - INPUT
        itemName(M): 감시항목 이름
        thrList(M): 임계치 설정 정보 리스트
        repeat(M): 동일 임계치 위반이 얼마나 반복할 때 장애로 판단할 것인가.
        bCatalog: 데이터 조회를 카탈로그에서 수행할지 여부. 2016-11-01 추가함. 기본값 false. 템플릿 수정 API를 추가하면서 임계치 수정을 위해서 추가
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Convert Threshold'
    try:
        params = {'item_seq':_params['item_seq'], 'threshold':[]}
        if _params.has_key('threshold'):
            thrInfo = _params['threshold']
            repeat = thrInfo['repeat']
            op = thrInfo['operator']
            gradeList = thrInfo['grade_info']
            
            itemName = None
            if bCatalog == True:
                itemName = dbm.select( db_sql.GET_ITEM_CATALOG_NAME(_params['item_seq']) )
            else:
                itemName = dbm.select( db_sql.GET_ITEM_INST_NAME(_params['item_seq']), 'monitoritem' )
            
            if itemName == None or len(itemName) < 1:
                if itemName == None :   rs = rrl.RS_FAIL_DB
                else:                   rs = rrl.RS_NO_DATA
                rres = rrl.rFa(None, rs, 'Getting ItemInst Error', itemName, {'item_seq':_params['item_seq']})
                logger.error( rres.lF(FNAME) )
                return rres
            
            cdtList = None
            if str(op).lower() == 'ge' :
                cdtList = _changeThrGE(itemName[0], gradeList, repeat)
            elif str(op).lower() == 'le' :
                cdtList = _changeThrLE(itemName[0], gradeList, repeat)
            else :
                rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Operator Error', None, thrInfo)
                logger.error( rres.lF(FNAME) )
                return rres
                
            if cdtList == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_OP, None, None, _params)
                logger.error( rres.lF(FNAME) )
                return rres
            
            params['threshold'] = cdtList
        return rrl.rSc(None, params, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, params)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres

def notiAlarmWeb(itemSeq, alertGrade, isAlert, dttm, trig_name=None, itemVal=None):
    url = URLS['noti_alarm']
    
    body = {'item_seq':itemSeq, 'grade': alertGrade, 'isAlert':isAlert, 'dttm':dttm}
    return
#     ret = rest_api.sendReq( HEADER, url, METHOD, body, 10 ) 널 체크
#     res = json.loads( ret.body )
#     if res['result'] == 'SC':
#         rres = rrl.rSc(None, None, {'url':url})
#         return rres
#     else:
#         rres = rrl.rFa(None, rrl.RS_API_UI_ERR, res['error'], ret, body)
#         logger.error( rres.lF('Notify Alarm to WEB') )
#         return rres

def notiWeb( title, msg ):
#     print "\n---------------------------------------------------------"
#     print "---------------------------------------------------------"
#     print "--------------------%s--------------------"%str(title)
#     print msg
#     print "---------------------------------------------------------"
#     print "---------------------------------------------------------"
    return

def notiInternalError( msg ):
#     print "\n---------------------------------------------------------"
#     print "---------------------------------------------------------"
#     print msg
#     print "---------------------------------------------------------"
#     print "---------------------------------------------------------"
    return

