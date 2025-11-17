#-*- coding: utf-8 -*-

from handler import rrl_handler as rrl
from msg import mon_msg

import logging, yaml
from util import logm, db_sql


TITLE = 'orchm'

PNF_PLUGIN_PATH = ''

logger = logging.getLogger(TITLE)
logm.init(logName='orchm-log', logDir='./log', logFile='myLogger.log')

TMP_CFG = './cfg/tmp_params.cfg'

def setTmpOsParams( cfgInfo ):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)
    if not cfgInfo.has_key('svr_svc'):
        logger.info ('svr_svc :   %s ' % str(cfgf['svr_svc']))
        cfgInfo['svr_svc'] = cfgf['svr_svc'] #['zabbix-agent', 'onebox-agent', 'onebox-vnfm', 'nova-api', 'apache2', 'neutron-server', 'glance-api']
    if not cfgInfo.has_key('svr_proc'):
        cfgInfo['svr_proc'] = cfgf['svr_proc'] #['rabbitmq-server', '/usr/sbin/mysqld']
    if not cfgInfo.has_key('svr_fs'):
        cfgInfo['svr_fs'] = cfgf['svr_fs'] #['/']

def setTmpUtmParams( targetSeq, dbm, cfgInfo, mappingInfo, wan_if_num = 1):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)

    multiport_items = ['eth5' , 'eth6', 'eth7']  # UTM의 회선 이중화시 두번째 이상 wan 회선에서 사용하는 vNIC 이름

    sql = """ SELECT vendorcode, targetmodel FROM tb_montargetcatalog WHERE montargetcatseq=%s """ %str(targetSeq)
    ret = dbm.select( sql )
    vendorCode = str(ret[0]['vendorcode']).lower()
    targetModel = ret[0]['targetmodel']
    if cfgf.has_key('utm') :
        for utmInfo in cfgf['utm'] :
            if utmInfo.has_key('vendor') :
                
                ## vendorCode, vnfModel 일치할 경우
                if (str(utmInfo['vendor']).lower() == str(vendorCode).lower() ) and \
                    list(utmInfo['model']).count( targetModel ) > 0 :
                    
                    if utmInfo.has_key('cfg') :
                        _cfg = dict(utmInfo['cfg'])
                        
                        cfgKey = _cfg.keys()
                        for cKey in cfgKey :
                            if not cfgInfo.has_key(cKey):
                                cfgInfo[cKey] = _cfg[cKey]

                    if utmInfo.has_key('mapping') :
                        utmMapping = dict(utmInfo['mapping'])
                        
                        mappingKey = utmMapping.keys()
                        for mKey in mappingKey :
                            mappingInfo[mKey] = [utmMapping[mKey]]  # 회선 이중화를 위해서 목록으로 등록한다.

                        if wan_if_num > 1:  # 회선 이중화
                            for idx in range(0, wan_if_num - 1):
                                vNIC = multiport_items[idx]
                                cfgInfo['vm_net'].append(vNIC)

                                mappingInfo['utm.wan.rx'].append(vNIC)
                                mappingInfo['utm.wan.tx'].append(vNIC)
                    break

def setTmpPnfUtmParams( targetSeq, dbm, cfgInfo, mappingInfo, wan_if_num = 1):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)

    # multiport_items = ['eth5' , 'eth6', 'eth7']  # UTM의 회선 이중화시 두번째 이상 wan 회선에서 사용하는 vNIC 이름

    sql = """ SELECT vendorcode, targetmodel FROM tb_montargetcatalog WHERE montargetcatseq=%s """ %str(targetSeq)
    ret = dbm.select( sql )
    vendorCode = str(ret[0]['vendorcode']).lower()
    targetModel = ret[0]['targetmodel']

    if cfgf.has_key('utm') :
        for utmInfo in cfgf['utm'] :
            if utmInfo.has_key('vendor') :
                ## vendorCode, vnfModel 일치할 경우
                if (str(utmInfo['vendor']).lower() == str(vendorCode).lower() ) and \
                    list(utmInfo['model']).count( targetModel ) > 0 :
                    if utmInfo.has_key('cfg') :
                        _cfg = dict(utmInfo['cfg'])
                        cfgKey = _cfg.keys()
                        for cKey in cfgKey :
                            if not cfgInfo.has_key(cKey):
                                cfgInfo[cKey] = _cfg[cKey]

                    if utmInfo.has_key('mapping') :
                        utmMapping = dict(utmInfo['mapping'])
                        
                        mappingKey = utmMapping.keys()
                        for mKey in mappingKey :
                            mappingInfo[mKey] = [utmMapping[mKey]]  # 회선 이중화를 위해서 목록으로 등록한다.

                    break

def setTmpWafParams( cfgInfo ):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)
    if not cfgInfo.has_key('vm_net'):
        cfgInfo['vm_net'] = cfgf['waf_net'] #['eth0', 'eth1']

def setTmpApcParams( cfgInfo ):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)
    if not cfgInfo.has_key('vm_net'):
        cfgInfo['vm_net'] = cfgf['apc_net'] #['eth1']
    if not cfgInfo.has_key('vm_fs'):
        cfgInfo['vm_fs'] = cfgf['apc_fs'] #['/']
    if not cfgInfo.has_key('vm_proc'):
        cfgInfo['vm_proc'] = cfgf['apc_proc'] 
#         ['Wac_ce.jar', 'Wac_nei.jar', 'Wac_emp.jar', 'Wac_dbg.jar',
#                      'Wac_stm.jar', 'Wac_unm.jar', 'Wac_scp.jar', 'Wac_pm.jar',
#                      'Wac_rsm.jar', 'wtd_mgr', 'fork_mgr', 'sm_mgr', 'as_mgr',
#                      'at_mgr', 'sv_mgr']
#
def setTmpPbxParams( cfgInfo ):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)
    if not cfgInfo.has_key('vm_net'):
        cfgInfo['vm_net'] = cfgf['pbx_net'] #['eth0', 'eth1', 'eth2', 'eth3']


def setTmpXmsParams( cfgInfo ):
    with open(TMP_CFG, "r") as f:
        cfgf = yaml.load(f)
    if not cfgInfo.has_key('vm_net'):
        cfgInfo['vm_net'] = cfgf['xms_net'] #['eth0', 'eth1', 'eth2', 'eth3']
    if not cfgInfo.has_key('vm_fs'):
        cfgInfo['vm_fs'] = cfgf['xms_fs'] #['/']
    if not cfgInfo.has_key('vm_proc'):
        cfgInfo['vm_proc'] = cfgf['xms_proc'] #['/home/onebox/tomcat/bin/bootstrap.jar']


## TBD
def convertTemplateAddParam( _monInfo ):
    """
    - FUNC: Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
    - INPUT
        _monInfo(M): Orch-F로부터 받은 API Parameter
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    monInfo = _monInfo
    return rrl.rSc(None, monInfo, None)

## TBD
def convertOneTouchParam( params ):
    """
    - FUNC: Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
    - INPUT
        params(M): Orch-F로부터 받은 API Parameter
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    _params = params
    return rrl.rSc(None, _params, None)

