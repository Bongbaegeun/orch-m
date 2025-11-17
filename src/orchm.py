# -*- coding: utf-8 -*-
'''
Created on 2015. 9. 11.

@author: ohhara
'''

import sys, yaml, threading
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
from time import sleep

from util import gsf
from handler import rrl_handler as rrl
import fault_mng, perf_mng, mon_mng
import api.zbm_api as zb

from api import zabbix_api

# import ssl
# AES
from util.aes_cipher import AESCipher

TITLE = 'orchm'
TITLE_FAULT = 'faultmsg'
TITLE_API = 'apimsg'
from util.ko_logger import ko_logger

logger = ko_logger(tag=TITLE, logdir="./log/", loglevel="debug", logConsole=False).get_instance()

#faultLogger = ko_logger(tag=TITLE_FAULT, logdir="./log/", loglevel="debug", logConsole=False, onlyLog=True).get_instance()
#apiLogger = ko_logger(tag=TITLE_API, logdir="./log/", loglevel="debug", logConsole=False, onlyLog=True).get_instance()



class httpSvrThread(threading.Thread):
    """
    - FUNC: Rest API 생성 클래스
    - INPUT
        applictions(M): URL, 처리 Handler, 인자 정의 객체
        port(M): API 용 포트
        proc(M): API 처리 프로세스 개수
    """
    def __init__(self, applictions, port, proc, certfile, keyfile):
        threading.Thread.__init__(self)
        self.svr = HTTPServer(applictions, ssl_options={
#            "ssl_version" : ssl.OP_NO_SSLv3,
#            "ciphers" : "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!3DES:!MD5:!PSK",
            "certfile" : certfile,
            "keyfile" : keyfile
        })
        self.svr.bind(port)
        self.svr.start(proc)

    def run(self):
        logger.info( rrl.lI2('run Http Server') )
        IOLoop.current().start()


# configuration
def loadConfig(cfgName):
    """
    - FUNC: Orch-M의 설정 파일 로딩
    - INPUT
        cfgName(M): 설정 파일이름
    - OUTPUT : 설정 파일 Dict
    """
    logger.info( rrl.lI2('load Config : fName=%s'%cfgName) )

    with open(cfgName, "r") as f:
        cfgf = yaml.load(f)

    gVar = gsf.VarShared( cfgf['gVar'] )
    cfgf['gVar'] = gVar

    # 2017. 11. 14 - lsh
    # AES Decrypt
    cipher=AESCipher(cfgf['orchm_salt'] , cfgf['orchm_code'] )
    cfgf['mysql_passwd'] = cipher.decrypt(cfgf['mysql_passwd'] )
    cfgf['db_passwd'] = cipher.decrypt(cfgf['db_passwd'] )
    cfgf['zb_passwd'] = cipher.decrypt(cfgf['zb_passwd'] )
    cfgf['zb_db_passwd'] = cipher.decrypt(cfgf['zb_db_passwd'] )

    return cfgf

def makeApp( _cfg ):
    """
    - FUNC: URL, Handler, 인자 설정 객체 생성
    - INPUT
        _cfg(M): 설정 정보 객체
    - OUTPUT : Application 객체
    """
    app = Application(  fault_mng.url( _cfg )           # FaultManager의 URL 및 API Handler, 인자 관리
                      + perf_mng.url ( _cfg )           # PerfManager URL 및 API Handler, 인자 관리
                      + mon_mng.url  ( _cfg )           # MonManager의 URL 및 API Handler, 인자 관리
                      # + rs2016.url  ( _cfg )            # roadshow
                      )

    return app

# Get info for operation
def getInitInfo(cfg):
    """
    - FUNC: 초기 설정 정보를 Orch-F로부터 수신( 예정 )
    - INPUT
        cfg(M): 설정 정보 객체
    """
    logger.info( rrl.lI2('get Init Info: %s'%cfg) )

# Set up config and Reload components
def setup(info, cfg):
    """
    - FUNC: Orch-F로부터 받은 설정 정보 setting( 예정 )
    - INPUT
        info(M): 초기 설정 정보
    """
    logger.info( rrl.lI2('setup: %s'%info) )
    loglevel = str(cfg['log_level']).lower()
    import logging
    if loglevel == "debug":
        logger.setLevel(logging.DEBUG)
    elif loglevel == "info":
        logger.setLevel(logging.INFO)
    elif loglevel == "warning":
        logger.setLevel(logging.WARN)
    elif loglevel == "error":
        logger.setLevel(logging.ERROR)
    elif loglevel == "critical":
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)


