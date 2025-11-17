#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
from datetime import datetime
from random import randint
import json

from util import db_sql
from api import zbm_api
from handler import plugin_handler
from handler import rrl_handler as rrl


TITLE = 'orchm'

import logging
logger = logging.getLogger(TITLE)



STATE_PLUGIN = 'PlugIn'
STATE_ITEM = 'Item'
STATE_GUIDE = 'Alarm Guide'
STATE_THRESHOLD = 'Threshold'
STATE_KEY = 'Item Key'
STATE_DISCMAP = 'Discovery Map'
STATE_DISC = 'Discovery'
STATE_DISCITEM = 'Discovery Item'


def delRowNoUse( tableName, referColumn, dbm, val=None ):
    """
    - FUNC: 참조하지 않고 사용 중이 아닌 데이터 삭제
    - INPUT
        tableName(M): 테이블 이름
        referColumn(M): 참조되는 컬럼 이름
        dbm(M): DB 연결 객체
        val(O): 참조 컬럼의 데이터
    - OUTPUT : 삭제된 데이터 수
    """
    getTableSql = db_sql.GET_TABLE_INFO_USING_FKEY( tableName, referColumn )
    tableList = dbm.select( getTableSql )
    if tableList == None or len(tableList) < 1 :
        delSql = db_sql.REMOVE_ROW_NOUSE( tableName, referColumn, val )
        return dbm.execute( delSql )
    else:
        delSql = db_sql.REMOVE_ROW_NOUSE_FK( tableName, referColumn, tableList, val )
        return dbm.execute( delSql )


def makeThresholdKey( grade, cTime=None ):
    """
    - FUNC: Zabbix 용 임계치 조건문을 구분하기 위한 구분자를 생성한다.(Zabbix 조건문을 구분하기 위해 comments 항목에 구분자를 입력)
    - INPUT
        grade(M): 장애 등급(text)
        cTime(M): 생성시간(dttm or text)
    - OUTPUT : Zabbix 용 임계치 구분자
    """
    cTime = ( lambda x: x if x != None else datetime.now() )(cTime)
    return str(grade).replace(' ', '-').lower() + '.' + str(randint(0, 10000)) + '.' + str(cTime).replace(' ', '-')

def _getCdtType( cdts ):
    """
    - FUNC: Orch-M 용 조건문에서 WEB 연동을 위한 조건 타입 추출(조건 타입: 이상, 이하, 초과, 미만, 동일)
    - INPUT
        cdts(M): Orch-M 용 조건문
    - OUTPUT : WEB 용 조건 판단 데이터(이상, 이하, 초과, 미만, 동일, None)
        result: rrl_handler._ReqResult
    """
    FNAME = 'Get Condition Type'
    if type(cdts) == list:
        if len(cdts) == 3 :
            cdtOp = valOp1 = valOp2 = None
            for tmp in cdts:
                if type(tmp) != dict and type(tmp) != list and str(tmp).lower() == 'and':
                    cdtOp = 'and'
                elif type(tmp) == dict and tmp.has_key('op'):
                    if valOp1 == None:
                        valOp1 = tmp
                    else:
                        valOp2 = tmp
                else:
                    rres = rrl.rFa(None, rrl.RS_UNSUPPORTED_PARAM, 'Data Parsing Error', None, tmp)
                    logger.warning( rres.lL(FNAME) )
            
            if cdtOp == 'and' :
                if float(valOp1['value']) > float(valOp2['value']) :
                    if valOp1['op'] == '<=' and valOp2['op'] == '>' : return rrl.rSc(None, 'le', None)
                    elif valOp1['op'] == '<' and valOp2['op'] == '>=' : return rrl.rSc(None, 'ge', None)
                elif float(valOp2['value']) > float(valOp1['value']) :
                    if valOp2['op'] == '<=' and valOp1['op'] == '>' : return rrl.rSc(None, 'le', None)
                    elif valOp2['op'] == '<' and valOp1['op'] == '>=' : return rrl.rSc(None, 'ge', None)
                else:
                    rres = rrl.rFa(None, rrl.RS_UNSUPPORTED_PARAM, 'Getting Condition Type Error', None, 
                                   {'op':cdtOp, 'val1':valOp1, 'val2':valOp2})
                    logger.error( rres.lL(FNAME) )
                    return rres
            else:
                rres = rrl.rFa(None, rrl.RS_UNSUPPORTED_PARAM, 'Not AND Operation', None, 
                               {'op':cdtOp, 'val1':valOp1, 'val2':valOp2})
                logger.error( rres.lL(FNAME) )
                return rres
        else:
            rres = rrl.rFa(None, rrl.RS_INVALID_DATA, 'Condition Length != 3', None, cdts)
            logger.error( rres.lL(FNAME) )
            return rres
                
    else:
        _op = cdts['op']
        if _op == '<=' : return rrl.rSc(None, 'le', None)
        elif _op == '<' : return rrl.rSc(None, 'lt', None)
        elif _op == '==' : return rrl.rSc(None, 'eq', None)
        elif _op == '>=' : return rrl.rSc(None, 'ge', None)
        elif _op == '>' : return rrl.rSc(None, 'gt', None)
        else:
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Unknown Condition Operator', None, cdts)
            logger.error( rres.lL(FNAME) )
            return rres
        
    rres = rrl.rFa(None, rrl.RS_FAIL_OP, 'Not Operated', None, cdts)
    logger.error( rres.lL(FNAME) )
    return rres

