#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
import json
from tornado.web import RequestHandler

import api.zbm_api as zb
from util import db_mng
from handler import rrl_handler as rrl
from util.db_mng import dbManager


TITLE = 'orchm'
TITLE_API = 'apimsg'

import logging
logger = logging.getLogger(TITLE)
apiLogger = logging.getLogger(TITLE_API)


TEST = 'TEST'
PERF_REQ = 'PERF_AVG_INQ'
PERF_MAX_REQ = 'PERF_MAX_INQ'
PERF_CURR_REQ = 'RECENT_PERF_INQ'
NETWORK_TOP = 'NETWORK_TOP'
ONEBOX_NETWORK_24H = 'ONEBOX_NETWORK_24H'

# 21. 4. 6 - lsh
# Zabbix RTT 값 조회
RTT_TOP = 'RTT_TOP'

# 상세 데이터 조회
RTT_DATA = 'RTT_DATA'


class PerfHandler(RequestHandler):
    """
    - FUNC: 성능 요청 API 생성 및 처리하는 클래스
    - INPUT
        opCode(M): 요청 서비스 이름
        cfg(M): Orch-M 설정 정보
    """
    
    def initialize(self, opCode, cfg):
        self.opCode = opCode
        self.cfg = cfg
        connNum = (lambda x: x['db_conn_num'] if x.has_key('db_conn_num') else 1 )(cfg)
        self.dbm = dbManager( 'orchm', cfg['db_name'], cfg['db_user'], cfg['db_passwd'],
                    cfg['db_addr'], int(cfg['db_port']), connCnt=connNum, _logger=logger )
        zbConnNum = (lambda x: x['zb_db_conn_num'] if x.has_key('zb_db_conn_num') else 1 )(cfg)
        self.zbDbm = dbManager( 'zbs', cfg['zb_db_name'], cfg['zb_db_user'], cfg['zb_db_passwd'],
                    cfg['zb_db_addr'], int(cfg['zb_db_port']), connCnt=zbConnNum, _logger=logger )
    
    def post(self):
        reqdata = self.request.body
        self.src = self.request.remote_ip
        logger.info( rrl.lRReq(self.src, 'PerfHandler', self.opCode, reqdata) )
        apiLogger.info( rrl.lRReq(self.src, 'PerfHandler', self.opCode, reqdata) )
        
        res = None
        if self.opCode == PERF_REQ :        res = self.perfReq()
        if self.opCode == PERF_MAX_REQ :    res = self.perfReq()
        if self.opCode == NETWORK_TOP :     res = self.perfReq()
        if self.opCode == RTT_TOP :         res = self.perfReq()
        if self.opCode == RTT_DATA :         res = self.perfReq()
        if self.opCode == ONEBOX_NETWORK_24H         :    res = self.perfReq()
        elif self.opCode == PERF_CURR_REQ : res = self.perfCurrReq()
        elif self.opCode == TEST :          res = self.test()
        
        self.write(res)
        self.flush()
        # apiLogger.info( rrl.lSRes(self.src, 'PerfHandler', self.opCode, res) )
    
    def perfReq(self):
        """
        - FUNC: 성능 정보(AVG/MAX) 요청 API 처리
        - OUTPUT : 성능 데이터(AVG/MAX)
            result: WEB 용 결과
        """
        try:
            reqdata = json.loads(self.request.body)
            
            logger.info ( '========== perfReq reqdata : %s' % reqdata)
            
            if self.opCode == PERF_REQ :
                isSucc, ret = zb.reqPerfData( reqdata, self.cfg['zb_perf_stat_period'], self.dbm, self.zbDbm, logger )
            elif self.opCode == PERF_MAX_REQ :
                isSucc, ret = zb.reqPerfMaxData( reqdata, self.cfg['zb_perf_stat_period'], self.dbm, self.zbDbm, logger )
            elif self.opCode == NETWORK_TOP :
                isSucc, ret = zb.reqNetwork_top( reqdata, self.dbm, self.zbDbm, logger )

            elif self.opCode == RTT_TOP :
                isSucc, ret = zb.reqRtt_top( reqdata, self.dbm, self.zbDbm, logger )

            elif self.opCode == RTT_DATA :
                isSucc, ret = zb.reqRtt_data( reqdata, self.dbm, self.zbDbm, logger )

            elif self.opCode == ONEBOX_NETWORK_24H  :
                isSucc, ret = zb.reqOneboxNetwork_24h( reqdata, self.dbm, self.zbDbm, logger )
            else:
                rres = rrl.rFa(None, rrl.RS_UNKNOWN_REQ, 'OpCode:%s, URL=%s'%(self.opCode, self.request.uri), None, reqdata)
                logger.error( rres.lF(self.opCode) )
                return rres.toWebRes()
            
            if isSucc :
                rres = rrl.rSc(None, ret, reqdata)
                res = rres.toWebRes()
            else:
                rres = rrl.rFa(None, rrl.RS_FAIL_ZB_OP, ret, None, reqdata)
                res = rres.toWebRes()
                
        except (ValueError, TypeError):
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            res = rres.toWebRes()
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            res = rres.toWebRes()
        
        return res

    def perfCurrReq(self):
        """
        - FUNC: 실시간 정보 요청 API 처리
        - OUTPUT : 실시간 성능 데이터
            result: WEB 용 결과
        """
        try:
            period = self.cfg['zb_perfhist_period']
            expire = self.cfg['zb_perfhist_expire']
            dbConn = db_mng.makeDbConn( self.cfg )
            zbDbConn = db_mng.makeZbDbConn( self.cfg )
            
            isSucc, ret = zb.reqCurrData( period, expire, zbDbConn, dbConn, logger )
            if isSucc :
                rres = rrl.rSc(None, ret, None)
                res = rres.toWebRes()
            else:
                rres = rrl.rFa(None, rrl.RS_FAIL_ZB_OP, ret, None, None)
                res = rres.toWebRes()
            dbConn.close()
            zbDbConn.close()
        except (ValueError, TypeError):
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            res = rres.toWebRes()
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            res = rres.toWebRes()
        
        return res

    def test(self):
        try:
            json.loads(self.request.body)