def convertProvisionParam( dbm, _monInfo, monitorAt, defaultPluginPath ):
    """
    - FUNC: Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
    - INPUT
        dbm(M): DB Connection 객체
        _monInfo(M): Orch-F로부터 받은 API Parameter
        monitorAt(M): 모니터링 시작 시점(OneTouch, Provisioning)
        defaultPluginPath(M): One-Box에 설치될 플러그인 파일의 Default 경로
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Convert ProvParam'
    monInfo = mon_msg.MonInfo
    if _monInfo != None :
        monInfo = _monInfo
    try:
        targetInfo = mon_msg.TargetInfo
        for targetInfo in monInfo.targetList:
            ## Target Sequence 가 없는 대상은 대상 정보로 target_seq를 얻어옴
            if targetInfo.targetSeq == None :

                _monitorAt = (lambda x: x if x != None else monitorAt)(targetInfo.targetFor)
                targetVer = targetInfo.targetVer
                vdudSeq = targetInfo.targetVdudSeq
                strsql = db_sql.GET_TARGET_FOR_CREATE( targetInfo.targetCode, targetInfo.targetType,
                                targetInfo.targetVendor, targetInfo.targetModel, targetVer, vdudSeq, _monitorAt )

                logger.info ('convertProvisionParam - GET_TARGET_FOR_CREATE : %s ' % strsql )

                ret = dbm.select( strsql )

                if ret == None or len(ret) < 1:
                    if ret == None: rs = rrl.RS_FAIL_DB
                    else: rs = rrl.RS_NO_DATA
                    rres = rrl.rFa(None, rs, 'Getting TargetSeq Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                targetInfo.targetSeq = ret[0]['montargetcatseq']
            else:
                if targetInfo.targetSeq == None:
                    rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, 'No TargetSeq', None, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
            
            if targetInfo.targetPluginPath == None :
                ret = dbm.select( db_sql.GET_PLUGIN_PATH( targetInfo.targetSeq ) )
                if ret == None or len(ret) != 1:
                    if ret == None: rs = rrl.RS_FAIL_DB
                    else: rs = rrl.RS_INVALID_DATA
                    rres = rrl.rFa(None, rs, 'Getting PluginPath Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres

                if targetInfo.targetCode == 'pnf' and targetInfo.targetVendor == 'axgate' : 
                    defaultPluginPath = PNF_PLUGIN_PATH 

                if monInfo.svrInfo.onebox_type == 'KtPnf' :
                    defaultPluginPath = PNF_PLUGIN_PATH 

                targetInfo.targetPluginPath = defaultPluginPath + '/' + ret[0]['path']
            
            ###### 임시 설정 
            if targetInfo.targetCfg != None :
                
                ret = dbm.select( db_sql.GET_TARGET_INFO( targetInfo.targetSeq ) )
                if ret == None or len(ret) < 1:
                    if ret == None: rs = rrl.RS_FAIL_DB
                    else: rs = rrl.RS_NO_DATA
                    rres = rrl.rFa(None, rs, 'Getting TargetInfo Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                if targetInfo.targetCode == None :
                    targetInfo.targetCode = ret[0]['targetcode']
                if targetInfo.targetType == None : 
                    targetInfo.targetType = ret[0]['targettype']
                
                cfgInfo = targetInfo.targetCfg
                if str(targetInfo.targetCode).upper() == 'OS' :
                    setTmpOsParams(cfgInfo)
                
                elif str(targetInfo.targetCode).upper() in [ 'VNF'] :
                    tType = str(targetInfo.targetType).upper()
                    if tType == 'UTM' :
                        setTmpUtmParams(targetInfo.targetSeq, dbm, cfgInfo, targetInfo.targetMapping, targetInfo.targetWanIfNum)
                        logger.debug( targetInfo.targetMapping )
                    elif tType == 'WAF' :
                        setTmpWafParams(cfgInfo)
                    elif tType == 'WIFI-AC' :
                        setTmpApcParams(cfgInfo)
                    elif tType == 'XMS' :
                        setTmpXmsParams(cfgInfo)
                    elif tType == 'PBX':
                        setTmpPbxParams(cfgInfo)

                elif str(targetInfo.targetCode).upper() in [ 'PNF'] :
                    tType = str(targetInfo.targetType).upper()
                    if tType == 'UTM' :
                        setTmpPnfUtmParams(targetInfo.targetSeq, dbm, cfgInfo, targetInfo.targetMapping, targetInfo.targetWanIfNum)


#                 elif cfgInfo.has_key('vm_name'):
#                     vmName = cfgInfo['vm_name']
#                     if str(vmName).count('UTM') > 0:
#                         setTmpUtmParams(targetInfo.targetSeq, dbm, cfgInfo, targetInfo.targetMapping)
#                     elif str(vmName).count('WAF') > 0:
#                         setTmpWafParams(cfgInfo)
#                     elif str(vmName).count('WIMS') > 0:
#                         setTmpApcParams(cfgInfo)
#                     elif str(vmName).count('XMS') > 0:
#                         setTmpXmsParams(cfgInfo)
                        
        return rrl.rSc(None, monInfo, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, monInfo)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres

def convertTemplateCreate( params ):
    """
    - FUNC: Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
    - INPUT
        params(M): Orch-F로부터 받은 API Parameter
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    _param = params
    return rrl.rSc(None, _param, params)