def startScheduler( cfg ):
    """
    - FUNC: 스케줄러 시작
    - INPUT
        cfg(M): 설정 정보 객체
    """
    logger.info( rrl.lI2( 'start Scheduler' ) )

    logger.info( rrl.lI2( 'start ZB Manager' ) )
    # 주기적으로 zbms 연결 상태 확인 및 재연결하는 클래스
    connThread = zb.ZBMConnThread( cfg, logger )
    connThread.start()

    logger.info( rrl.lI2( 'start ZB PerfHist Collector' ) )
    # 주기적으로 Zabbix로부터 최신 데이터를 조회하고 DB저장하는 thread 생성
    histCollector = zb.PerfHistCollector( cfg, logger )
    histCollector.start()

    logger.info( rrl.lI3( 'start Alarm Ack Manager' ) )
    # 장애 인지 처리 후 인지 유지 시간이 넘어도 장애 해결이 되지 않으면 인지 해제시키는 스케줄러
    ackMng = fault_mng.alarmAckManager( cfg )
    ackMng.start()

    logger.info( rrl.lI3( 'start CurrAlarm Manager' ) )
    # tb_curalarm 테이블에서 하루 지난 항목을 제거
    alrMng = fault_mng.curAlarmRemover(cfg)
    alrMng.start()

    logger.info( rrl.lI3( 'start ZBS Status Checker' ) )
    # Zabbix 연결 상태 확인
    zbChk = mon_mng.zbStatusChecker(cfg)
    zbChk.start()

    logger.info( rrl.lI3( 'start ZB Item State Checker' ) )
    # Zabbix Item State Checker
    zbStateChk = zb.zbItemStateChecker(cfg, logger)
    zbStateChk.start()

    logger.info( rrl.lI3( 'start SNMP Host Active Checker' ) )
    # Zabbix Item State Checker
    SNMPHostActiveChk = zabbix_api.snmp_host_start(cfg, logger)
    SNMPHostActiveChk.start()


def startAPI(app, cfg, info):
    """
    - FUNC: API 쓰레드 시작
    - INPUT
        app(M): Application 객체
        cfg(M): 설정 정보 객체
        info(M): 초기 설정 정보
    """
    logger.info( rrl.lI2('start API : port=%s, procNum=%s, url=%s'%(cfg['port'], cfg['procNum'], app)) )
    svr = httpSvrThread(app, cfg['port'], cfg['procNum'], cfg['certfile'], cfg['keyfile'])
    svr.start()


def onStart(cfg):
    """
    - FUNC: 프로그램 시작 시 수행할 업무 트리거
    - INPUT
        cfg(M): 설정 정보 객체
    """
    logger.info( rrl.lI2('start Init Operation') )
    # 2017.07.11 김승주전임 주석처리 요청(zabbix와 장애 데이터 동기화 하는 기능인데 데이터량 많아 장애 발생가능성 있으며 쿼리 수정 필요)
    # fault_mng.onStart(cfg)          # FaultManager 시작 시 실행해야할 기능 구현
    mon_mng.onStart(cfg)            # MonManager 시작 시 실행해야할 기능 구현
    perf_mng.onStart(cfg)           # PerfManager 시작 시 실행해야할 기능 구현


def main(cfgName):
    logger.info( rrl.lI1("Main Start") )

    # Orch-M의 설정 파일 로딩
    cfg = loadConfig(cfgName)

    # 초기 설정 정보를 Orch-F로부터 수신( 예정 ) - X
    info = getInitInfo( cfg )

    # Orch-F로부터 받은 설정 정보 setting( 예정 ) -> log level setup
    setup( info, cfg )

    # URL, Handler, 인자 설정 객체 생성
    app = makeApp( cfg )

    # 스케줄러 시작
    startScheduler( cfg )

    # 프로그램 시작 시 수행할 업무 트리거
    onStart(cfg)

    sleep(1)

    # API 쓰레드 시작
    startAPI( app, cfg, info )

    logger.info( rrl.lI1("Main END") )

if __name__ == '__main__':

    cfgName = './cfg/orchm.cfg'
    if len(sys.argv) >= 2:
        cfgName = sys.argv[1]

    main(cfgName)