def chkForCreateTarget( dbm, targetCode, targetType, targetVer, vendorCode, targetModel, vdudSeq, targetFor ):
    """
    - FUNC: 감시 대상을 만들기 위한 요청 파라미터의 유효성 체크
    - INPUT
        dbm(M): DB 연결 객체
        targetCode(M): 감시 대상 코드(hw, os, vim, vnf)
        targetType(M): 감시 대상 타입(svr, linux/unix, openstack/cloudstack, waf/utm/xms.. )
        targetVer(M): 감시 대상 모니터링 버전
        vendorCode(M): 벤더 코드
        targetModel(M): 감시 대상 상품 모델
        vdudSeq(M): VDUD Seq
        targetFor(M): 감시 목적(OneTouch/Provisioning)
    - OUTPUT : 파라미터 유효성 체크 결과
        result: rrl_handler._ReqResult
    """
    FNAME = 'Check for Create Target'
    try:
        ## vendor 유무 확인
        hasVendorSql = db_sql.GET_VENDOR_FOR_CREATE( vendorCode )
        ret = dbm.select( hasVendorSql )
        if ret == None or len(ret) < 1 :
            if ret == None:
                rs = rrl.RS_FAIL_DB
                err = None
                param = hasVendorSql
            else:
                rs = rrl.RS_NO_DATA
                err = 'No Vendor Info'
                param = vendorCode
            rres = rrl.rFa(None, rs, err, ret, param)
            logger.error( rres.lF(FNAME) )
            return rres
        
        ## vdud 확인
        if vdudSeq != None and vdudSeq != '' :
            hasVdudSql = db_sql.GET_VDUD_FOR_CREATE( vdudSeq )
            ret = dbm.select( hasVdudSql )
            if ret == None or len(ret) < 1 :
                if ret == None:
                    rs = rrl.RS_FAIL_DB
                    err = None
                    param = hasVdudSql
                else:
                    rs = rrl.RS_NO_DATA
                    err = 'No VDUD Info'
                    param = vdudSeq
                rres = rrl.rFa(None, rs, err, ret, param)
                logger.error( rres.lF(FNAME) )
                return rres
        
        ## 동일 target 확인
        hasTargetSql = db_sql.GET_TARGET_FOR_CREATE( targetCode, targetType, vendorCode, targetModel, 
                                                     targetVer, vdudSeq )
        ret = dbm.select( hasTargetSql )
        if ret == None or len(ret) > 0 :
            if ret == None:
                rs = rrl.RS_FAIL_DB
                err = None
                param = hasTargetSql
            else:
                rs = rrl.RS_DUPLICATE_DATA
                err = 'Duplicated Target'
                param = {'code':targetCode, 'type':targetType, 'vendor':vendorCode, 'model':targetModel}
            rres = rrl.rFa(None, rs, err, ret, param)
            logger.error( rres.lF(FNAME) )
            return rres
        
        return rrl.rSc(None, None, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres

def createTarget( targetCode, targetType, vendorCode, targetModel, targetDesc, 
                  targetName, targetVName, targetVer, vdudSeq, targetFor, vdudVer, dbm ):
    """
    - FUNC: 감시 대상 정보 생성
    - INPUT
        targetCode(M): 감시 대상 코드(hw, os, vim, vnf)
        targetType(M): 감시 대상 타입(svr, linux/unix, openstack/cloudstack, waf/utm/xms.. )
        vendorCode(M): 벤더 코드
        targetModel(M): 감시 대상 상품 모델
        targetDesc(M): 감시 대상에 대한 설명
        targetName(M): 감시 대상 이름
        targetVName(M): 감시 대상 표시 이름
        targetVer(M): 감시 대상 모니터링 버전
        vdudSeq(M): VDUD Seq
        targetFor(M): 감시 목적(OneTouch/Provisioning)
        vdudVer(M): VDUD 버전
        dbm(M): DB 연결 객체
    - OUTPUT : 감시대상 Seq(targetSeq)
        result: rrl_handler._ReqResult
    """
    try:
        createTargetSql = db_sql.INSERT_TARGET( targetCode, targetType, vendorCode, targetModel, targetDesc, 
                                    targetName, targetVName, targetVer, targetFor )
        targetSeq = dbm.execute( createTargetSql, True )
        if targetSeq == None :
            rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert Target Error', None, createTargetSql)
            logger.error( rres.lF('Create Target') )
            return rres

        if targetSeq is not None and vdudSeq is not None :
            createTargetVdudo = db_sql.INSERT_VDUDTARGET(targetSeq, vdudSeq, vdudVer)
            dbm.execute( createTargetVdudo, True )
        
        return rrl.rSc(None, { 'targetSeq' : str(targetSeq) }, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error( rres.lF('Create Target') )
        logger.fatal( e )
        return rres

def createGroup( targetSeq, groupInfo, dbm ):
    """
    - FUNC: 감시 그룹 정보 생성
    - INPUT
        targetSeq(M): 감시 대상 Seq
        groupInfo(M): 감시 그룹 정보
        dbm(M): DB 연결 객체
    - OUTPUT : 감시그룹 Seq(groupSeq)
        result: rrl_handler._ReqResult
    """
    try:
        grpName = groupInfo['name']
        grpVName = groupInfo['visible']
        grpDesc = groupInfo['description']
        
        hasGroupSql = db_sql.GET_GROUP_FOR_CREATE( targetSeq, grpName )
        ret = dbm.select( hasGroupSql )
        if ret == None or len(ret) > 0 :
            if ret == None :
                rs = rrl.RS_FAIL_DB
                err = None
                param = hasGroupSql
            else:
                rs = rrl.RS_DUPLICATE_DATA
                err = 'Used GroupName'
                param = {'target_seq':targetSeq, 'group_name':grpName}
            rres = rrl.rFa(None, rs, err, ret, param)
            logger.error( rres.lF('Create Group') )
            return rres
        
        addGroupSql = db_sql.INSERT_GROUP( targetSeq, grpName, grpVName, grpDesc )
        grpSeq = dbm.execute( addGroupSql, True )
        if grpSeq == None :
            rres = rrl.rFa(None, rrl.RS_FAIL_DB, None, None, addGroupSql)
            logger.error( rres.lF('Create Group') )
            return rres
        
        return rrl.rSc(None, { 'groupSeq': str(grpSeq) }, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, None)
        logger.error( rres.lF('Create Group') )
        logger.fatal( e )
        return rres

def removeItem( itemList, dbm ):
    """
    - FUNC: 감시 아이템 제거
    - INPUT
        itemList(M): 감시 아이템 리스트
        dbm(M): DB 연결 객체
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Remove Item'
    state = STATE_KEY
    itemSeq = None
    try:
        cnt = 0
        for itemSeq in itemList:
            state = STATE_KEY
            delKeySql = db_sql.DEL_KEY_BY_ITEM(itemSeq)
            ret = dbm.execute( delKeySql )
            if ret == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Delete Key Error', ret, delKeySql)
                logger.error( rres.lF(FNAME) )
                return rres
            delRowNoUse( 'tb_zbkeycatalog', 'zbkeycatseq', dbm)
            
            state = STATE_THRESHOLD
            getThrsSql =  db_sql.DEL_THRESOLD_BY_ITEM(itemSeq)
            ret = dbm.execute( getThrsSql )
            if ret == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Delete Threshold Error', ret, getThrsSql)
                logger.error( rres.lF(FNAME) )
                return rres
            delRowNoUse( 'tb_monthresholdcatalog', 'monthresholdcatseq', dbm)
            
            state = STATE_ITEM
            getGuideSql = db_sql.GET_GUIDE_FOR_DELITEM(itemSeq)
            _gList = dbm.select( getGuideSql, 'monalarmguideseq' )
            if _gList == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Get Guide Error', _gList, getGuideSql)
                logger.error( rres.lF(FNAME) )
                return rres
            
            getPlugSql = db_sql.GET_PLUGIN_FOR_DELITEM(itemSeq)
            pSeq = dbm.select( getPlugSql, 'monplugincatseq' )
            if pSeq == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Get PlugIn Error', pSeq, getPlugSql)
                logger.error( rres.lF(FNAME) )
                return rres
            
            delItemSql = db_sql.DEL_ITEM_BY_SEQ(itemSeq)
            ret = dbm.execute( delItemSql )
            if ret == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Delete Item Error', ret, delItemSql)
                logger.error( rres.lF(FNAME) )
                return rres
            delRowNoUse( 'tb_monitemcatalog', 'monitemcatseq', dbm)
            
            state = STATE_GUIDE
            if len(_gList) > 0: 
                for gSeq in _gList:
                    if gSeq == None :
                            continue
                        
                    delGuideSql = db_sql.DEL_GUIDE_BY_SEQ(gSeq)
                    ret = dbm.execute( delGuideSql )
                    if ret == None:
                        rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Delete Guide Error', ret, delGuideSql)
                        logger.error( rres.lF(FNAME) )
                        return rres
                    delRowNoUse( 'tb_monalarmguide', 'monalarmguideseq', dbm)
            
            state = STATE_PLUGIN
            if len(pSeq) > 0 :
                delPlugInSql = db_sql.DEL_PLUGIN_BY_SEQ(pSeq[0])
                ret = dbm.execute( delPlugInSql )
                if ret == None:
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Delete PlugIn Error', ret, delPlugInSql)
                    logger.error( rres.lF(FNAME) )
                    return rres
                delRowNoUse( 'tb_monplugincatalog', 'monplugincatseq', dbm)
            
            cnt += 1
        
        return rrl.rSc(None, cnt, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'item_seq':itemSeq, 'state':state})
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres

def createItem( targetSeq, groupSeq, itemList, dbm, discSeq=None, keyInput=None ):
    """
    - FUNC: 감시 아이템 생성
    - INPUT
        targetSeq(M): 감시 대상 Seq
        groupSeq(M): 감시 그룹 Seq
        itemList(M): 감시 아이템 리스트
        dbm(M): DB 연결 객체
        discSeq(O): 감시 Discovery Seq
        keyInput(O): 감시 Discovery의 Key 파라미터
    - OUTPUT: 생성된 각 항목의 수
        result: rrl_handler._ReqResult
    """
    FNAME = 'Creaet Item'
    state = STATE_PLUGIN
    cntPlugin = 0
    cntItem = 0
    cntGuide = 0
    cntThreshold = 0
    cntKey = 0
    cntMap = 0
    itemInfo = None
    try:
        for itemInfo in itemList :
            # PlugIn 생성
            pluginSeq = None
            if itemInfo.has_key('plugin'):
                rres = plugin_handler.registerPlugIn( targetSeq, groupSeq, itemInfo['plugin'], dbm )
                if rres.isFail() :
                    rres.setParam({'plugin_info':itemInfo['plugin']})
                    rres.lF(FNAME)
                    return rres
                pluginSeq = rres.ret()
                cntPlugin += 1
                logger.info( 'Success: Register PlugIn, name=%s, seq=%s'%( itemInfo['plugin']['name'], str(pluginSeq) ) )
            
            # 장애 guide 생성
            state = STATE_GUIDE
            alarmGuideSeq = None
            if itemInfo.has_key('alarm_guide') :
                guideInfo = itemInfo['alarm_guide']
                insertGuideSql = db_sql.INSERT_GUIDE( guideInfo['name'], guideInfo['guide'] )
                alarmGuideSeq = dbm.execute( insertGuideSql, True )
                if alarmGuideSeq == None :
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert Guide Error', None, insertGuideSql)
                    rres.lF(FNAME)
                    return rres
                cntGuide += 1
                logger.info( 'Success: Make Alarm Guide, name=%s, seq=%s'%( guideInfo['name'], str(alarmGuideSeq) ) )
            
            # Item 생성
            state = STATE_ITEM
            iName = itemInfo['name']
            iVName = itemInfo['visible']
            iType = itemInfo['type']
            iPeriod = itemInfo['period']
            iDataType = itemInfo['data_type']
            iDesc = itemInfo['description']
            iValType = ( lambda x : x['value_type'] if x.has_key('value_type') else None )( itemInfo )
            iUnit = ( lambda x : x['unit'] if x.has_key('unit') else None )( itemInfo )
            if itemInfo.has_key('history') :
                histSaveMon = itemInfo['history']
            else:
                histSaveMon = str(10)
                itemInfo['history'] = histSaveMon
            if itemInfo.has_key('statistic') :
                statSaveMon = itemInfo['statistic']
            else:
                statSaveMon = str(180)
                itemInfo['statistic'] = statSaveMon
            graphYN = ( lambda x : x['graph_yn'] if x.has_key('graph_yn') else 'n' )( itemInfo )
            realTimeYN = ( lambda x : x['realtime_yn'] if x.has_key('realtime_yn') else 'n' )( itemInfo )
            inputType = ( lambda x : None if x == None else 'zabbix' )( keyInput )
            monMethod = ( lambda x : x['monitor_method'] if x.has_key('monitor_method') else 'active' )( itemInfo )
            statisticsYn = (lambda x: x['statistics_yn'] if x.has_key('statistics_yn') else 'n')(itemInfo)  # 2017.02.16  add statistics_yn
            itemId = (lambda x: x['item_id'] if x.has_key('item_id') else 'n')(itemInfo)  # 2017.02.27  add item_id
            pluginType = None
            if itemInfo.has_key('zb_type'):
                pluginType = 'zabbix'
            else:
                pluginType = 'plugin'

            # 2017.02.16  add statisticsYn, 2017.02.27 add item_id
            insertItemSql = db_sql.INSERT_ITEM( targetSeq, groupSeq, iName, iVName, iType, iPeriod,
                                    pluginSeq, iDataType, histSaveMon, statSaveMon, 
                                    graphYN, realTimeYN, monMethod, iDesc, pluginType, 
                                    iValType, iUnit, inputType, alarmGuideSeq, statisticsYn, itemId )
            itemSeq = dbm.execute( insertItemSql, True )
            if itemSeq == None :
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert Item Error', None, insertItemSql)
                rres.lF(FNAME)
                return rres
            cntItem += 1
            logger.info( 'Success: Make Item, name=%s, seq=%s'%( iName, str(itemSeq) ) )
            
            # Threshold 생성
            state = STATE_THRESHOLD
            if itemInfo.has_key('threshold'):
                thrZbYn = ( lambda x: True if x.has_key('threshold_zb_yn') and str(x['threshold_zb_yn']).lower() == 'y' else False )(itemInfo)
                for thrInfo in itemInfo['threshold'] :
                    tName = thrInfo['name']
                    tGrade = thrInfo['grade'].lower()
                    tCondition = json.dumps( thrInfo['conditions'], encoding='utf-8')
                    tRepeat = str(thrInfo['repeat'])
                    tDesc = thrInfo['description']
                    tKey = None
                    if thrZbYn:
                        tKey = makeThresholdKey( tGrade, datetime.now() )
                    thrInfo['t_key'] = tKey
                    rres = _getCdtType(thrInfo['conditions'])
                    if rres.isFail() :
                        rres.lF(FNAME)
                        return rres
                    tCdtType = rres.ret()
                    
                    insertThrSql = db_sql.INSERT_THRESHOLD( tName, itemSeq, tGrade, tCdtType, tCondition, tRepeat, tDesc, tKey )
                    thrSeq = dbm.execute( insertThrSql, True )
                    if thrSeq == None :
                        rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert Threshold Error', None, insertThrSql)
                        rres.lF(FNAME)
                        return rres
                    cntThreshold += 1
                    logger.info( 'Success: Make Threshold, name=%s, seq=%s'%( tName, str(thrSeq) ) )
            
            # Key 생성
            state = STATE_KEY
            keyParam = None
            keyParamType = None
            if keyInput != None :
                keyParam = '[%s]'
                keyParamType = '{#%s}'%keyInput
            if itemInfo.has_key('zb_type') :
                getZbKeySql = db_sql.GET_ZB_KEY( itemInfo['zb_type'] )
                ret = dbm.select( getZbKeySql, 'key' )
                if ret == None or len(ret) != 1:
                    if ret == None :
                        rs = rrl.RS_FAIL_DB
                        param = getZbKeySql
                        err = 'Get ZB Key DB Error'
                    else:
                        rs = rrl.RS_INVALID_DATA
                        param = {'zb_type': itemInfo['zb_type'], 'item_info':itemInfo}
                        err = 'No ZB Key Info'
                    rres = rrl.rFa(None, rs, err, ret, param)
                    rres.lF(FNAME)
                    return rres
                key = ret[0]
            else:
                if str(itemInfo['plugin']['type']).lower() == 'builtin':
                    rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Builtin-Plugins Need zb_type Parameter', None, itemInfo)
                    rres.lF(FNAME)
                    return rres
                
                getTGSql = db_sql.GET_TARGET_GROUP_FOR_KEY(targetSeq, groupSeq)
                ret = dbm.select( getTGSql )
                if ret == None or len(ret) != 1 :
                    if ret == None:
                        rs = rrl.RS_FAIL_DB
                        param = getTGSql
                    else:
                        rs = rrl.RS_INVALID_DATA
                        param = {'target_seq':targetSeq, 'group_seq':groupSeq}
                    rres = rrl.rFa(None, rs, 'Get Target-Group Info for Key Error', None, param)
                    rres.lF(FNAME)
                    return rres
                key = zbm_api.makeZbKey( targetSeq, ret[0]['targettype'], ret[0]['groupname'], iType, keyParam )
            
            getKeySql = db_sql.GET_KEY_FOR_ADD( targetSeq, key, keyParamType )
            ret = dbm.select( getKeySql )
            if ret == None:
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Get Key Error', None, getKeySql)
                rres.lF(FNAME)
                return rres
            if len(ret) > 0 :
                rres = rrl.rFa(None, rrl.RS_DUPLICATE_DATA, 'Duplicated Key', None, 
                               {'target_seq':targetSeq, 'key':key, 'key_param_type':keyParamType})
                rres.lF(FNAME)
                return rres
            
            itemInfo['key']=key
            insertKeySql = db_sql.INSERT_KEY( itemSeq, key, keyParamType )
            keySeq = dbm.execute( insertKeySql, True )
            if keySeq == None :
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert Key Error', None, insertKeySql)
                rres.lF(FNAME)
                return rres
            cntKey += 1
            logger.info( 'Success: Make Key, key=%s, seq=%s'%( key, str(keySeq) ) )
            
            # DiscoveryMap 생성
            state = STATE_DISCMAP
            if discSeq != None :
                insertDiscMapSql = db_sql.INSERT_DISCOVERY_MAP( discSeq, itemSeq )
                mapSeq = dbm.execute( insertDiscMapSql, True )
                if mapSeq == None :
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert DiscoveryMap Error', None, insertDiscMapSql)
                    rres.lF(FNAME)
                    return rres
                cntMap += 1
                logger.info( 'Success: Make DiscoveryMap, discoverySeq=%s, itemSeq=%s, seq=%s'%(str(discSeq), str(itemSeq), str(mapSeq)) )
        
        ret = {'Item':cntItem, 'PlugIn':cntPlugin, 'AlarmGuide':cntGuide, 'Threshold':cntThreshold, 'Key':cntKey}
        if discSeq != None :
            ret['DiscoveryMap'] = cntMap
        
        return rrl.rSc(None, ret, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'item_info':itemInfo, 'state':state})
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres

def createDiscovery( targetSeq, groupSeq, discoveryList, dbm ):
    """
    - FUNC: 감시 Discovery 생성
    - INPUT
        targetSeq(M): 감시 대상 Seq
        groupSeq(M): 감시 그룹 Seq
        discoveryList(M): 감시 Disocvery 리스트
        dbm(M): DB 연결 객체
    - OUTPUT: 생성된 각 항목의 수
        result: rrl_handler._ReqResult
    """
    FNAME = 'Create Discovery'
    state = STATE_PLUGIN
    cntPlugIn = 0
    cntDisc = 0
    _ret = {'Discovery':0, 'DiscoveryPlugIn':0, 'Item':0, 'PlugIn':0, 'Key':0, 'Threshold':0, 'AlarmGuide':0, 'DiscoveryMap':0 }
    dName = None
    try:
        for discInfo in discoveryList :
            # PlugIn 생성
            pluginSeq = None
            if discInfo.has_key('plugin'):
                rres = plugin_handler.registerPlugIn( targetSeq, groupSeq, discInfo['plugin'], dbm )
                if rres.isFail() :
                    rres.lF(FNAME)
                    return rres
                pluginSeq = rres.ret()
                cntPlugIn += 1
                logger.info( 'Success: Register PlugIn, name=%s, seq=%s'%( discInfo['plugin']['name'], str(pluginSeq) ) )
            
            # Discovery 생성
            state = STATE_DISC
            dName = discInfo['name']
            dPeriod = str(discInfo['period'])
            returnField = discInfo['return_field']
            histSaveDay = ( lambda x : x['remain'] if x.has_key('remain') else 1 )( discInfo )
            monMethod = ( lambda x : x['monitor_method'] if x.has_key('monitor_method') else 'active' )( discInfo )
            dDesc = discInfo['description']
            pluginType = 'plugin'
            if discInfo.has_key('zb_type'):
                getZbKeySql = db_sql.GET_ZB_KEY( discInfo['zb_type'] )
                ret = dbm.select( getZbKeySql, 'key' )
                if ret == None or len(ret) != 1:
                    if ret == None :
                        rs = rrl.RS_FAIL_DB
                        param = getZbKeySql
                    else:
                        rs = rrl.RS_INVALID_DATA
                        param = {'zb_type': discInfo['zb_type'], 'disc_name':dName}
                    rres = rrl.rFa(None, rs, 'Get ZB Key Error', ret, param)
                    rres.lF(FNAME)
                    return rres
                zbKey = ret[0]
                pluginType = 'zabbix'
            else:
                if str(discInfo['plugin']['type']).lower() == 'builtin':
                    rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Builtin-Plugins Need zb_type Parameter', None, 
                                   {'disc_name':dName, 'plugin': discInfo['plugin']})
                    rres.lF(FNAME)
                    return rres
                
                getTGSql = db_sql.GET_TARGET_GROUP_FOR_KEY(targetSeq, groupSeq)
                ret = dbm.select( getTGSql )
                if ret == None or len(ret) != 1 :
                    if ret == None:
                        rs = rrl.RS_FAIL_DB
                        param = getTGSql
                    else:
                        rs = rrl.RS_INVALID_DATA
                        param = {'target_seq':targetSeq, 'group_seq':groupSeq}
                    rres = rrl.rFa(None, rs, 'Get Target-Group Info for Key Error', None, param)
                    rres.lF(FNAME)
                    return rres
                zbKey = zbm_api.makeZbKey( targetSeq, ret[0]['targettype'], ret[0]['groupname'], dName )
            
            insDiscSql = db_sql.INSERT_DISCOVERY( targetSeq, groupSeq, dName, zbKey, dPeriod, pluginSeq, 
                                        returnField, histSaveDay, dDesc, monMethod, pluginType )
            discSeq = dbm.execute( insDiscSql, True )
            if discSeq == None :
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert Discovery Error', None, insDiscSql)
                rres.lF(FNAME)
                return rres
            cntDisc += 1
            logger.info( 'Success: Make Discovery, name=%s, seq=%s'%( dName, str(discSeq) ) )
            
            # Item 생성
            state = STATE_DISCITEM
            if discInfo.has_key('item') :
                rres = createItem( targetSeq, groupSeq, discInfo['item'], dbm, discSeq, returnField )
                if rres.isFail() :
                    rres.lF(FNAME)
                    return rres
                retItem = rres.ret()
            # {'Item':, 'PlugIn':, 'AlarmGuide':, 'Threshold':, 'Key':}
            
            _ret['Item'] += retItem['Item']
            _ret['AlarmGuide'] += retItem['AlarmGuide']
            _ret['Threshold'] += retItem['Threshold']
            _ret['Key'] += retItem['Key']
            _ret['DiscoveryMap'] += retItem['DiscoveryMap']
            logger.info( 'Success: Make DiscoveryItem, count=%s'%( str(retItem['Item']) ) )
        
        _ret['Discovery'] = cntDisc
        _ret['DiscoveryPlugIn'] = cntPlugIn
        return rrl.rSc(None, _ret, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'disc_name':dName, 'state':state})
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres







