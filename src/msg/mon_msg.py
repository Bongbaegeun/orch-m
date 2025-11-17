# -*- coding: utf-8 -*-
'''
Created on 2016. 3. 22.

@author: ohhara

모니터링을 수행하기 위해서 Orch-F로부터 전달 받은 파라미터를 Orch-M에서 사용할 수 있도록 변환 및 객체로 전환 
'''


class BaseMsg(object):
    """메시지 관련 기본 객체
    """
    
    def __init__(self):
        pass

    def __str__(self):
        dd = dict(self.__dict__)
        d = {}
        for k in dd.keys():
            if type(dd[k]) == list or type(dd[k]) == tuple :
                d[k] = []
                for t in dd[k]:
                    if isinstance(t, BaseMsg) :
                        d[k].append(t.__dict__)
                    else :
                        d[k].append(t)
            elif type(dd[k]) == dict :
                _d = {}
                for _k in dd[k].keys():
                    if isinstance( dd[k][_k], BaseMsg ) :
                        _d[_k] = dd[k][_k].__dict__
                    else:
                        _d[_k] = dd[k][_k]
                d[k] = _d
            elif isinstance(dd[k], BaseMsg) :
                d[k] = dd[k].__dict__
            else:
                d[k] = dd[k]
        
        return str(d)

# 해당 변수가 존재할 경우 할당, 없다면 None 할당
def setArg( arg, argName, noneType=None ):
    return (lambda x: x[argName] if x.has_key(argName) else noneType)(arg)


class SvrInfo(BaseMsg):
    """원박스 서버의 정보
    """
    
    def __init__(self, svrParam):
        self.svrSeq = svrParam['seq']
        self.svrObid = setArg(svrParam, 'onebox_id')
        self.svrUuid = setArg(svrParam, 'uuid')
        self.svrIP = setArg(svrParam, 'ip')
        self.svrName = setArg(svrParam, 'name')
        self.svrDesc = setArg(svrParam, 'desc', '')
        self.svrZbaPort = setArg(svrParam, 'mon_port')
        self.onebox_type = setArg(svrParam, 'onebox_type')

class SvrModInfo(BaseMsg):
    
    def __init__(self, svrParam):
        self.svrSeq = svrParam['seq']
        self.svrNewIP = svrParam['new_ip']
        self.svrModDesc = setArg(svrParam, 'mod_desc', '')


# 2016. 8.28 - lsh
# sulbyun

class lan_info(BaseMsg):
    def __init__(self, svrParam):
        self.svrseq = setArg(svrParam, 'svrseq')
        self.before_eth = setArg(svrParam, 'before_eth')
        self.after_eth = setArg(svrParam, 'after_eth')
        self.before_lan = setArg(svrParam, 'before_lan')
        self.after_lan = setArg(svrParam, 'after_lan')



class TargetInfo(BaseMsg):
    """모니터링 타겟(템플릿) 정보
    """
    
    def __init__(self, targetParam):
        self.targetSeq = setArg(targetParam, 'target_seq')
        self.targetCode = setArg(targetParam, 'target_code')
        self.targetType = setArg(targetParam, 'target_type')
        self.targetVendor = setArg(targetParam, 'vendor_code')
        self.targetModel = setArg(targetParam, 'target_model')
        self.targetVer = setArg(targetParam, 'target_version')
        self.targetFor = setArg(targetParam, 'target_for')
        
        self.targetVdudSeq = setArg(targetParam, 'vdudseq')
        self.targetPluginPath = setArg(targetParam, 'plugin_path')
        self.targetCfg = setArg(targetParam, 'cfg')
        self.targetMapping = setArg(targetParam, 'mapping', {})

        # 2017-02-15 회선 이중화를 위해서 mapping 필드중 wan, office1, office2, server 정보는 무조건 list 형식을 가지도록 수정
        for key in self.targetMapping:  # 매핑 정보는 회선 이중화인 경우에만 존재한다.
            if type(self.targetMapping[key]) is str:  # wan, office1, server 필드의 값이 문자열이면 리스트 형식으로 변환
                self.targetMapping[key] = [self.targetMapping[key]]

        self.targetWanIfNum = setArg(targetParam, 'wan_if_num', 1)  # 2017.02.16 wan 회선수 추가

class MonInfo(BaseMsg):
    """모니터링 대상 정보. 서버, 타겟(템플릿) 정보를 포함
    """
    
    def __init__(self, monParam):
        self.svrInfo = SvrInfo( monParam['svr_info'] )
        self.service_number = setArg(monParam, 'ob_service_number')
        self.targetList = []
        for target in monParam['target_info'] :
            self.targetList.append( TargetInfo(target) )

class ResumeInfo(BaseMsg):
    
    def __init__(self, resumeParam):
        self.svrInfo = SvrInfo( resumeParam['svr_info'] )
        self.resumeType = setArg(resumeParam, 'type')
        self.targetList = []
        for target in resumeParam['target_info'] :
            self.targetList.append( TargetInfo(target) )