#             res = zb.reqPerfHistAvgPerPeriod( reqdata, self.dbm, self.zbDbm, logger )
#             print res
        except (ValueError, TypeError):
            rres = rrl.rFa(None, rrl.RS_INVALID_PARAM, None, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            res = rres.toWebRes()
        except Exception, e:
            rres = rrl.rFa(None, rrl.RS_EXCP, e, None, self.request.body)
            logger.error( rres.lF(self.opCode) )
            logger.fatal(e)
            res = rres.toWebRes()
        
        return res
        

def url( _cfg ):
    """
    - FUNC: PerfManager URL 및 API Handler, 인자 관리
    - INPUT
        _cfg(M): Orch-M 설정 정보
    - OUTPUT : API에 대한 URL, Handler, 인자 리스트
    """
    url = [ ('/perf/test', PerfHandler, dict(opCode=TEST, cfg=_cfg)),
            ('/perf', PerfHandler, dict(opCode=PERF_REQ, cfg=_cfg)),
            ('/perf/network_top', PerfHandler, dict(opCode=NETWORK_TOP, cfg=_cfg)),
            ('/perf/rtt_top', PerfHandler, dict(opCode=RTT_TOP, cfg=_cfg)),
            ('/perf/rtt_data', PerfHandler, dict(opCode=RTT_DATA, cfg=_cfg)),
            ('/perf/onebox_network_24h', PerfHandler, dict(opCode=ONEBOX_NETWORK_24H, cfg=_cfg)),
            ('/perf/max', PerfHandler, dict(opCode=PERF_MAX_REQ, cfg=_cfg)),
            ('/perf/curr', PerfHandler, dict(opCode=PERF_CURR_REQ, cfg=_cfg)) ]
    return url


def onStart(cfg):
    """
    - FUNC: PerfManager 시작 시 실행해야할 기능 구현
    - INPUT
        cfg(M): Orch-M 설정 정보
    """
    return


