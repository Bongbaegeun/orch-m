#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
from util import db_sql
from handler import rrl_handler as rrl
from msg import mon_msg

from datetime import datetime
import os, fcntl, yaml
import json


TITLE = 'orchm'

import logging
from api import oba_api
logger = logging.getLogger(TITLE)




def registerPlugIn( targetSeq, gSeq, params, dbm ):
    """
    - FUNC: PlugIn 등록
    - INPUT
        targetSeq(M): 모니터링 TargetSeq
        gSeq(M): 모니터링 GroupSeq
        params(M): PlugIn 파라미터
            Mandatory: name, type, target_seq
            Option: script, group_seq, plugin_param, param_num, description, 
                lib_type, lib_script, lib_path, lib_name
                cfg_path, cfg_name, cfg_input 
        dbm(M): DB 연결 객체
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Register PlugIn'
    try:
        pName = params['name']
        pType = str(params['type']).lower()
        script = params['script']
        targetSeq = str(targetSeq)
        
        groupSeq = pluginParam = description = None
        
        if gSeq != None:     groupSeq = str(gSeq)
        if params.has_key('plugin_param'):
            paramList = []
            for _param in params['plugin_param'] :
                paramList.append( str(_param) )
            pluginParam = str(paramList).replace( """'""", '"')
        if params.has_key('description'):   description = str(params['description'])
            
        if pType == 'builtin' :
            getPluginSql = db_sql.GET_PLUGIN_BUILTIN( pName, script, description )
        else :
            getPluginSql = db_sql.GET_PLUGIN_NOBUILTIN( script, targetSeq, groupSeq, pluginParam )
        
        ret = dbm.select( getPluginSql )
        if  len(ret) > 0 :
            rres = rrl.rFa(None, rrl.RS_DUPLICATE_DATA, 'PlugIn Duplicated', ret, 
                {'script':script, 'target_seq':targetSeq, 'group_seq':groupSeq, 'plugin_param':pluginParam})
            logger.error( rres.lF(FNAME) )
            return rres
        
        paramNum = libType = libScript = libPath = libName = None
        cfgPath = cfgName = cfgInput = discoveryCfg = inputList = None
        if params.has_key('lib_type'):      libType = str(params['lib_type'])
        if params.has_key('lib_script'):    libScript = str(params['lib_script'])
        if params.has_key('lib_path'):      libPath = str(params['lib_path'])
        if params.has_key('lib_name'):      libName = str(params['lib_name'])
        if params.has_key('cfg_path'):      cfgPath = str(params['cfg_path'])
        if params.has_key('cfg_name'):      cfgName = str(params['cfg_name'])
        if params.has_key('cfg_input'):
            inputList = []
            for _input in params['cfg_input'] :
                inputList.append( str(_input) )
        if params.has_key('param_num'):
            paramNum = str(params['param_num'])
        else:
            paramNum = 0
        
        if libType != None and str(libType).lower() != 'builtin' :
            if str(libType).lower() == 'text' :
                if libName == None or libPath == None or libScript == None :
                    rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Plugin LibInfo Error', None, 
                        {'name':pName, 'lib_type':libType, 'lib_name':libName, 'lib_path':libPath, 'lib_script':libScript})
                    logger.error( rres.lF(FNAME) )
                    return rres
            else:
                if libScript == None:
                    rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Plugin LibInfo Error', None, 
                        {'name':pName, 'lib_type':libType, 'lib_script':libScript})
                    logger.error( rres.lF(FNAME) )
                    return rres
                else:
                    if libName == None : libName = os.path.basename( libScript )
                    if libPath == None : libPath = './'
        
        if cfgName == None :
            if ( cfgPath != None or inputList != None ) :
                rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'Plugin CfgInfo Error', None, 
                    {'name':pName, 'cfg_name':cfgName, 'cfg_path':cfgPath, 'cfg_input':inputList})
                logger.error( rres.lF(FNAME) )
                return rres
        else:
            if cfgPath == None : cfgPath = './'
        
        if params.has_key('discovery_input') and str(params['discovery_input']) != '':
            discoveryCfg = str(params['discovery_input'])
            getPluginDiscoverySql = db_sql.GET_PLUGIN_DISCOVERY_BY_TARGET( targetSeq, discoveryCfg )
            ret = dbm.select( getPluginDiscoverySql )
            if len(ret) > 0 :
                rres = rrl.rFa(None, rrl.RS_DUPLICATE_DATA, 'DiscoveryCfg Duplicated', None, 
                    {'target_seq':targetSeq, 'disc_cfg':discoveryCfg})
                logger.error( rres.lF(FNAME) )
                return rres
        
        if cfgName != None :
            getCfgInput = db_sql.GET_PLUGIN_CFGINPUT( targetSeq, cfgName, cfgPath )
            ret = dbm.select( getCfgInput, 'cfg_input' )
            cfgInputList = []
            if ret != None and len(ret) > 0 :
                for cfgInputGroup in ret :
                    if cfgInputGroup == None or cfgInputGroup == '' :
                        continue
                    try:
                        cigList = json.loads(cfgInputGroup)
                        for ci in cigList :
                            if not str(ci) in cfgInputList :
                                cfgInputList.append( str(ci) )
                    except Exception, e:
                        rres = rrl.rFa(None, rrl.RS_EXCP, 'PlugIn Input Update Error', None, cfgInputGroup)
                        logger.error( rres.lF(FNAME) )
                        logger.fatal(e)
                        return rres
            
            for cfgI in inputList :
                if not str(cfgI) in cfgInputList:
                    cfgInputList.append( str(cfgI) )
            
            cfgInput = str(cfgInputList).replace("""'""", '"')
            updateCfgInput = db_sql.UPDATE_PLUGIN_CFGINPUT( targetSeq, cfgName, cfgPath, cfgInput )
            ret = dbm.execute( updateCfgInput )
            
        insertPluginSql = db_sql.INSERT_PLUGIN_DATA( pName, pType, targetSeq, groupSeq, 
                                          script, paramNum, description,
                                          libType, libScript, libPath, libName, 
                                          cfgPath, cfgName, cfgInput,
                                          pluginParam, discoveryCfg )
        pluginSeq = dbm.execute( insertPluginSql, True )
        if  pluginSeq == None :
            rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Insert PlugInData Error', None, insertPluginSql)
            logger.error( rres.lF(FNAME) )
            return rres
        
        return rrl.rSc(None, pluginSeq, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, params)
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres


def removePlugIn( tid, pluginCatSeq ):
    """
    - FUNC: PlugIn 등록 해제( 구현 예정 )
    - INPUT
        tid(M): 요청 TID
        pluginCatSeq(M): PlugIn Catalog Seq
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Remove PlugIn'
    try:
#         ret = dbm.execute( db_sql.DEL_PLUGIN_BY_SEQ(str(pluginCatSeq)) )
        return rrl.rFa( tid, rrl.RS_UNSUPPORTED_FUNC, None, None, pluginCatSeq)
#         logger.info( 'Success: Remove PlugIn, name=%s'%pName )
#         return True
    except Exception, e:
        rres = rrl.rFa(tid, rrl.RS_EXCP, e, None, pluginCatSeq)
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres



def sendPlugIn_first_notify( rbDB, oba_ip, oba_port, svrSeq, targetSeq):
    """
    - 2017.10.12 - lsh
    - FUNC: 설변후 obj 추가, 제거, cfg 파일 전송
    - INPUT
        rbDB(M): DB 연결 객체
        oba_ip
        oba_port(M): OBAgent 포트
        svrseq,1
        targetseq
    - OUTPUT
        result: rrl_handler._ReqResult
    """

    ## plugin 파일/Text  전송
    FNAME = 'sendPlugIn first notify'


    sendedlist = []

    ret=rbDB.select(db_sql.GET_PLUGIN_INFO (svrSeq, targetSeq))

    for plugin in ret:
        dstName = plugin['pluginpath']

        fn=plugin['script']
        _type=plugin['type']

        # logger.info('oba_ip1 : %s' % oba_ip)
        if str(_type).upper() == 'FILE':
            # dstName=os.path.join(pluginPath, os.path.basename(fn))

            if fn in sendedlist : 
                logger.info('PASS ' + fn ) 
            else : 
                logger.info ( "1. sendFile :  %s, %s " % (fn, dstName) )
                rres=oba_api.sendFile(fn, dstName, oba_ip, oba_port, './backup')
                if rres.isFail():
                    rres=rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending PlugInFile Error', None,
                                {'org_name': fn, 'dst_name': dstName})
                    logger.error(rres.lF(FNAME))
                    return rres
                else :
                    # 중복전송 방지
                    sendedlist.append(fn)

        else:
            # fname=targetSeq + "-plugin-" + str(datetime.now().strftime("%Y%m%d_%H:%M:%S"))
            # dstName=os.path.join(pluginPath, os.path.basename(fname))
            data=fn
            #logger.info ( "2. sendFile :  %s, %s " % (fn, dstName) )
            rres=oba_api.sendData(data, dstName, oba_ip, oba_port, './backup')
            if rres.isFail():
                rres=rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending PlugIn Data Error', None,
                            {'data': data, 'dst_name': dstName})
                logger.error(rres.lF(FNAME))
                return rres


    ret=rbDB.select(db_sql.GET_PLUGIN_LIB(svrSeq, targetSeq))
    ## 라이브러리 파일 전송
    for lib in ret:
        # pSeq=lib['monplugincatseq']
        fn=lib['libname']
        _type=lib['libtype']
        path=lib['libpath']
        script=lib['libscript']
        if os.path.isabs(path):
            dstName=path
        else:
            dstName=os.path.basename(fn)

        if str(_type).upper() == 'FILE':
            orgName=script
            #logger.info ( "3. sendFile :  %s, %s " % (fn, dstName) )
            rres=oba_api.sendFile(orgName, dstName, oba_ip, oba_port, './backup')
            if rres.isFail():
                rres=rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending Lib File Error', None,
                            {'org_name': orgName, 'dst_name': dstName})
                logger.error(rres.lF(FNAME))
                return rres
        else:
            data=script
            #logger.info ( "4. sendFile :  %s, %s " % (fn, dstName) )
            rres=oba_api.sendData(data, dstName, oba_ip, oba_port, './backup')
            if rres.isFail():
                rres=rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending Lib Data Error', None,
                            {'data': data, 'dst_name': dstName})
                logger.error(rres.lF(FNAME))
                return rres


    ## 설정 데이터 생성 및 전송, cfgname, cfgpath, cfg_input
    selSql=db_sql.GET_PLUGIN_INST_CFG_BY_TARGET(svrSeq, targetSeq)
    CfgList=rbDB.select(selSql)
    if ret == None:
        rres=rrl.rFa(None, rrl.RS_FAIL_DB, 'First_Notify Getting PlugInCfg Error', None, selSql)
        logger.error(rres.lF(FNAME))
        return rres

    for cfg in CfgList:
        cfgpath=cfg['cfgpath']
        cfgdata=yaml.safe_load(cfg['cfgdata'])
        if cfgdata is None:
            continue

        sendData=yaml.safe_dump(cfgdata, encoding='utf-8', default_flow_style=False, allow_unicode=True)
        rres=oba_api.sendData(sendData, cfgpath, oba_ip, oba_port, './backup')
        if rres.isFail():
            rres=rrl.rFa(None, rrl.RS_API_OBA_ERR, 'First_Notify Sending Cfg Data Error', None,
                         {'sendData': sendData, 'cfgpath': cfgpath})
            logger.error(rres.lF(FNAME))
            return rres

        #logger.info("5. sendFile :  %s, %s " % (cfgpath, sendData))


def sendPlugIn( _monInfo, dbm, oba_port, defaultData={}):
    """
    - FUNC: PlugIn 파일 전송 및 결과 저장
    - INPUT
        _monInfo(M): 요청 파라미터
        dbm(M): DB 연결 객체
        oba_port(M): OBAgent 포트
        defaultData(O): PlugIn 기본 설정 데이터
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Send PlugIn'
    
    logger.info( 'Sending PlugIn To One-Box' )
    monInfo = mon_msg.MonInfo
    if _monInfo != None :
        monInfo = _monInfo
    else:
        rres = rrl.rFa(None, rrl.RS_NO_PARAM, 'No PlugIn Param', None, None)
        logger.error( rres.lF(FNAME) )
        return rres
    
    svrSeq = monInfo.svrInfo.svrSeq
    ip = monInfo.svrInfo.svrIP
    
    sendedlist = []

    try:
        for targetInfo in monInfo.targetList :
            targetSeq = str(targetInfo.targetSeq)
            pluginPath = str(targetInfo.targetPluginPath)
            targetCfg = None
            if targetInfo.targetCfg != None :
                targetCfg = targetInfo.targetCfg

            ## plugin 파일/Text  전송
            ret = dbm.select( db_sql.GET_PLUGIN_BY_TARGET(targetSeq) )
            for plugin in ret :
                pSeq = plugin['monplugincatseq']
                groupSeq = plugin['mongroupcatseq']
                fn = plugin['script']
                _type = plugin['type']
                dstName = None

                if str(_type).upper() == 'FILE':
                    dstName = os.path.join( pluginPath, os.path.basename( fn ) )
                    # 2019. 3.5 - lsh
                    # 중복으로 전송하는 경우가 잦음. 한번 전송된것은 다시 안보내도록
                    if fn in sendedlist : 
                        logger.info('PASS ' + fn ) 
                    else :
                        rres = oba_api.sendFile( fn, dstName, ip, oba_port, './backup' )
                        if rres.isFail() :
                            rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending PlugInFile Error', None, {'org_name':fn, 'dst_name':dstName})
                            logger.error( rres.lF(FNAME) )
                            return rres
                        else :
                            # 중복전송 방지
                            sendedlist.append(fn)

                else :
                    fname = targetSeq + "-plugin-" + str(datetime.now().strftime("%Y%m%d_%H:%M:%S"))
                    dstName = os.path.join( pluginPath, os.path.basename( fname ) )
                    data = fn
                    # 2019. 3.5 - lsh
                    # 중복으로 전송하는 경우가 잦음. 한번 전송된것은 다시 안보내도록
                    if fn in sendedlist : 
                        logger.info('PASS ' + fn ) 
                    else :
                        rres = oba_api.sendData( data, dstName, ip, oba_port, './backup' )
                        if rres.isFail() :
                            rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending PlugIn Data Error', None, {'data':data, 'dst_name':dstName})
                            logger.error( rres.lF(FNAME) )
                            return rres
                        else :
                            # 중복전송 방지
                            sendedlist.append(fn)

            
                # svrSeq, pseq, targetSeq, groupSeq, pluginPath 
                dbm.execute( db_sql.INSERT_PLUGIN_INST( svrSeq, pSeq, targetSeq, groupSeq, dstName ) )


            ## 라이브러리 파일 전송
            ret = dbm.select( db_sql.GET_PLUGIN_LIB_BY_TARGET(targetSeq) )
            for lib in ret :
                pSeq= lib['monplugincatseq']
                fn = lib['libname']
                _type = lib['libtype']
                path = lib['libpath']
                script = lib['libscript']
                if os.path.isabs( path ) :
                    dstName = os.path.join( path, os.path.basename( fn ) )
                else:
                    dstName = os.path.join( os.path.normpath( pluginPath+'/'+path ), os.path.basename( fn ) )

                if str(_type).upper() == 'FILE':
                    orgName = script
                    # 2019. 3.5 - lsh
                    # 중복으로 보내는경우가 너무 많다. 한번 보낸건 다시 안보내도록
                    if script in sendedlist : 
                        logger.info('PASS ' + script ) 
                    else :
                        rres = oba_api.sendFile( orgName, dstName, ip, oba_port, './backup' )
                        if rres.isFail() :
                            rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending Lib File Error', None, {'org_name':orgName, 'dst_name':dstName})
                            logger.error( rres.lF(FNAME) )
                            return rres
                        else :
                            # 중복전송 방지
                            sendedlist.append(script)
                else :
                    data = script
                    if script in sendedlist : 
                        logger.info('PASS ' + script ) 
                    else :
                        rres = oba_api.sendData( data, dstName, ip, oba_port, './backup' )
                        if rres.isFail() :
                            rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending Lib Data Error', None, {'data':data, 'dst_name':dstName})
                            logger.error( rres.lF(FNAME) )
                            return rres
                        else :
                            # 중복전송 방지
                            sendedlist.append(orgName)
            
                # svrSeq, pluginSeq, libPath
                dbm.execute( db_sql.UPDATE_PLUGIN_INST_LIB( svrSeq, pSeq, dstName ) )
            
            ## 설정 데이터 생성 및 전송, cfgname, cfgpath, cfg_input
            if targetCfg != None:
                ret = dbm.select( db_sql.GET_PLUGIN_CFG_BY_TARGET(targetSeq) )
                for cfg in ret:
                    pSeq= cfg['monplugincatseq']
                    fn = cfg['cfgname']
                    path = cfg['cfgpath']
                    _inputs = cfg['cfg_input']
                    if _inputs is None :
                        continue
                    
                    inputs = json.loads( _inputs )
                    if os.path.isabs( path ) :
                        dstName = os.path.join( path, os.path.basename( fn ) )
                    else:
                        dstName = os.path.join( os.path.normpath( pluginPath+'/'+path ), os.path.basename( fn ) )
                    
                    _data = {}
                    for _input in inputs :
                        if targetCfg.has_key(_input) :
                            _data[ _input ] = targetCfg[_input]
                        elif defaultData.has_key(_input):
                            _data[ _input ] = defaultData[_input]
                    
                    data = yaml.safe_dump( _data, encoding='utf-8', default_flow_style=False, allow_unicode=True )
                    data = str(data).replace("""'""", '"')
                    # 2019. 3.5 - lsh
                    # 중복으로 보내는경우가 너무 많다. 한번 보낸건 다시 안보내도록
                    if dstName in sendedlist : 
                        logger.info('PASS ' + dstName ) 
                    else :
                        rres = oba_api.sendData( data, dstName, ip, oba_port, './backup' )
                        if rres.isFail() :
                            rres = rrl.rFa(None, rrl.RS_API_OBA_ERR, 'Sending Cfg Data Error', None, {'data':data, 'dst_name':dstName})
                            logger.error( rres.lF(FNAME) )
                            return rres
                        else : 
                            sendedlist.append(dstName)

                    # svrSeq, pluginSeq, dstCfgPath, cfgData
                    dbm.execute( db_sql.UPDATE_PLUGIN_INST_CFG( svrSeq, pSeq, dstName, data ) )
    
        return rrl.rSc(None, None, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, monInfo)
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres


def modPlugInMod( rbDB, svrSeq, lanname, objname, _type,  oba_port ):

    FNAME = 'modPlugInMod'
    rres = ''

    # 서버 IP 가져오기
    strsql=db_sql.GET_SVR_IP(svrSeq)
    ret=rbDB.select(strsql)

    if ret == None or len(ret) != 1:
        rbDB.rollback()
        rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'Get CFG Error', ret, {'svrSeq': strsql})
        logger.error(rres.lF(FNAME))
        return rres

    ip = ret[0]['mgmtip']

    isPNF = str(ret[0]['nfsubcategory']).lower() == 'ktpnf'

    # 설변, eth 추가후 os, utm 쪽 config 파일 재 전송
    # wan 이면 2번 루프, OS, UTM 쪽 eth 를 추가 or 삭제한다.
    strsql=db_sql.GET_PLUGIN_CFG(svrSeq)

    # logger.info ( "GET_PLUGIN_CFG SQL : %s"  % strsql  )

    ret=rbDB.select(strsql)

    if ret == None or len(ret) == 0 :
        # 에러 아님. DB 값이 없음.
        return rrl.rSc(None, FNAME , None)


    keylist = ['vm_net']

    # ExtraWAN 은 OS 쪽 플러그인만 추가, 제거,  VM 제외
    if lanname.lower() == 'extra_wan' :
        keylist[0] = 'svr_net'

    # WAN 은 OS 쪽, UTM 쪽 두곳 모두 추가, 제거 반영
    elif lanname.lower() == 'wan' :
        keylist.append (  'svr_net' )
        
    # 2019. 3.12 - lsh
    # PNF 일때도 conf 두번 전송 OS 와 UTM의 ether 설정이 같다.
    elif isPNF :
        keylist.append (  'svr_net' )


    for r in ret:
        cfgPath=(lambda x: str(x['cfgpath']) if x.has_key('cfgpath') else "")(r)
        cfgData=(lambda x: str(x['cfgdata']) if x.has_key('cfgdata') else "")(r)
        # cfgPath=r['cfgpath']
        # cfgData=r['cfgdata']
        if cfgPath == "" :
            continue

        # logger.info ( "cfgPath, cfgdata : %s, %s"  % (cfgPath, cfgData ) )

        yamlData=yaml.safe_load(cfgData)

        # yamlData 에 Key값이 있나?
        for key in keylist :
            if key in yamlData :
                for y in yamlData[key]:
                    if y == objname:
                        # 기존 eth0 삭제.
                        logger.info ( "remove : %s"  % objname ) 

                        yamlData[key].remove(objname)
                # 추가
                if _type == 'A' :
                    yamlData[key].append ( objname )

                # 설변시 OBA 재구동으로 인해 Connect 오류생김
                # 1분 정도 재시도
                sendData=yaml.safe_dump(yamlData, encoding='utf-8', default_flow_style=False, allow_unicode=True)
                sendData=str(sendData).replace("""'""", '"')

                logger.info ( "cfgPath, cfgdata : %s, %s"  % (cfgPath, sendData ) )

                rres=oba_api.sendData(sendData, cfgPath, ip, oba_port, './backup')

                if rres.isFail():
                    logger.error(rres.lF(FNAME))
                    return rres

                # logger.info ( "UPDATE_PLUGIN_INST_CFG_FOR_MOD : %s, %s, %s"  % (svrSeq, cfgPath, sendData) )
                ## 변경 설정 저장
                ret = rbDB.execute(db_sql.UPDATE_PLUGIN_INST_CFG_FOR_MOD(svrSeq, cfgPath, sendData))
                if ret == None or ret < 1:
                    rres=rrl.rFa(tid, rrl.RS_FAIL_DB, 'UPDATE_PLUGIN_INST_CFG_FOR_MOD Error', ret, {'svrSeq': svrSeq})
                    logger.error(rres.lF(FNAME))
                    return rres

    return rres