def convertTargetSeqParam( dbm, svrSeq, params, monitorAt, ignoreNodata=False ):
    """
    - FUNC: Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
    - INPUT
        dbm(M): DB Connection 객체
        svrSeq(M): 서버 Sequence
        params(M): Orch-F로부터 받은 API Parameter
        monitorAt(M): 모니터링 시작 시점(OneTouch, Provisioning)
        ignoreNodata(O): True 일 경우 Target 정보가 한 개 또는 없는 것까지 처리하고, False 일 경우 한 개인 것만 처리
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Convert TargetSeq'
    try:
        rmList = []
        _monitorAt = monitorAt
        if monitorAt == 'All' :
            _monitorAt = None
        
        for targetInfo in params['target_info']:
            if not targetInfo.has_key('target_seq'):
                targetVer = (lambda x: x['target_version'] if x.has_key('target_version') else None)(targetInfo)
                vdudSeq = (lambda x: x['vdud_seq'] if x.has_key('vdud_seq') else None)(targetInfo)
                sql = db_sql.GET_TARGET_BY_TARGETINFO( svrSeq, targetInfo['target_code'], targetInfo['target_type'], 
                                targetInfo['vendor_code'], targetInfo['target_model'], targetVer, vdudSeq, _monitorAt )

                # logger.Info ( 'GET_TARGET_BY_TARGETINFO : ' + sql )
                
                ret = dbm.select( sql )
                if ret == None :
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Getting TargetSeq Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                if not ignoreNodata :
                    if len(ret) != 1:
                        rres = rrl.rFa(None, rrl.RS_INVALID_DATA, 'Target Not Unique', ret, targetInfo)
                        logger.error( rres.lF(FNAME) )
                        return rres
                else:
                    if len(ret) == 0 :
                        rmList.append(targetInfo)
                        continue
                    elif len(ret) > 1:
                        rres = rrl.rFa(None, rrl.RS_DUPLICATE_DATA, 'Getting TargetSeq Error', ret, targetInfo)
                        logger.error( rres.lF(FNAME) )
                        return rres
                
                targetInfo['target_seq'] = ret[0]['montargetcatseq']
            
            ###### 임시 설정 
            if targetInfo.has_key('cfg') :
                
                ret = dbm.select( db_sql.GET_TARGET_INFO( targetInfo['target_seq'] ) )
                if ret == None or len(ret) < 1:
                    if ret == None: rs = rrl.RS_FAIL_DB
                    else: rs = rrl.RS_NO_DATA
                    rres = rrl.rFa(None, rs, 'Getting TargetInfo Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                if not targetInfo.has_key('target_code') or targetInfo['target_code'] == None :
                    targetInfo['target_code'] = ret[0]['targetcode']
                if not targetInfo.has_key('target_type') or targetInfo['target_type'] == None :
                    targetInfo['target_type'] = ret[0]['targettype']
                
                cfgInfo = targetInfo['cfg']
                if targetInfo.has_key('target_code') and str(targetInfo['target_code']).upper() == 'OS' :
                    setTmpOsParams(cfgInfo)
                    
                elif str(targetInfo['target_code']).upper() in [ 'VNF', 'PNF' ] :
                    tType = str(targetInfo['target_type']).upper()
                    if tType == 'UTM' :
                        if not targetInfo.has_key('mapping') :
                            targetInfo['mapping'] = {}
                        setTmpUtmParams(targetInfo['target_seq'], dbm, cfgInfo, targetInfo['mapping'], targetInfo['wan_if_num'])
                    elif tType == 'WAF' :
                        setTmpWafParams(cfgInfo)
                    elif tType == 'WIFI-AC' :
                        setTmpApcParams(cfgInfo)
                    elif tType == 'XMS' :
                        setTmpXmsParams(cfgInfo)
#                 elif cfgInfo.has_key('vm_name'):
#                     vmName = cfgInfo['vm_name']
#                     if str(vmName).count('UTM') > 0:
#                         if not targetInfo.has_key('mapping') :
#                             targetInfo['mapping'] = {}
#                         setTmpUtmParams(targetInfo['target_seq'], dbm, cfgInfo, targetInfo['mapping'])
#                     elif str(vmName).count('WAF') > 0:
#                         setTmpWafParams(cfgInfo)
#                     elif str(vmName).count('WIMS') > 0:
#                         setTmpApcParams(cfgInfo)
#                     elif str(vmName).count('XMS') > 0:
#                         setTmpXmsParams(cfgInfo)
        for rmInfo in rmList:
            params['target_info'].remove(rmInfo)
        
        return rrl.rSc(None, params, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, params)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres


def convertTargetSeq( dbm, svrSeq, _monInfo, monitorAt, ignoreNodata=False ):
    """
    - FUNC: Orch-F으로부터 받은 API Parameter를 Orch-M 형식으로 변환
    - INPUT
        dbm(M): DB Connection 객체
        svrSeq(M): 서버 Sequence
        _monInfo(M): Orch-F로부터 받은 API Parameter
        monitorAt(M): 모니터링 시작 시점(OneTouch, Provisioning)
        ignoreNodata(O): True 일 경우 Target 정보가 한 개 또는 없는 것까지 처리하고, False 일 경우 한 개인 것만 처리
    - OUTPUT
        result: rrl_handler._ReqResult
    """
    FNAME = 'Convert TargetSeq'
    
    monInfo = mon_msg.MonInfo
    if _monInfo != None : monInfo = _monInfo
    
    try:
        rmList = []
        _monitorAt = monitorAt
        if monitorAt == 'All' :
            _monitorAt = None
        
        targetInfo = mon_msg.TargetInfo
        for targetInfo in monInfo.targetList:
            if targetInfo.targetSeq == None :
                targetVer = targetInfo.targetVer
                vdudSeq = targetInfo.targetVdudSeq
                sql = db_sql.GET_TARGET_BY_TARGETINFO( svrSeq, targetInfo.targetCode, targetInfo.targetType, 
                                targetInfo.targetVendor, targetInfo.targetModel, targetVer, vdudSeq, _monitorAt )

                logger.info (' GET_TARGET_BY_TARGETINFO : %s' % sql)

                ret = dbm.select( sql )
                if ret == None :
                    rres = rrl.rFa(None, rrl.RS_FAIL_DB, 'Getting TargetSeq Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                if not ignoreNodata :
                    if len(ret) != 1:
                        rres = rrl.rFa(None, rrl.RS_INVALID_DATA, 'Target Not Unique', ret, targetInfo)
                        logger.error( rres.lF(FNAME) )
                        return rres
                else:
                    if len(ret) == 0 :
                        rmList.append(targetInfo)
                        continue
                    elif len(ret) > 1:
                        rres = rrl.rFa(None, rrl.RS_DUPLICATE_DATA, 'Getting TargetSeq Error', ret, targetInfo)
                        logger.error( rres.lF(FNAME) )
                        return rres
                
                targetInfo.targetSeq = ret[0]['montargetcatseq']


            ###### 임시 설정 
            if targetInfo.targetCfg != None :
                
                ret = dbm.select( db_sql.GET_TARGET_INFO( targetInfo.targetSeq ) )
                if ret == None or len(ret) < 1:
                    if ret == None: rs = rrl.RS_FAIL_DB
                    else: rs = rrl.RS_NO_DATA
                    rres = rrl.rFa(None, rs, 'Getting TargetInfo Error', ret, targetInfo)
                    logger.error( rres.lF(FNAME) )
                    return rres
                
                if targetInfo.targetCode == None :
                    targetInfo.targetCode = ret[0]['targetcode']

                if targetInfo.targetType == None : 
                    targetInfo.targetType = ret[0]['targettype']
                
                cfgInfo = targetInfo.targetCfg
                if str(targetInfo.targetCode).upper() == 'OS' :
                    setTmpOsParams(cfgInfo)

                elif str(targetInfo.targetCode).upper() in [ 'VNF', 'PNF' ] :
                    tType = str(targetInfo.targetType).upper()
                    if tType == 'UTM' :
                        setTmpUtmParams(targetInfo.targetSeq, dbm, cfgInfo, targetInfo.targetMapping)
                    elif tType == 'WAF' :
                        setTmpWafParams(cfgInfo)
                    elif tType == 'WIFI-AC' :
                        setTmpApcParams(cfgInfo)
                    elif tType == 'XMS' :
                        setTmpXmsParams(cfgInfo)
#                 elif cfgInfo.has_key('vm_name'):
#                     vmName = cfgInfo['vm_name']
#                     if str(vmName).count('UTM') > 0:
#                         setTmpUtmParams(targetInfo.targetSeq, dbm, cfgInfo, targetInfo.targetMapping)
#                     elif str(vmName).count('WAF') > 0:
#                         setTmpWafParams(cfgInfo)
#                     elif str(vmName).count('WIMS') > 0:
#                         setTmpApcParams(cfgInfo)
#                     elif str(vmName).count('XMS') > 0:
#                         setTmpXmsParams(cfgInfo)
                        
        for rmInfo in rmList:
            monInfo.targetList.remove(rmInfo)
        
        return rrl.rSc(None, monInfo, None)
    except Exception, e:
        rres = rrl.rFa(None, rrl.RS_EXCP, e, None, monInfo)
        logger.error(rres.lF(FNAME))
        logger.fatal(e)
        return rres


