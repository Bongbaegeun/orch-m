# -*- coding: utf-8 -*-
import platform, os, time
import redis
import psycopg2
import logging
import logging.handlers

ZABBIX_DB_IP = '127.0.0.1'
LOG_PATH = "/var/log/zabbix"

# 실행때 마다 zabbix_server.conf 파일을 읽어야 하나?
# Zabbix_server.conf 에서 password 가져오기
# ZABBIX_CONFIG_PATH = "/etc/zabbix/zabbix_server.conf"
# with open(ZABBIX_CONFIG_PATH) as f:
#     lines = f.readlines()
# for line in lines:
#     if 'DBPassword=' in line:
#         if line[0] == '#':
#             continue
#         DBPassword = line.split('=')[1].strip()
#         break
# f.close()

DBPassword='ohhberry3333'

logger = logging.getLogger("mylogger")

redis = redis.StrictRedis(host='127.0.0.1', db=2)
dbConn = psycopg2.connect( database='zabbix', user='zabbix', password=DBPassword,
                        host=ZABBIX_DB_IP, application_name='VPNStatus' )
dbConn.autocommit = True

if platform.system() == 'Windows' :
    LOG_PATH = "./"
else :
    LOG_PATH = "/var/log/zabbix/"

def init_logger ( ) :
    if not os.path.isdir(LOG_PATH) :
        os.mkdir(LOG_PATH)
        
    # 로거 인스턴스 생성
    # logger = logging.getLogger("mylogger")

    # 포매터를 만든다
    # formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    formatter = logging.Formatter('[%(asctime)s][%(filename)s:%(lineno)s][%(levelname)s] %(message)s')

    fileMaxByte = 1024 * 1024 * 10  # 10MB

    # 화면, 파일 각각 핸들러 생성
    filename = LOG_PATH + "VPNStatus.log"
    fileHandler = logging.handlers.RotatingFileHandler(filename, maxBytes=fileMaxByte, backupCount=10)

    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    # 핸들러를 생성된 logger 에 추가한다.
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    logger.setLevel(logging.DEBUG)

def get_vpntotalcount ( ) :

    Query = """
        SELECT h.host, count(*)
        FROM hosts h, items i
        WHERE h.hostid = i.hostid
        AND key_ like 'vpn.status.%'
        AND h.status = 0 
        AND h.flags = 0
        AND i.status = 0
        AND i.state = 0
        AND i.templateid is NULL
        GROUP BY host
    """

    cur = dbConn.cursor()
    cur.execute( Query )
    rows = cur.fetchall()
    
    for row in rows:
        logger.info ( "VPN Total Tunnel :%s, %s" % ( row[0], row[1] ))
        redis.set(row[0], row[1])
        redis.expire(row[0], 60*30)



    # VPN Status 
    # -- 1, Down
    # -- 2, UP
    # -- 2 값을 0 으로 맵핑후 SUM 으로 0 보다 큰값은 장애 
    Query = """
        SELECT a.host,
            sum(histvalue) as value
        FROM (
            SELECT h.host, i.name
                , CASE WHEN hist.value = 2 THEN 0
                    ELSE hist.value
                END histvalue
            FROM hosts h, items i, history_uint hist
            WHERE h.hostid = i.hostid
            AND h.hostid = i.hostid
            AND h.status = 0
            and i.key_ like 'vpn.status.%'
            and i.templateid IS NULL
            and i.itemid = hist.itemid
            and hist.clock > extract(epoch from now()) - 60*10 
        ) A
        GROUP BY a.host
    """    
    cur.execute( Query )
    rows = cur.fetchall()
    
    for row in rows:
        # Key Name
        key_name = row[0] + '.vpnstatus' 
        # 0 보다 크면 장애
        value = 1 if row[1] == 0 else 0
        redis.set(key_name, value)
        redis.expire(key_name, 60*10)
            
    logger.info ( "VPN Status : %s, %s" % ( key_name, value ))

    cur.close()
    redis.close()
    
if __name__ == "__main__":     
    init_logger()
    logger.info("Start")
    get_vpntotalcount()