def modPlugInDiscList( rbDB, svrSeq, icSeq, iObjList, oba_port ):
    """
    - FUNC: Discovery PlugIn의 설정 파일 변경(Monitor Object 변경 기능)
    - INPUT
        rbDB(M): DB 연결 객체
        svrSeq(M): 서버 Seq
        icSeq(M): 감시 아이템 카탈로그 Seq
        iObjList(M): 감시 아이템의 Object 리스트
        oba_port(M): OBAgent 포트
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Modify PlugIn DiscoveryList'
    try:
        ## 기존 데이터 가져오기
        getPluginInfo = db_sql.GET_PLUGIN_CFG_FOR_MOD_OBJ( svrSeq, icSeq )

        # logger.info ( 'getPluginInfo : %s ' % getPluginInfo)

        ret = rbDB.select( getPluginInfo )
        if ret == None or len(ret) < 1 :
            if ret == None :
                rs = rrl.RS_FAIL_DB
            else:
                rs = rrl.RS_NO_DATA
            rres = rrl.rFa(None, rs, 'Getting PlugInCfg Error', None, getPluginInfo)
            logger.error( rres.lF(FNAME) )
            return rres


        ## 유효성 체크
        ip = ret[0]['mgmtip']
        dCfgInput = ret[0]['discovery_cfg_input']
        cfgPath = ret[0]['cfgpath']
        cfgData = ret[0]['cfgdata']
        
        if ip == None or dCfgInput == None or cfgPath == None or cfgData == None :
            rres = rrl.rFa(None, rrl.RS_INVALID_DATA, None, None, 
                           {'svr_ip':ip, 'disc_cfg_input':dCfgInput, 'cfg_path':cfgPath, 'cfg_data':cfgData})
            logger.error( rres.lF(FNAME) )
            return rres
        
        ## 변경 설정 전송
        yamlData = yaml.safe_load( cfgData )
        yamlData[dCfgInput] = iObjList
        sendData = yaml.safe_dump( yamlData, encoding='utf-8', default_flow_style=False, allow_unicode=True )
        sendData = str(sendData).replace("""'""", '"')
        rres = oba_api.sendData( sendData, cfgPath, ip, oba_port, './backup' )

        if rres.isFail() :
            logger.error( rres.lF(FNAME) )
            return rres
        
        ## 변경 설정 저장
        rbDB.execute( db_sql.UPDATE_PLUGIN_INST_CFG_FOR_MOD( svrSeq, cfgPath, sendData ) )
        
        return rrl.rSc(None, None, {'svr_seq':svrSeq, 'item_cat_seq':icSeq, 'item_obj_list':iObjList})
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'svr_seq':svrSeq, 'item_cat_seq':icSeq, 'item_obj_list':iObjList})
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres

def updatePlugInCfg( dbm, svrSeq, targetList, oba_port ):
    """
    - FUNC: PlugIn의 설정 파일 변경
    - INPUT
        dbm(M): DB 연결 객체
        svrSeq(M): 서버 Seq
        targetList(M): 요청 파라미터
        oba_port(M): OBAgent 포트
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Update PlugIn Cfg'
    try:
        svrIP = dbm.select( db_sql.GET_SVR_IP(svrSeq), 'mgmtip' )
        svrIP = svrIP[0]
        
        for targetInfo in targetList:
            if not targetInfo.has_key('cfg'):
                continue
            
            targetSeq = targetInfo['target_seq'] 
            cfgInfo = targetInfo['cfg']
            selSql = db_sql.GET_PLUGIN_INST_CFG_BY_TARGET( svrSeq, targetSeq )
            _prevCfgList = dbm.select( selSql )
            if _prevCfgList == None :
                rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Getting PlugInCfg Error', None, selSql)
                logger.error( rres.lF(FNAME) )
                return rres
            
            ## 비교
            for _prevCfg in _prevCfgList:
                prevCfgPath = _prevCfg['cfgpath'] 
                prevCfg = yaml.safe_load( _prevCfg['cfgdata'] )
                for cfgParam in cfgInfo.keys():
                    if prevCfg.has_key(cfgParam):
                        prevCfg[cfgParam] = cfgInfo[cfgParam]
                sendData = yaml.safe_dump( prevCfg, encoding='utf-8', default_flow_style=False, allow_unicode=True )
                rres = oba_api.sendData( sendData, prevCfgPath, svrIP, oba_port, './backup' )
                if rres.isFail() :
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                sendData = str(sendData).replace("""'""", '"')
                updSql = db_sql.UPDATE_PLUGIN_INST_CFG_FOR_MOD( svrSeq, prevCfgPath, sendData )
                ret = dbm.execute( updSql )
                if ret == None:
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Updating PlugInCfg Error', None, updSql)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
            ## 다른 설정 배포
        
        rres = rrl.rSc(None, None, {'svr_ip':svrIP})
        logger.info( rres.lS(FNAME) )
        return rres
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, {'svr_seq':svrSeq, 'target_info':targetList})
        logger.error( rres.lF(FNAME) )
        logger.fatal( e )
        return rres
        
