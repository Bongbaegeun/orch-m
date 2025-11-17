#!/usr/bin/python
#-*- coding: utf-8 -*-
"""로드쇼_2018 용 VPN Count, Wan 상태 값을 DB 저장하는 APP
    2018.06.18 - lsh
"""
import yaml
import time
from util import statistics
# import util.statistics_model as model
from util import gsf 
from handler import rrl_handler as rrl
import psycopg2.extras

TITLE = 'RoadShow_2018'
TITLE_FAULT = 'RoadShow'
TITLE_API = 'RoadShow'
from util.ko_logger import ko_logger
logger = ko_logger(tag=TITLE, logdir="./log/", loglevel="debug", logConsole=False).get_instance()

# AES
from util.aes_cipher import AESCipher
from util import db_mng
import psycopg2

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
    cfgf['db_passwd'] = cipher.decrypt(cfgf['db_passwd'] )
    cfgf['zb_passwd'] = cipher.decrypt(cfgf['zb_passwd'] )
    cfgf['zb_db_passwd'] = cipher.decrypt(cfgf['zb_db_passwd'] )

    return cfgf

    
class updateDB ():
    """모니터링 데이터 복사를 위한 스레드
    """
    zb = None
    zbCur = None
    
    orch = None
    orchCur = None
    
    logger = None

    bonsa_vpnserver = False
    
    def __init__(self, logger, cfg):
        self.logger = logger

        self.zb = db_mng.makeZbDbConn(cfg)  # 자빅스 DB 연결 객체
        self.zbCur = self.zb.cursor(cursor_factory=psycopg2.extras.DictCursor)       # 자빅스 DB 커서

        self.orch = db_mng.makeDbConn(cfg)  # Orch-M DB 연결 객체
        self.orchCur = self.orch.cursor(cursor_factory=psycopg2.extras.DictCursor)   # Orch-M DB 커서


    def check_conn_type(self):
        """본사 상태가 I__DISCONNECTED 인가 ?
            if 본사 One-Box 중(상태: I__DISCONNECTED가 아닌)에 VPN모니터링값이 != Null 존재:
              if 지사.VPN모니터링값!=Null:
                 지사의 conn_type=VPN
              else:
                 지사의 conn_type=INTERNET
            else:
              지사의 conn_type=INTERNET

            *default: INTERNET"
        """
        sql = """
            SELECT customerseq, officeseq, status, monitorvalue vpncount, officename
            FROM 
            (
                SELECT svr.serverseq,  svr.officeseq, svr.status, svr.customerseq, office.officename
                FROM tb_customer_office office, tb_server svr, tb_customer cust
                WHERE office.customerseq = cust.customerseq
                AND svr.officeseq = office.officeseq
                AND cust.customername = '로드쇼2018'
            ) info
            LEFT OUTER JOIN tb_moniteminstance ii ON ii.serverseq = info.serverseq AND ii.monitemcatseq = 215
            LEFT OUTER JOIN tb_realtimeperf perf ON ii.moniteminstanceseq = perf.moniteminstanceseq AND monitoredyn = 'y'
            """

        self.orchCur.execute(sql)
        items = self.orchCur.fetchall()
        
        # bDISCONN
        bDISCONN = False
        self.bonsa_vpnserver = False
        for item in items:
            if item['officename'] == '본사' and item['vpncount'] <> None:
                self.bonsa_vpnserver= True  # 본사 VPN 값 저장, Fake지사 체크용

            if item['status'] == 'I__DISCONNECTED' and item['officename'] == '본사' :
                customerseq = item['customerseq']
                bDISCONN = True
                break
                
        # 본사 I__DISCONNECTED 확인.
        if bDISCONN :
            sql = """
                UPDATE tb_customer_office 
                SET conn_type = 'INTERNET'
                WHERE customerseq = %s """ % customerseq
            self.orchCur.execute(sql)

        else :
            for item in items:
                if item['vpncount'] <> None :
                    msg='VPN'
                else :
                    if self.bonsa_vpnserver :
                        msg='VPN'
                    else :
                        msg = 'INTERNET'

                sql = """
                    UPDATE tb_customer_office 
                    SET conn_type = '%s'
                    WHERE officeseq = %s """ % (msg, item['officeseq'])

                self.orchCur.execute(sql)

        return True


    def check_conn_status(self):
        """
            If 지사의 conn_type == VPN:
              if 지사의 VPN모니터링값 > 0:
                지사의 conn_status = N__OK
              else:
                지사의 conn_status = E_ERROR
            else:
              if 지사의 One-Box 인터넷 연결 상태 == OK:
                지사의 conn_status = N__OK
              else:
                지사의 conn_status = E__ERROR"
        """
        sql = """
               SELECT officeseq, conn_type, count(vpncount) vpn, count(internet) internet, count( fakeserver ) real_server
                FROM
                (
                    SELECT  officeseq, conn_type
                    , CASE WHEN monitemcatseq = 215 THEN monitorvalue END vpncount
                    , CASE WHEN monitemcatseq = 51 THEN monitorvalue END internet
                    , CASE WHEN monitemcatseq = 45 THEN monitorvalue END fakeserver
                    FROM  
                    (
                        -- 지사만 추출
                        SELECT svr.serverseq,  svr.officeseq, conn_type
                        FROM tb_customer_office office, tb_server svr, tb_customer cust
                        WHERE office.customerseq = cust.customerseq
                        AND svr.officeseq = office.officeseq
                        AND cust.customername = '로드쇼2018'
                        -- AND svr.status = 'N__IN_SERVICE'
                        -- AND officename <> '본사'
                    ) info
                    LEFT OUTER JOIN tb_moniteminstance ii ON ii.serverseq = info.serverseq 
					AND ( ii.monitemcatseq in ( 45, 215 ) OR ( ii.monitemcatseq = 51 and ii.monitorobject in ('eth0')))
                    LEFT OUTER JOIN tb_realtimeperf perf ON ii.moniteminstanceseq = perf.moniteminstanceseq 
					AND monitoredyn = 'y'
                ) A
                GROUP BY officeseq, conn_type
            """
        self.orchCur.execute(sql)
        items=self.orchCur.fetchall()

        for item in items:
            if item['real_server'] :
                if item['conn_type'] == 'VPN':
                    if item['vpn'] :
                        msg = "N__OK"
                    else :
                        msg = "E__ERROR"
                else :
                    if item['internet'] :
                        msg = "N__OK"
                    else :
                        msg = "E__ERROR"

                sql="""
                UPDATE tb_customer_office 
                SET conn_status = '%s'
                WHERE officeseq = %s """ % (msg, item['officeseq'])

                self.orchCur.execute(sql)


    def check_wan_status (self):
        """
        if tb_customer_office_wan.onebox_id == Null:
          status = N_NOTUSED
        else:
          if 해당 One-Box의 인터넷 연결 상태 == OK:
            status = N__OK
          else:
            status = E__ERROR"

        """
        sql = """
                SELECT cow.office_wanseq, cow.onebox_id, svr.serverseq, MAX(perf.monitorvalue) internet
                FROM tb_customer_office_wan cow
                LEFT OUTER JOIN tb_server svr ON svr.onebox_id = cow.onebox_id
                LEFT OUTER JOIN tb_moniteminstance ii ON ii.serverseq = svr.serverseq AND ii.monitemcatseq = 51 AND monitorobject in ('eth0')
                LEFT OUTER JOIN tb_realtimeperf perf ON perf.moniteminstanceseq = ii.moniteminstanceseq AND perf.monitoredyn = 'y'
                GROUP BY cow.office_wanseq, cow.onebox_id, svr.serverseq
                """
        self.orchCur.execute(sql)
        items=self.orchCur.fetchall()

        for item in items:
            if not item['onebox_id'] :
                msg = "N__NOTUSED"
            elif  item['internet'] == '1' :
                msg = "N__OK"
            else :
                msg = "E__ERROR"

            sql="""
            UPDATE tb_customer_office_wan
            SET wan_status = '%s'
            WHERE office_wanseq = %s """ % ( msg, item['office_wanseq'] )
            self.orchCur.execute(sql)


if __name__ == '__main__':
    cfgName = './cfg/orchm.cfg'
    cfg = loadConfig(cfgName)
    
    # 모니터링 데이터 복사
    s = updateDB(logger, cfg)

    while True :
        s.check_conn_type()
        s.check_conn_status()
        s.check_wan_status()
        time.sleep(10)