# def add_extra_plugin( dbm, svrSeq, targetSeq, groupSeq, pluginInfo, oba_port ):
#     try:
#         def getVal( _param, _key):
#             return (lambda x: x[_key] if x.has_key(_key) else None)(_param)
#         
#         pluginName = pluginInfo['name']
#         pluginType = pluginInfo['type']
#         pluginScript = pluginInfo['script']
#         pluginParamNone = getVal( pluginInfo, 'param')
#         if pluginParamNone != None :
#             paramList = []
#             for _param in pluginParamNone :
#                 paramList.append( str(_param) )
#             pluginParamNone = str(paramList).replace( """'""", '"')
#         
#         ## 중복 체크    
#         ret = dbm.select( db_sql.GET_PLUGIN_INST_FOR_ADD_EXTRA(svrSeq, targetSeq, pluginScript, pluginParamNone ) )
#         if ret != None and len(ret) > 0:
#             logger.error( 'Duplicated PluginInstance Info, prev=%s'%str(ret) )
#             return ec.getErr( ec.DUPLICATE_DATA, pluginInfo )
#         
#         
#         pluginParamNumNone = getVal( pluginInfo, 'param_num')
#         pluginDescNone = getVal( pluginInfo, 'description')
#         pluginLibName = getVal( pluginInfo, 'lib_name')
#         pluginLibTypeNone = getVal( pluginInfo, 'lib_type')
#         pluginLibScriptNone = getVal( pluginInfo, 'lib_script')
#         pluginLibPathNone = getVal( pluginInfo, 'lib_path')
#         pluginCfgNameNone = getVal( pluginInfo, 'cfg_name')
#         pluginCfgPathNone = getVal( pluginInfo, 'cfg_path')
#         plugincfgInputNone = getVal( pluginInfo, 'cfg_input')
#         plugincfgDiscInputNone = getVal( pluginInfo, 'discovery_input')
#     except Exception, e:
#         logger.fatal(e)
#         return ec.getErr( ec.EXCP, e )








