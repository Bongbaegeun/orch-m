#-*- coding: utf-8 -*-
'''
Created on 2015. 9. 19.

@author: ohhara
'''
import time

def convertDicToStr( dic ):
    import json
    return json.dumps( dic, encoding='utf-8')

def GET_TABLE_INFO_USING_FKEY( table_name, column_name ):
    return """
    SELECT ku.table_name, ku.column_name
    FROM INFORMATION_SCHEMA.constraint_column_usage cu
        LEFT OUTER JOIN INFORMATION_SCHEMA.table_constraints tc ON cu.constraint_name=tc.constraint_name 
        LEFT OUTER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku ON cu.constraint_name=ku.constraint_name
    WHERE cu.table_name='%s' AND cu.column_name='%s' 
        AND tc.constraint_type='FOREIGN KEY' AND ku.constraint_schema='public' 
    GROUP BY ku.table_name, ku.column_name
    """%( table_name, column_name )

def REMOVE_ROW_NOUSE( tableName, column_name=None, val=None ):
    delSql = """DELETE FROM %s WHERE delete_dttm is not null"""%tableName
    if val != None:
        if type(val) == int or type(val) == float :
            delSql += """ AND %s=%s """%(column_name, str(val))
        else :
            delSql += """ AND %s='%s' """%(column_name, str(val).replace("""'""", '"'))
    
    return delSql

def REMOVE_ROW_NOUSE_FK( tableName, column_name, tableList, val=None ):
    delSql = """DELETE FROM %s WHERE delete_dttm is not null AND %s not in (
        SELECT %s FROM ( """%( tableName, column_name, column_name )
    
    isFirst = True
    for tbInfo in tableList :
        if isFirst :
            delSql += """ SELECT %s as %s FROM %s """%( tbInfo['column_name'], column_name, tbInfo['table_name'] )
            isFirst = False
        else :
            delSql += """ UNION SELECT %s as %s FROM %s """%( tbInfo['column_name'], column_name, tbInfo['table_name'] )
    
    delSql += """ ) as d WHERE %s is not null GROUP BY %s )"""%( column_name, column_name )
    
    if val != None:
        if type(val) == int or type(val) == float :
            delSql += """ AND %s=%s """%(column_name, str(val))
        else :
            delSql += """ AND %s='%s' """%(column_name, str(val).replace("""'""", '"'))
    
    return delSql


# SMS
def INSERT_SMS_MSG( userID, subject, msg, callBack, destInfo, destCount, nowDate, 
                     scheduleType=0, sendDate=None, callbackUrl=None, ktOfficeCode=None, cdrID=None):
    insSql = """ INSERT INTO SDK_SMS_SEND 
         ( USER_ID, SUBJECT, SMS_MSG, CALLBACK, DEST_INFO, DEST_COUNT, NOW_DATE, SCHEDULE_TYPE, SEND_DATE """
    valSql = """ VALUES ( '%s', '%s', '%s', '%s', '%s', %s, '%s', %s 
         """%( userID, subject, msg, callBack, destInfo, str(destCount), nowDate, str(scheduleType) )
     
    if sendDate != None :
        valSql += ( """ , '%s' """%sendDate )
    else:
        valSql += ( """ , '%s' """%nowDate )
    if callbackUrl != None :
        insSql += ( """ , CALLBACK_URL """ )
        valSql += ( """ , '%s' """%callbackUrl )
    if ktOfficeCode != None :
        insSql += ( """ , KT_OFFICE_CODE """ )
        valSql += ( """ , '%s' """%ktOfficeCode )
    if cdrID != None:
        insSql += ( """ , CDR_ID """ )
        valSql += ( """ , '%s' """%cdrID )
     
    insSql += ( """ ) """ )
    valSql += ( """ ) """ )
         
    return insSql + valSql

def GET_SMS_REPORT_DETAIL( smsMsgID ):
    return """ SELECT * FROM SDK_SMS_REPORT_DETAIL WHERE MSG_ID=%s """%str(smsMsgID)

## ZB
def GET_ZBDB_CURR_HIST_ONE_SERVER(host_name, itemKeyList, period):
    
    partitions_tablename = time.strftime('p%Y_%m_%d', time.localtime())

    return """
    SELECT host as host_name, key_ as item_key, value_int, value_str, clock
    FROM
        (
        SELECT *, ROW_NUMBER() over (PARTITION BY itemid ORDER BY clock DESC) rn
        FROM
        
            (
            SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
            FROM partitions.history_%s hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='%s' AND key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
            FROM history_log hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='%s' AND key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
            FROM history_str hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='%s' AND key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, null as value_int, value as value_str
            FROM history_text hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='%s' AND key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, value as value_int, null as value_str
            FROM partitions.history_uint_%s hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE h.host='%s' AND key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            ) all_hist
        
        ) recent_hist
    
    WHERE rn=1
    """%( partitions_tablename,
         host_name, itemKeyList, str(period), 
         host_name, itemKeyList, str(period), 
         host_name, itemKeyList, str(period), 
         host_name, itemKeyList, str(period), 
         partitions_tablename,
         host_name, itemKeyList, str(period))




def GET_ZBDB_CURR_HIST(itemKeyList, period):
    
    return """
    SELECT host as host_name, key_ as item_key, value, clock
    FROM
        (
        SELECT *, ROW_NUMBER() over (PARTITION BY itemid ORDER BY clock DESC) rn
        FROM
        
            (
            SELECT item.host, item.key_, hist.itemid, clock, value
            FROM history hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            
            UNION
            
            SELECT item.host, item.key_, hist.itemid, clock, value
            FROM history_uint hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE key_ in %s AND i.hostid=h.hostid
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            ) all_hist
        
        ) recent_hist
    
    WHERE rn=1
    """%( itemKeyList, str(period), 
          itemKeyList, str(period))


def GET_ZBDB_CURR_HIST_ICMPPING(itemKeyList, utime, period):
    return """
    SELECT host as host_name, key_ as item_key, value, clock
    FROM
        (
        SELECT *, ROW_NUMBER() over (PARTITION BY itemid ORDER BY clock DESC) rn
        FROM

            (
            SELECT item.host, item.key_, hist.itemid, clock, value
            FROM history hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE key_ in %s AND i.hostid=h.hostid AND delay = %s
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s

            UNION

            SELECT item.host, item.key_, hist.itemid, clock, value
            FROM history_uint hist, (
                    SELECT itemid, key_, i.hostid, host
                    FROM items i, hosts h
                    WHERE key_ in %s AND i.hostid=h.hostid AND delay = %s
                    ) item
            WHERE hist.itemid=item.itemid 
            AND hist.clock > %s
            ) all_hist

        ) recent_hist

    WHERE rn=1
    """ % (itemKeyList, str(period), str(utime),
           itemKeyList, str(period), str(utime))






def GET_ZBHIST_AVG_PER_PERIOD( host_name, item_key, sec, sDttm, eDttm ):
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    return """
    SELECT clk, val FROM (
        (
        SELECT clock/%s*%s as clk, round(avg(value), 2) as val
        FROM history_uint hist, items i, hosts h
        WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
        AND hist.clock BETWEEN %s AND %s
        GROUP BY clk
        )
        UNION
        (
        SELECT clock clk, round(value, 2) as val
        FROM history_uint hist, items i, hosts h
        WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND to_char(current_timestamp, 'YYYY-MM-DD HH24:MI')<='%s'
            AND hist.clock>cast(extract(epoch from now()) as int)/%s*%s
        )
        UNION
        (
        SELECT clock/%s*%s as clk, round(avg(value), 2) as val
        FROM history hist, items i, hosts h
        WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
        AND hist.clock BETWEEN %s AND %s
        GROUP BY clk
        )
        UNION
        (
        SELECT clock clk, round(value, 2) as val
        FROM history hist, items i, hosts h
        WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND to_char(current_timestamp, 'YYYY-MM-DD HH24:MI')<='%s'
            AND hist.clock>cast(extract(epoch from now()) as int)/%s*%s
        )) as stat
    WHERE val is not null
    ORDER BY clk desc
    """%( str(sec), str(sec), item_key, host_name,
          stm_epoch, etm_epoch,
          item_key, host_name, eDttm, str(sec), str(sec),
          str(sec), str(sec), item_key, host_name,
          stm_epoch, etm_epoch,
          item_key, host_name, eDttm, str(sec), str(sec) )



def GET_ZBHIST_MAX_PER_PERIOD( host_name, item_key, sec, sDttm, eDttm ):

    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    return """
    SELECT clk, val FROM (
        (
        SELECT clock/%s*%s as clk, round(max(value), 2) as val
        FROM history_uint hist, items i, hosts h
        WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
        AND hist.clock BETWEEN %s AND %s
        GROUP BY clk
        )
        UNION
        (
        SELECT clock/%s*%s as clk, round(max(value), 2) as val
        FROM history hist, items i, hosts h
        WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
        AND hist.clock BETWEEN %s AND %s
        GROUP BY clk
        )
        ) as stat
    WHERE val is not null
    ORDER BY clk desc
    """%( str(sec), str(sec), item_key, host_name,
          stm_epoch, etm_epoch,
          str(sec), str(sec), item_key, host_name,
          stm_epoch, etm_epoch)


def GET_ZBHIST_PER_PERIOD_2(host_name, item_key, sec, sDttm, eDttm):
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    yesterday=86400
    beforeweek=86400 * 7

    sql = """
    SELECT day, clk, max_val, avg_val 
    FROM (

            -- 금일
            SELECT 'D' as day, clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
            FROM history_uint hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk
            UNION
            SELECT 'D' as day, clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
            FROM history hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk

            UNION

            -- 어제
            SELECT 'D1' as day, clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
            FROM history_uint hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s 
            GROUP BY clk
            UNION
            SELECT 'D1' as day, clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
            FROM history hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s 
            GROUP BY clk

            UNION

            -- 7일전        
            SELECT 'D7' as day, clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
            FROM history_uint hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk
            UNION
            SELECT 'D7' as day, clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val
            FROM history hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk

            -- 금일 데이터 (단순 round )
            UNION 
            SELECT 'D' as day, clock clk, null as max_val, round(value, 2) as avg_val
            FROM history_uint hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND to_char(current_timestamp, 'YYYY-MM-DD HH24:MI')<='%s'
            AND hist.clock>cast(extract(epoch from now()) as int)/%s*%s
            UNION 
            SELECT 'D' as day, clock clk, null as max_val, round(value, 2) as avg_val
            FROM history hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND to_char(current_timestamp, 'YYYY-MM-DD HH24:MI')<='%s'
            AND hist.clock>cast(extract(epoch from now()) as int)/%s*%s
            
    ) as stat
    ORDER BY clk desc
    """ % (
        str(sec), str(sec), item_key, host_name,
        stm_epoch, etm_epoch,
        str(sec), str(sec), item_key, host_name,
        stm_epoch, etm_epoch,

        str(sec), str(sec), item_key, host_name,
        stm_epoch - yesterday, etm_epoch - yesterday,
        str(sec), str(sec), item_key, host_name,
        stm_epoch - yesterday, etm_epoch - yesterday,

        str(sec), str(sec), item_key, host_name,
        stm_epoch - beforeweek, etm_epoch - beforeweek,
        str(sec), str(sec), item_key, host_name,
        stm_epoch - beforeweek, etm_epoch - beforeweek,

        item_key, host_name, eDttm, str(sec), str(sec),
        item_key, host_name, eDttm, str(sec), str(sec)
    )
    return sql

# 2019. 8. 20 
# 상세 그래프 수정.
def GET_ZBHIST_PER_PERIOD_DETAIL(host_name, item_key, sec, sDttm, eDttm):
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    sql = """
    SELECT clk, min_val, avg_val, max_val
    FROM (

            -- 기간 지정 상세.
            SELECT clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val, round(min(value), 2) as min_val
            FROM history_uint hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk
            UNION
            SELECT clock/%s*%s as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val, round(min(value), 2) as min_val
            FROM history hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk

    ) as stat
    ORDER BY clk 
    """ % (
        str(sec), str(sec), item_key, host_name, stm_epoch, etm_epoch,
        str(sec), str(sec), item_key, host_name, stm_epoch, etm_epoch
    )
    return sql

def GET_ZBHIST_PER_PERIOD_TRENDS(host_name, item_key, sec, sDttm, eDttm):
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    sql = """
    SELECT clk, value_min as min_val, value_avg as avg_val, value_max as max_val
    FROM (

            -- 기간 지정 통계
            SELECT clock as clk, value_min, value_avg, value_max
            FROM trends_uint t,  items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND t.itemid=i.itemid 
            AND t.clock BETWEEN %s AND %s
            UNION
            -- 기간 지정 통계
            SELECT clock as clk, value_min, value_avg, value_max
            FROM trends t,  items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND t.itemid=i.itemid 
            AND t.clock BETWEEN %s AND %s
    ) as stat
    ORDER BY clk
    """ % (
        item_key, host_name, stm_epoch, etm_epoch,
        item_key, host_name, stm_epoch, etm_epoch
    )
    return sql


def GET_ZB_ALARM():
    return """
    SELECT message
    FROM 
    (
        SELECT ev.*, al.message, ROW_NUMBER() over (PARTITION BY objectid ORDER BY ev.clock DESC, ns DESC) rn
        FROM events ev, triggers tr, alerts al, (SELECT extract(epoch from (now() - interval '24 hour')) as c) clk
        WHERE ev.source=0 AND ev.object=0 AND ev.clock > clk.c
            AND tr.comments is not null AND tr.comments!='' AND tr.triggerid=ev.objectid 
            AND ev.eventid=al.eventid
    ) as t
    WHERE rn=1 AND value=1
    """

def GET_ZB_ITEM_STATE( itemStateKey ):
    return """
    SELECT total.host, CAST ((inact.inact_cnt*100.0)/(total.total_cnt) AS NUMERIC(1000,2)) perc
    FROM(
        SELECT h.host host, count(i.itemid) total_cnt
        FROM 
        (
            SELECT h.*
            FROM hosts h, items i
            WHERE i.key_='%s' AND i.hostid=h.hostid AND h.status=0 AND i.status=0
        ) h LEFT OUTER JOIN items i ON h.hostid=i.hostid
        WHERE h.hostid=i.hostid
        GROUP BY h.host
    ) total,
    (
        SELECT h.host host, count(i.itemid) inact_cnt
        FROM 
        (
            SELECT h.*
            FROM hosts h, items i
            WHERE i.key_='%s' AND i.hostid=h.hostid AND h.status=0 AND i.status=0
        ) h LEFT OUTER JOIN items i ON h.hostid=i.hostid AND i.state!=0 
        GROUP BY h.host
    ) inact
    WHERE total.host=inact.host
    """%(itemStateKey, itemStateKey)

## zba
def GET_ITEMINSTANCE_SEQ_BY_HOST_KEY(svr_obid, item_key):
    # VPN 장애는 MACRO 방식이라 고정값이 아님 
    # 예 :  "key": "vpnstatus.sh["mokforti.OB1"]",
    if item_key.find('vpnstatus.sh') > -1 :
        condition = "ki.monitemkey LIKE 'vpnstatus.sh%'"
    elif item_key.find('wanactive.sh') > -1:
        # snmp wan count가 0일때 장애 알람을 띄우기 위해 key 맞추기
        # itemKey : wanactive.sh(onebox.OB1) -> wanactive.sh["{HOST.NAME}"]
        condition = "ki.monitemkey LIKE 'wanactive.sh%'"
    else :
        condition = "ki.monitemkey = '%s'" % item_key
    
    return """ 
    SELECT ki.moniteminstanceseq as itemseq, ii.monitoryn, ii.displayyn
    FROM tb_mapzbkeyinstance ki, tb_server svr, tb_moniteminstance ii
    WHERE svr.onebox_id='%s' 
    AND svr.serverseq=ki.serverseq 
    AND ii.moniteminstanceseq=ki.moniteminstanceseq
    AND %s
    """%(svr_obid, condition)


def GET_ITEMINSTANCE_KEY_BY_HOST_ITEM(svr_uuid, item_seq):
    return """ 
    SELECT ki.monitemkey as itemkey, ii.unit, svr.onebox_id
    FROM tb_mapzbkeyinstance ki, tb_server svr, tb_moniteminstance ii
    WHERE svr.serveruuid='%s' AND ki.moniteminstanceseq=%s AND ki.serverseq=svr.serverseq 
        AND ki.moniteminstanceseq=ii.moniteminstanceseq
    """%(svr_uuid, str(item_seq))


def GET_ITEMINSTANCE_KEY_BY_MON_OBJECT(svrseq, mon_object, targetcode):
    return """ 
    SELECT ic.moniteminstanceseq, ic.monitemcatseq
    FROM  tb_moniteminstance ic, tb_montargetcatalog tc
    WHERE ic.serverseq=%s
    AND ic.monitorobject='%s'
    AND ic.delete_dttm is null  
    AND ic.montargetcatseq = tc.montargetcatseq
    AND tc.targetcode = '%s'
    """%(svrseq, mon_object, targetcode)

def GET_ITEMINSTANCE_KEY_BY_MON_OBJECT_SEQ(svrseq, mon_object, monitemcatseq):
    return """ 
    SELECT moniteminstanceseq, monitemcatseq
    FROM  tb_moniteminstance
    WHERE serverseq=%s 
    AND monitorobject='%s' 
    AND monitemcatseq = %s
    AND delete_dttm is null 
    """%(svrseq, mon_object, monitemcatseq)


def GET_ITEMCATSEQ_BY_SUL(svrseq, targetcode):
    return """ 
    SELECT ic.monitemcatseq
    FROM tb_monitemcatalog ic, tb_mongroupcatalog gc
    WHERE montargetcatseq in 
    (
        SELECT montargetcatseq
        FROM tb_moniteminstance
        WHERE serverseq = %s
        AND montargetcatseq in (
            SELECT tc.montargetcatseq
            FROM tb_monitemcatalog ic, tb_montargetcatalog tc, tb_mongroupcatalog gc 
            WHERE ic.mongroupcatseq = gc.mongroupcatseq
            AND ic.montargetcatseq = tc.montargetcatseq
            AND tc.targetcode='%s' 
            AND gc.groupname in ('net', 'vnet') 
            AND ic.monitortype in ('Tx Rate', 'Rx Rate', 'Status')
        )
        GROUP BY montargetcatseq, mongroupcatseq
    )
    AND ic.monitortype in ('Tx Rate', 'Rx Rate', 'Status')
    and ic.mongroupcatseq = gc.mongroupcatseq
    AND gc.groupname in ('net', 'vnet')
    """% (svrseq, targetcode)


def GET_SERVER_LIST(): 
    return """
    SELECT si.onebox_id as onebox_id, si.serverseq as svr_seq, si.servername as svr_name
    FROM tb_server si, 
        (SELECT serverseq FROM tb_moniteminstance WHERE delete_dttm is null GROUP BY serverseq) ss
    WHERE ss.serverseq=si.serverseq
    """

def GET_SERVER_TYPE(svr_seq):
    return """
    SELECT nfsubcategory as svr_type FROM tb_server WHERE serverseq=%s
    """%str(svr_seq)

def GET_SERVER_INFO(svr_seq):
    return """ SELECT * FROM tb_maphostinstance WHERE serverseq=%s """%str(svr_seq)

def GET_ITEMKEY_LIST():
    return """ 
    SELECT ikey.monitemkey as item_key
    FROM  tb_mapzbkeyinstance ikey, 
        (SELECT moniteminstanceseq FROM tb_moniteminstance WHERE delete_dttm is null AND realtimeyn='y' GROUP BY moniteminstanceseq) item
    WHERE item.moniteminstanceseq=ikey.moniteminstanceseq
    """

def GET_ITEMKEY_LIST_BY_SERVER( svr_seq ):
    return """ 
    SELECT ikey.monitemkey as item_key, period
    FROM  tb_mapzbkeyinstance ikey, 
        (SELECT moniteminstanceseq, period FROM tb_moniteminstance 
        WHERE serverseq=%s AND delete_dttm is null AND realtimeyn='y' AND monitoryn='y' 
        GROUP BY moniteminstanceseq) item
    WHERE item.moniteminstanceseq=ikey.moniteminstanceseq
    """%str(svr_seq)


## Perf
def INSERT_INIT_REALTIMEPERF( svrSeq, targetList=None ):
    insSql = """
    INSERT INTO tb_realtimeperf(
        SERVERSEQ, moniteminstanceseq, monitordttm, monitoredyn)
    (
        SELECT serverseq, moniteminstanceseq, now(), 'n'
        FROM tb_moniteminstance 
        WHERE serverseq=%s AND realtimeyn='y' AND monitoryn='y' AND delete_dttm is null 
    """%str(svrSeq)
    
    if targetList != None:
        insSql += ( """ AND montargetcatseq in %s """%targetList )
    
    insSql += ( """ ) """ )
    
    return insSql

def INSERT_INIT_REALTIMEPERF_BY_ITEM( svrSeq, itemSeq ):
    return """
    INSERT INTO tb_realtimeperf( moniteminstanceseq, serverseq, monitoredyn, monitordttm)
        VALUES ( %s, %s, 'n', now() )
    """%( str(itemSeq), str(svrSeq) )

def UPDATE_REALTIMEPERF( expirePeriod, val, clock, svr_obid, item_key ):
    return """ 
    INSERT INTO tb_realtimeperf(
        SERVERSEQ, moniteminstanceseq, monitorvalue, monitordttm, monitoredyn)
    (
        SELECT svr_seq, item_seq, val, mon_time, 
            CASE WHEN expire_time >= cur_time THEN 'y'ELSE 'n' END monitored
        FROM 
        (
            SELECT svr_seq, item_seq, val, period, to_timestamp(mon_clock) as mon_time, 
                to_timestamp(mon_clock) + (%s+period)*interval '1 second' as expire_time, now() as cur_time
            FROM 
            (
            SELECT key.serverseq as svr_seq, key.moniteminstanceseq as item_seq, period,
                '%s' as val, %s as mon_clock
            FROM tb_server svr, tb_mapzbkeyinstance key, tb_moniteminstance item
            WHERE svr.onebox_id='%s' AND key.serverseq=svr.serverseq 
                AND key.moniteminstanceseq=item.moniteminstanceseq 
                AND item.delete_dttm is null AND key.monitemkey='%s' 
            ) seq
            LEFT OUTER JOIN tb_realtimeperf perf ON seq.svr_seq=perf.serverseq AND seq.item_seq=perf.moniteminstanceseq
        ) time_comp
    )
    """%(str(expirePeriod), str(val), str(clock), svr_obid, item_key )


#######################################################
# 18.01.29 - lsh
# Zabbix 모니터값을 여러번 Insert 하던것을 서버별 한번으로 변경.
def UPDATE_REALTIMEPERF_NEW( expirePeriod, query):
    return """ 
    INSERT INTO tb_realtimeperf(
        SERVERSEQ, moniteminstanceseq, monitorvalue, monitordttm, monitoredyn)
    (
        SELECT svr_seq, item_seq, val, mon_time, 
            CASE WHEN expire_time >= cur_time THEN 'y'ELSE 'n' END monitored
        FROM 
        (
            SELECT svr_seq, item_seq, val, period, to_timestamp(mon_clock) as mon_time, 
                to_timestamp(mon_clock) + (%s+period)*interval '1 second' as expire_time, now() as cur_time
            FROM 
            (
            SELECT key.serverseq as svr_seq, key.moniteminstanceseq as item_seq, period,
                        zb.val as val, zb.clock as mon_clock
            FROM tb_server svr,
            		tb_mapzbkeyinstance key, 
		            tb_moniteminstance item,
		            ( %s ) zb 
            WHERE svr.onebox_id=zb.host_name 
		    AND key.serverseq=svr.serverseq 
                AND key.moniteminstanceseq=item.moniteminstanceseq 
                AND item.delete_dttm is null 
                AND key.monitemkey=zb.item_key
            ) seq
            LEFT OUTER JOIN tb_realtimeperf perf ON seq.svr_seq=perf.serverseq AND seq.item_seq=perf.moniteminstanceseq
        ) time_comp
    )
    """%(str(expirePeriod), query )

def UPDATE_REALTIMEPERF_FOR_EXPIRE(expire):
    return """
    UPDATE tb_realtimeperf perf SET monitoredyn='n' FROM tb_moniteminstance item
    WHERE perf.moniteminstanceseq=item.moniteminstanceseq
        AND perf.monitordttm + (%s+item.period)*interval '1 second' < now()
    """%str(expire)


# def UPDATE_REALTIMEPERF_FOR_EXPIRE(expire):
#     return """
#     UPDATE tb_realtimeperf perf SET monitoredyn='n' FROM tb_moniteminstance item, tb_server svr
#     WHERE perf.moniteminstanceseq=item.moniteminstanceseq
#         AND svr.serverseq = perf.serverseq
#         AND svr.nfsubcategory not in ('Fortinet')
#         AND perf.monitordttm + (%s+item.period)*interval '1 second' < now()
#     """%str(expire)


# def UPDATE_REALTIMEPERF_FOR_EXPIRE_FORTINET(expire):
#     return """
#     UPDATE tb_realtimeperf perf SET monitoredyn='n' FROM tb_moniteminstance item, tb_server svr
#     WHERE perf.moniteminstanceseq=item.moniteminstanceseq
#         AND svr.serverseq = perf.serverseq
#         AND svr.nfsubcategory in ('Fortinet')
#         AND perf.monitordttm + (%s+item.period)*interval '1 second' < now()
#     """%str(expire)


def UPDATE_REALTIMEPERF_FOR_ZBCHK(iSeq, value):
    return """
    UPDATE tb_realtimeperf SET monitorvalue='%s', monitoredyn='y', monitordttm=now()
    WHERE moniteminstanceseq=%s
    """%(str(value), str(iSeq))


















### Fault
## v2
def GET_SERVICE_NUMBER_BY_ITEMSEQ(itemSeq):
    return """
    SELECT service_number FROM tb_moniteminstance
    WHERE moniteminstanceseq = %s
    """%str(itemSeq)

def GET_THRESHOLD_CONDITION( itemCatSeq, grade ):
    return """
    SELECT condition FROM tb_monthresholdcatalog
    WHERE monitemcatseq=%s AND UPPER(fault_grade)=UPPER('%s') AND delete_dttm is null
    """%( str(itemCatSeq), grade )

def GET_UNRESOLVED_ALARM( itemSeq ):
    return """
    SELECT curalarmseq FROM tb_curalarm WHERE moniteminstanceseq=%s AND resolve_dttm is null
    """%str(itemSeq)

def GET_RESOLVED_ALARM( itemSeq ):
    return """
    SELECT rca.orgnamescode, svr.serverseq, svr.servername, tc.targetname, ii.monitoritem, ii.monitorobject,
        rca.resolve_methodcode, rca.curalarmseq, ii.visiblename, ii.value_type, 
        COALESCE((select c.customername from tb_customer c where c.customerseq = svr.customerseq), svr.servername) customername
    	,(select c.group_seq from tb_customer c where c.customerseq = svr.customerseq) group_seq
        ,(select cg.group_name from tb_customer c, tb_customer_group cg where c.customerseq = svr.customerseq and c.group_seq = cg.seq) group_name
	    ,svr.nfsubcategory nfsubcat
        ,svr.mgmtip mgmtip
        , rca.resolve_mon_gap, ii.unit
    FROM (
        SELECT ca.onebox_id, ca.montargetcatseq, ca.moniteminstanceseq, ca.orgnamescode, ca.resolve_methodcode, 
            ca.curalarmseq, (ca.resolve_dttm - ca.mon_dttm)::text as resolve_mon_gap
        FROM tb_curalarm ca
        WHERE ca.moniteminstanceseq=%s AND resolve_dttm is not null 
          AND '00:02:00' >= age(now(), resolve_dttm)
        ORDER BY ca.resolve_dttm desc limit 1
    ) rca
        LEFT OUTER JOIN tb_server svr ON rca.onebox_id=svr.onebox_id
        LEFT OUTER JOIN tb_montargetcatalog tc ON rca.montargetcatseq=tc.montargetcatseq
        LEFT OUTER JOIN tb_moniteminstance ii ON rca.moniteminstanceseq=ii.moniteminstanceseq
    """%str(itemSeq)


def GET_RESOLVED_ALARM_ARUBA( itemSeq ):
    return """
    select ca.curalarmseq, ca.device_id, (ca.resolve_dttm - ca.mon_dttm)::text as resolve_mon_gap,
        (select c.servername from tb_server_aruba c where c.device_id = ca.device_id) servername,
        (select c.customername from tb_customer_aruba c where c.customerseq = (select customerseq from tb_server_aruba where device_id = ca.device_id)) as orgnamescode,
        (select c.nfsubcategory from tb_server_aruba c where c.device_id = ca.device_id) nfsubcategory
        ,(select c.publicip from tb_server_aruba c where c.device_id = ca.device_id) publicip
        ,(select c.status from tb_server_aruba c where c.device_id = ca.device_id) status
    from tb_curalarm_aruba ca
    where curalarmseq = %s and resolve_dttm is not null 
          AND '00:02:00' >= age(now(), resolve_dttm)
    ORDER BY ca.resolve_dttm desc limit 1
    """%str(itemSeq)

def GET_ITEMINSTANCE_INFO_FOR_SMS( itemSeq ):
    return """
    SELECT svr.orgnamescode, ii.serverseq, svr.servername, tc.targetname, tc.targetversion, gc.groupname,
	    ii.monitoritem, ii.monitorobject, ii.unit, ii.visiblename, ii.value_type, 
	    COALESCE((select c.customername from tb_customer c where c.customerseq = svr.customerseq), svr.servername) customername
    	,(select c.group_seq from tb_customer c where c.customerseq = svr.customerseq) group_seq
	    ,(select cg.group_name from tb_customer c, tb_customer_group cg where c.customerseq = svr.customerseq and c.group_seq = cg.seq) group_name
	    ,svr.nfsubcategory nfsubcat
        ,svr.mgmtip mgmtip
	    ,(select nw.display_name from tb_onebox_nw nw where svr.serverseq = nw.serverseq and ii.monitorobject = nw.name ) display_name
    FROM tb_moniteminstance ii, tb_server svr, tb_montargetcatalog tc, tb_mongroupcatalog gc
    WHERE ii.moniteminstanceseq=%s AND svr.serverseq=ii.serverseq
        AND tc.montargetcatseq=ii.montargetcatseq AND gc.mongroupcatseq=ii.mongroupcatseq
    """%str(itemSeq)


def GET_ITEMINSTANCE_INFO_FOR_SMS_ARUBA( itemSeq ):
    return """
    select ca.curalarmseq, ca.device_id, (ca.resolve_dttm - ca.mon_dttm)::text as resolve_mon_gap,
        (select c.servername from tb_server_aruba c where c.device_id = ca.device_id) servername,
        (select c.customername from tb_customer_aruba c 
            where c.customerseq = (select customerseq from tb_server_aruba where device_id = ca.device_id)) as orgnamescode,
        (select c.nfsubcategory from tb_server_aruba c where c.device_id = ca.device_id) nfsubcategory
        ,(select c.publicip from tb_server_aruba c where c.device_id = ca.device_id) publicip
        ,(select c.status from tb_server_aruba c where c.device_id = ca.device_id) status
    from tb_curalarm_aruba ca
    where curalarmseq = %s
    """%str(itemSeq)


def GET_SMS_WEEK_FAULT_INFO ( serverseq, group_seq, fault_name ):
    return """
    SELECT 'ONEBOX' AS level_title
      , CASE EXTRACT ( 'dow' from current_timestamp ) WHEN '1' THEN monday WHEN '2' THEN tuesday WHEN '3' THEN wednesday 
                WHEN '4' THEN thursday WHEN '5' THEN friday WHEN '6' THEN saturday  WHEN '0' THEN sunday END AS today_yn
        , %s  AS fault_yn
        , allow_stm, allow_etm
        , deny_yn, deny_sdt, deny_edt
    FROM tb_smsschedule
    WHERE serverseq = %s
    UNION ALL
    SELECT 'GROUP'
      , CASE EXTRACT ( 'dow' from current_timestamp ) WHEN '1' THEN monday WHEN '2' THEN tuesday WHEN '3' THEN wednesday 
                WHEN '4' THEN thursday WHEN '5' THEN friday WHEN '6' THEN saturday  WHEN '0' THEN sunday END AS today_yn
        , %s AS fault_yn
        , allow_stm, allow_etm
        , deny_yn, deny_sdt, deny_edt
    FROM tb_smsschedule
    WHERE serverseq = 0
    AND group_seq = %s
    UNION ALL
    SELECT 'ALL'
      , CASE EXTRACT ( 'dow' from current_timestamp ) WHEN '1' THEN monday WHEN '2' THEN tuesday WHEN '3' THEN wednesday 
                WHEN '4' THEN thursday WHEN '5' THEN friday WHEN '6' THEN saturday  WHEN '0' THEN sunday END AS today_yn
        , %s AS fault_yn
        , allow_stm, allow_etm
        , deny_yn, deny_sdt, deny_edt
    FROM tb_smsschedule
    WHERE serverseq = -1
    AND group_seq = -1
    """% (fault_name, serverseq, fault_name, group_seq, fault_name)


def GET_SMSUSERS( orgName, svrSeq=None ):
    # 2019. 6.26 - lsh
    # orgName 을 변경할수 있어 유저목록 조회가 안되는 이슈
    # 목동으로 고정함.

    orgName_fix = '목동'
    sql = """
    SELECT username as name, regexp_replace(hp_num, '-', '', 'g') as phone_num, sp.smsuserseq 
    FROM tb_smsuserlist sul, tb_smspolicy sp
    WHERE sp.smsuserseq=sul.smsuserseq AND sul.smsreceiveyn='Y' AND
        ( (sp.orgnamescode='중앙') or (sp.orgnamescode='%s' AND sp.serverseq is null) """ % orgName_fix
    
    if svrSeq != None:
        sql += ( """ OR sp.serverseq=%s """%str(svrSeq) )
    
    sql += ( ' ) ')
    
    return sql

# def GET_SMSGRADE():
#     qry = "SELECT grade FROM tb_smssendgrade WHERE send_yn = 'y'"
#     return qry

def GET_SMSGRADE():
    qry = """select grade, 'status' as value_type from tb_smssendgrade where status_send_yn = 'y'
            union all
            select grade, 'perf' as value_type from tb_smssendgrade where perf_send_yn = 'y'"""
    return qry

def GET_SMSSTATUS_FOR_HA():
    return """ SELECT * FROM tb_smssendstatus WHERE res_dttm is null"""

def INSERT_CURR_ALARM( dttm, itemVal, alertGrade, isAlert, trig_name, itemSeq, service_number ):
    if service_number == None:
        service_number = "null"
    else:
        service_number = "'" + service_number + "'"
    
    return """
    INSERT INTO tb_curalarm(
        customerseq, orgnamescode, serveruuid, onebox_id, nsseq, vnfseq, vdu_uuid, 
        moniteminstanceseq, monitortype, monitorobject, montargetcatseq, mongroupcatseq, 
        mon_dttm, monitorvalue, faultgradecode, faultstagecode, faultsummary, service_number )
     (
        SELECT cust_seq, org_code, svr_uuid, onebox_id, ns_seq, nf_seq, vd_uuid, item_seq, item_type, item_obj, target_seq, group_seq,
                    to_timestamp('%s', 'yyyy-mm-dd hh24:mi:ss'), %s, '%s', '%s', '%s', %s
        FROM (SELECT moniteminstanceseq,
                svr.customerseq           cust_seq, 
                svr.orgnamescode          org_code, 
                svr.serveruuid            svr_uuid,
                svr.onebox_id             onebox_id,
                item.moniteminstanceseq   item_seq, 
                item.monitortype          item_type, 
                item.monitorobject        item_obj,
                item.montargetcatseq      target_seq, 
                item.mongroupcatseq       group_seq
            FROM tb_moniteminstance item, tb_server svr
            WHERE item.moniteminstanceseq=%s AND svr.serverseq=item.serverseq ) as cust
        LEFT OUTER JOIN 
            (SELECT moniteminstanceseq, nfr.nsseq ns_seq, nfr.nfseq nf_seq, vdu.uuid vd_uuid
            FROM tb_moniteminstance item, tb_montargetcatalog tc, tb_server svr
                LEFT OUTER JOIN tb_nfr nfr ON nfr.nsseq=svr.nsseq
                LEFT OUTER JOIN tb_vdu vdu ON vdu.nfseq=nfr.nfseq AND vdu.status='Active'
                LEFT OUTER JOIN tb_montargetvdud tv ON svr.serverseq = tv.serverseq
            WHERE item.moniteminstanceseq=%s AND svr.serverseq=item.serverseq
                AND tc.montargetcatseq=item.montargetcatseq -- AND vdu.vdudseq=tc.vdudseq
                AND tv.montargetcatseq = tc.montargetcatseq AND tv.vdudseq = vdu.vdudseq
            ) as nfv ON cust.moniteminstanceseq=nfv.moniteminstanceseq
    )
    """%(str(dttm), str(itemVal), alertGrade, isAlert, trig_name, service_number, str(itemSeq), str(itemSeq))

def INSERT_HIST_ALARM(currSeq):
    return """
    INSERT INTO tb_histalarm(
        curalarmseq, mon_dttm, customerseq, orgnamescode, 
        serveruuid, onebox_id, vnfseq, vdu_uuid, moniteminstanceseq, monitortype, 
        monitorobject, monitorvalue, faultgradecode, faultstagecode, 
        perceive_dttm, perceive_user, perceive_detail, resolve_dttm, 
        resolve_user, resolve_methodcode, resolve_detail, perceivelasthour, 
        montargetcatseq, mongroupcatseq, faultsummary, reg_dttm, nsseq, service_number)
    ( SELECT
        curalarmseq, mon_dttm, customerseq, orgnamescode, 
        serveruuid, onebox_id, vnfseq, vdu_uuid, moniteminstanceseq, monitortype, 
        monitorobject, monitorvalue, faultgradecode, faultstagecode, 
        perceive_dttm, perceive_user, perceive_detail, resolve_dttm, 
        resolve_user, resolve_methodcode, resolve_detail, perceivelasthour, 
        montargetcatseq, mongroupcatseq, faultsummary, reg_dttm, nsseq, service_number
    FROM tb_curalarm WHERE curalarmseq=%s )
    """%str(currSeq)

def INSERT_HIST_ALARM_FOR_SYNC_ALL():
    return """
    INSERT INTO tb_histalarm(
        curalarmseq, mon_dttm, customerseq, orgnamescode, 
        serveruuid, onebox_id, vnfseq, vdu_uuid, moniteminstanceseq, monitortype, 
        monitorobject, monitorvalue, faultgradecode, faultstagecode, 
        perceive_dttm, perceive_user, perceive_detail, resolve_dttm, 
        resolve_user, resolve_methodcode, resolve_detail, perceivelasthour, 
        montargetcatseq, mongroupcatseq, faultsummary, reg_dttm, nsseq)
    (
        SELECT
            curalarmseq, mon_dttm, customerseq, orgnamescode, 
            serveruuid, onebox_id, vnfseq, vdu_uuid, moniteminstanceseq, monitortype, 
            monitorobject, monitorvalue, faultgradecode, faultstagecode, 
            perceive_dttm, perceive_user, perceive_detail, resolve_dttm, 
            resolve_user, resolve_methodcode, resolve_detail, perceivelasthour, 
            montargetcatseq, mongroupcatseq, faultsummary, reg_dttm, nsseq
        FROM tb_curalarm 
        WHERE curalarmseq IN
	        ( SELECT curalarmseq FROM tb_curalarm
	            EXCEPT
	            SELECT curalarmseq FROM tb_histalarm
	        )
    )
    """

def INSERT_SMS_HIST( isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeq=None, smsMsgId=None ):
    smsID = ( lambda x : """%s"""%x if x != None else 'null')(smsMsgId)
    resDttm = ( lambda x : """now()""" if x != False else 'null')(isResult)
    valSql = ''
    orgName_fix = '목동'
    insSql = """ INSERT INTO tb_smssendstatus(
        create_dttm, orgnamescode, monitortarget, servername, monitoritem,  
        monitortype, send_status, send_error, smsmsgid, res_dttm, curalarmseq, service_number """

    # if smsID == 'null' and resDttm == 'null':
    #     valSql = """
    #         ( SELECT now(), orgnamescode, targetcode, servername, groupname,
    #             monitortype, '%s', '%s', null, null, %s, ii.service_number
    #         """ % (str(sendStatus).upper(), str(error), curAlarmSeq)
    # elif smsID == 'null':
    #     valSql = """
    #         ( SELECT now(), orgnamescode, targetcode, servername, groupname,
    #             monitortype, '%s', '%s', null, %s, %s, ii.service_number
    #         """ % (str(sendStatus).upper(), str(error), resDttm, curAlarmSeq)
    # elif resDttm == 'null':
    #     valSql = """
    #         ( SELECT now(), orgnamescode, targetcode, servername, groupname,
    #             monitortype, '%s', '%s', %s, null, %s, ii.service_number
    #         """ % (str(sendStatus).upper(), str(error), smsID, curAlarmSeq)
    # else:
    valSql = """
        ( SELECT now(), '%s', targetcode, servername, groupname,
            monitortype, '%s', '%s', %s, %s, %s, ii.service_number
        """ % (orgName_fix, str(sendStatus).upper(), str(error), smsID, resDttm, curAlarmSeq)

    valSql1 = """
            FROM tb_server svr, tb_moniteminstance ii, tb_montargetcatalog tc, tb_mongroupcatalog gc
            WHERE ii.moniteminstanceseq=%s AND ii.serverseq=svr.serverseq
                AND ii.montargetcatseq=tc.montargetcatseq AND ii.mongroupcatseq=gc.mongroupcatseq
            )""" % (str(itemSeq))

    if userSeq != None :
        insSql += ( """ , userhpnum, smsuserseq """)
        valSql += ( """ , (SELECT hp_num FROM tb_smsuserlist WHERE smsuserseq=%s), %s """%(userSeq, userSeq))
    # else :
    #     valSql = valSql%('')
    
    insSql += ( ' ) ')
    valSql += valSql1
    
    return insSql + valSql


def INSERT_SMS_HIST_ARUBA(isResult, itemSeq, sendStatus, error, curAlarmSeq, userSeq=None, smsMsgId=None):
    smsID = (lambda x: """%s""" % x if x != None else 'null')(smsMsgId)
    resDttm = (lambda x: """now()""" if x != False else 'null')(isResult)
    curAlarmSeq = (lambda x: """%s""" if x != None else 'null')(curAlarmSeq)
    valSql = ''
    orgName_fix = '목동'
    insSql = """ INSERT INTO tb_smssendstatus_aruba(
        create_dttm, orgnamescode, monitortarget, servername, monitoritem,  
        monitortype, send_status, send_error, smsmsgid, res_dttm, service_number, curalarmseq """

    valSql = """
        ( SELECT now(), '%s', nfsubcategory, servername, 'net',
            'SVR Connection', '%s', '%s', %s, %s, '', %s
        """ % (orgName_fix, str(sendStatus).upper(), str(error), smsID, resDttm, itemSeq)

    if userSeq != None:
        insSql += (""" , userhpnum, smsuserseq """)
        valSql += (""" , (SELECT hp_num FROM tb_smsuserlist WHERE smsuserseq=%s), %s """ % (userSeq, userSeq))
    # else :
    #     valSql = valSql%('')

    valSql1 = """
                FROM tb_server_aruba svr, tb_curalarm_aruba ca 
                WHERE svr.device_id = ca.device_id and ca.curalarmseq = %s
                )
                """ % (itemSeq)

    insSql += (' ) ')
    valSql += valSql1

    return insSql + valSql


def UPDATE_SERVER_ADDR(svr_seq, svr_new_ip, svr_mod_desc):
    sql = """
    UPDATE tb_maphostinstance SET mgmtip='%s', last_mod_dttm=now() 
    """%(svr_new_ip)
    
    if svr_mod_desc != None :
        sql += """ , mod_desc='%s' """%(svr_mod_desc)
    
    sql += """ WHERE serverseq=%s """%str(svr_seq)
    
    return sql

def UPDATE_CURR_ALARM_RESOLVE( dttm, resolveName, state, itemSeq, alertGrade):
    return """
    UPDATE tb_curalarm
    SET resolve_dttm=to_timestamp('%s', 'yyyy-mm-dd hh24:mi:ss'), resolve_methodcode='%s', faultstagecode='%s'
    WHERE moniteminstanceseq=%s AND faultgradecode='%s' AND resolve_dttm is null
    """%(str(dttm), resolveName, state, str(itemSeq), alertGrade)

def UPDATE_HIST_ALARM_RESOLVE( dttm, resolveName, state, itemSeq, alertGrade):
    return """
    UPDATE tb_histalarm
    SET resolve_dttm=to_timestamp('%s', 'yyyy-mm-dd hh24:mi:ss'), resolve_methodcode='%s', faultstagecode='%s'
    WHERE moniteminstanceseq=%s AND faultgradecode='%s' AND resolve_dttm is null
    """%(str(dttm), resolveName, state, str(itemSeq), alertGrade)

def UPDATE_HIST_ALARM_FOR_SYNC_RESOLVE():
    return """
    UPDATE tb_histalarm ha
    SET resolve_dttm=ca.resolve_dttm, resolve_methodcode=ca.resolve_methodcode, faultstagecode=ca.faultstagecode
    FROM (
        SELECT * FROM tb_curalarm WHERE resolve_dttm is not null 
        ) ca
    WHERE ha.curalarmseq=ca.curalarmseq AND ( ha.resolve_dttm!=ca.resolve_dttm OR ha.resolve_methodcode!=ca.resolve_methodcode
        OR ha.faultstagecode!=ca.faultstagecode )
    """

def UPDATE_CURR_ALARM_SYNC( itemSeq, resolveName, state ):
    return """
    UPDATE tb_curalarm ca SET resolve_dttm=now(), resolve_methodcode='%s', faultstagecode='%s'
    FROM tb_moniteminstance ii,
        (SELECT moniteminstanceseq, serverseq, monitemcatseq, monitorobject FROM tb_moniteminstance WHERE moniteminstanceseq=%s) ii_1
    WHERE ( (ii_1.monitemcatseq is not null AND ii.monitemcatseq=ii_1.monitemcatseq AND ii.serverseq=ii_1.serverseq) 
            OR (ii_1.monitemcatseq is null AND ii.moniteminstanceseq=ii_1.moniteminstanceseq) )
        AND ii.monitorobject=ii_1.monitorobject
        AND ca.moniteminstanceseq=ii.moniteminstanceseq AND ca.resolve_dttm is null
    """%( resolveName, str(state), str(itemSeq) )

def UPDATE_CURR_ALARM_ACK_RELEASE():
    return """
    UPDATE tb_curalarm SET faultstagecode='발생', 
        perceive_dttm=NULL, perceive_user=NULL, perceive_detail=NULL, perceivelasthour=NULL
    WHERE faultstagecode='인지' AND perceive_dttm + (perceivelasthour)*interval '1 hour' < now()
    """

def UPDATE_HIST_ALARM_SYNC_ACK():
    return """
    UPDATE tb_histalarm ha
    SET faultstagecode=ca.faultstagecode, perceive_dttm=ca.perceive_dttm, perceive_user=ca.perceive_user,
        perceive_detail=ca.perceive_detail, perceivelasthour=ca.perceivelasthour
    FROM (
        SELECT ca.* FROM tb_curalarm ca, tb_histalarm ha WHERE ha.perceive_dttm is not null AND ha.curalarmseq=ca.curalarmseq
        ) ca
    WHERE ha.curalarmseq=ca.curalarmseq AND ( ha.faultstagecode!=ca.faultstagecode OR ha.perceive_dttm!=ca.perceive_dttm
        OR ha.perceive_user!=ca.perceive_user OR ha.perceive_detail!=ca.perceive_detail OR ha.perceivelasthour!=ca.perceivelasthour )
    """

def UPDATE_CURR_ALARM_FOR_DEL_SVR( svr_obid, target_list, resolveDetail ):
    sql = """
    UPDATE tb_curalarm SET resolve_dttm=now(), resolve_methodcode='%s', faultstagecode='해제'
    WHERE onebox_id='%s' AND resolve_dttm is null
    """%( resolveDetail, svr_obid )
    
    if target_list != None:
        sql += ( """ AND montargetcatseq in %s """%(target_list) )
    
    return sql

def UPDATE_CURR_ALARM_FOR_DEL_ITEMCAT( itemCatSeq, resolveDetail ):
    return """
    UPDATE tb_curalarm ca SET resolve_dttm=now(), resolve_methodcode='%s', faultstagecode='해제'
    FROM tb_moniteminstance ii
    WHERE ii.monitemcatseq=%s AND ii.delete_dttm is null 
        AND ii.moniteminstanceseq=ca.moniteminstanceseq AND ca.resolve_dttm is null
    """%( resolveDetail, str(itemCatSeq) )

def UPDATE_CURR_ALARM_FOR_MOD_OBJ( itemSeq, resolveDetail ):
    return """
    UPDATE tb_curalarm ca SET resolve_dttm=now(), resolve_methodcode='%s', faultstagecode='해제'
    WHERE ca.moniteminstanceseq=%s AND ca.resolve_dttm is null
    """%( resolveDetail, str(itemSeq) )

def UPDATE_CURR_ALARM_NFV_FOR_RESUME( svrSeq, targetSeq ):
    return """
    UPDATE tb_curalarm ca SET nsseq=nfr.nsseq, vnfseq=nfr.nfseq, vdu_uuid=vdu.uuid
    FROM tb_montargetcatalog tc, tb_server svr
        LEFT OUTER JOIN tb_nfr nfr ON nfr.nsseq=svr.nsseq
        LEFT OUTER JOIN tb_vdu vdu ON vdu.nfseq=nfr.nfseq AND vdu.status='Active'
        LEFT OUTER JOIN tb_montargetvdud tv ON tv.serverseq=svr.serverseq
    WHERE svr.serverseq=%s AND svr.onebox_id=ca.onebox_id 
        AND tc.montargetcatseq=%s AND tc.montargetcatseq=ca.montargetcatseq 
        AND tv.montargetcatseq = tc.montargetcatseq AND tv.vdudseq = vdu.vdudseq
    """%(str(svrSeq), str(targetSeq))

def UPDATE_HIST_ALARM_FOR_SYNC_RESUME( svrSeq, targetSeq ):
    return """
    UPDATE tb_histalarm ha
    SET nsseq=ca.nsseq, vnfseq=ca.vnfseq, vdu_uuid=ca.vdu_uuid
    FROM (
        SELECT ca.* FROM tb_curalarm ca, tb_server svr 
        WHERE svr.serverseq=%s AND svr.onebox_id=ca.onebox_id AND ca.montargetcatseq=%s
        ) ca
    WHERE ha.curalarmseq=ca.curalarmseq AND ( ha.nsseq!=ca.nsseq OR ha.vnfseq!=ca.vnfseq
        OR ha.vdu_uuid!=ca.vdu_uuid )
    """%(str(svrSeq), str(targetSeq))

def UPDATE_SMS_REPORT( sendStatus, _error, curAlarmSeq, userSeq, smsMsgID ):
    error = (lambda x : 'null' if x == None or x == '' else """'%s'"""%x)(_error)
    return """
    UPDATE tb_smssendstatus SET send_status='%s', send_error=%s, res_dttm=now()
    WHERE curalarmseq=%s AND smsuserseq=%s AND smsmsgid=%s
    """%( str(sendStatus).upper(), error, str(curAlarmSeq), str(userSeq), str(smsMsgID) )


def UPDATE_SMS_REPORT_ARUBA( sendStatus, _error, userSeq, smsMsgID ):
    error = (lambda x : 'null' if x == None or x == '' else """'%s'"""%x)(_error)
    return """
    UPDATE tb_smssendstatus_aruba SET send_status='%s', send_error=%s, res_dttm=now()
    WHERE smsuserseq=%s AND smsmsgid=%s
    """%( str(sendStatus).upper(), error, str(userSeq), str(smsMsgID) )


def UPDATE_HIST_ALARM_FOR_SYNC_INSERT():
    return """
    INSERT INTO tb_histalarm(
        curalarmseq, mon_dttm, customerseq, orgnamescode, 
        serveruuid, onebox_id, vnfseq, vdu_uuid, moniteminstanceseq, monitortype, 
        monitorobject, monitorvalue, faultgradecode, faultstagecode, 
        perceive_dttm, perceive_user, perceive_detail, resolve_dttm, 
        resolve_user, resolve_methodcode, resolve_detail, perceivelasthour, 
        montargetcatseq, mongroupcatseq, faultsummary, reg_dttm, nsseq)
    ( SELECT
        curalarmseq, mon_dttm, customerseq, orgnamescode, 
        serveruuid, onebox_id, vnfseq, vdu_uuid, moniteminstanceseq, monitortype, 
        monitorobject, monitorvalue, faultgradecode, faultstagecode, 
        perceive_dttm, perceive_user, perceive_detail, resolve_dttm, 
        resolve_user, resolve_methodcode, resolve_detail, perceivelasthour, 
        montargetcatseq, mongroupcatseq, faultsummary, reg_dttm, nsseq
    FROM tb_curalarm
    WHERE curalarmseq not in (SELECT curalarmseq FROM tb_histalarm GROUP BY curalarmseq)
    ORDER BY curalarmseq )
    """

def UPDATE_HIST_ALARM_FOR_SYNC_ALL():
    return """
    UPDATE tb_histalarm ha
    SET resolve_dttm=ca.resolve_dttm, resolve_methodcode=ca.resolve_methodcode, 
        resolve_user=ca.resolve_user, resolve_detail=ca.resolve_detail,
        faultstagecode=ca.faultstagecode, faultsummary=ca.faultsummary,
        perceive_dttm=ca.perceive_dttm, perceive_user=ca.perceive_user, 
        perceive_detail=ca.perceive_detail, perceivelasthour=ca.perceivelasthour, 
        nsseq=ca.nsseq, vnfseq=ca.vnfseq, vdu_uuid=ca.vdu_uuid
    FROM (
        SELECT ca.* FROM tb_curalarm ca, tb_histalarm ha
        WHERE ca.curalarmseq=ha.curalarmseq AND (
            ca.resolve_dttm!=ha.resolve_dttm OR ca.resolve_methodcode!=ha.resolve_methodcode OR 
            ca.resolve_user!=ha.resolve_user OR ca.resolve_detail!=ha.resolve_detail OR
            ca.faultstagecode!=ha.faultstagecode OR ca.faultsummary!=ha.faultsummary OR
            ca.perceive_dttm!=ha.perceive_dttm OR ca.perceive_user!=ha.perceive_user OR 
            ca.perceive_detail!=ha.perceive_detail OR ca.perceivelasthour!=ha.perceivelasthour OR 
            ca.nsseq!=ha.nsseq OR ca.vnfseq!=ha.vnfseq OR ca.vdu_uuid!=ha.vdu_uuid )
        ) as ca
    WHERE ha.curalarmseq=ca.curalarmseq
    """

def UPDATE_REALTIMEPERF_FOR_SYSC(itemSeq, itemVal):
    return """
    UPDATE tb_realtimeperf 
    SET monitoredyn='y', monitorvalue='%s', monitordttm=now()
    WHERE moniteminstanceseq=%s
    """% (str(itemVal), str(itemSeq))



















### Perf



### Mon

def GET_ITEM_KEY_BY_SEQ(item_seq):
    """아이템 시퀀스를 바탕으로 자빅스의 키로 사용하는 값 불러오기
    """
    return """
        select
            key
        from tb_zbkeycatalog
        where monitemcatseq = %s
    """ % (item_seq)

def GET_TEMPLATE_NAME_BY_SEQ(item_seq):
    return """
        select
            tc.montargetcatseq, tc.targetname, tc.targetversion
        from tb_montargetcatalog as tc
        left outer join tb_monitemcatalog as ic on tc.montargetcatseq = ic.montargetcatseq
        where ic.monitemcatseq = %s
    """ % (item_seq)

def GET_TEMPLATE_ITEM(monitemcatseq):
    """템플릿에 속한 아이템 정보 불러오기
    """
    return """SELECT 
    """

def UPDATE_TEMPLATE_ITEM(monitemcatseq, params):
    """템플릿에 속한 감시항목 수정
    params['visiblename']: 감시항목 명
    params['period']: 감시주기
    params['realtimeyn']: 실시간 감시
    """
    valueQuery = ""
    qry = "UPDATE tb_monitemcatalog SET "

    if "visiblename" in params and params['visiblename'] != None:
        valueQuery += ", visiblename = '" + params['visiblename'] + "' "
    if "period" in params and params['period'] != None:
        valueQuery += ", period = '" + params['period'] + "' "
    if "realtimeyn" in params and params['realtimeyn'] != None:
        valueQuery += ", realtimeyn = '" + params['realtimeyn'] + "' "
    valueQuery = valueQuery[1:]

    qry = qry + valueQuery + " WHERE monitemcatseq = " + str(monitemcatseq)
    return qry

def UPDATE_TEMPLATE_ITEM_GUIDE(monitemcatseq, guide):
    """알람 가이드 수정
    """
    return """UPDATE tb_monalarmguide AS ag
        SET guide = '%s'
        FROM tb_monitemcatalog AS ic
        WHERE ag.monalarmguideseq = ic.monalarmguideseq AND ic.monitemcatseq = %s""" % (guide, monitemcatseq)

def UPDATE_TEMPLATE_THRESHOLD(monitemcatseq, condition, conditionType, repeat, fault_grade):
    """
    :param int monitemcatseq: 감시항목 시퀀스
    :param string condition: 조건
    :param string conditionType: 조건 유형. 이상, 이하
    :param int repeat: 반복 주기
    :param string fault_grade: 장애 등록. critical, minor, major, warning
    """
    return """UPDATE tb_monthresholdcatalog AS tc
        SET condition = '%s',
        repeat = '%s',
        condition_type = '%s'
        FROM tb_monitemcatalog AS ic
        where tc.monitemcatseq=ic.monitemcatseq AND ic.monitemcatseq = %s AND tc.fault_grade = '%s'
    """ % (condition, repeat, conditionType, monitemcatseq, fault_grade)

def UPDATE_TEMPLATE_NAME(monitemcatseq, name):
    return "UPDATE tb_monitemcatalog SET visiblename = '%s' WHERE monitemcatseq = %s" % (name, monitemcatseq)

def UPDATE_TEMPLATE_PERIOD(item_seq, period):
    return "UPDATE tb_monitemcatalog SET period = '%s' WHERE monitemcatseq = %s" % (period, item_seq)

def UPDATE_TEMPLATE_ITEM_PERIOD(item_seq, period):
    return "UPDATE tb_moniteminstance SET period = '%s' where monitemcatseq = %s" % (period, item_seq)

def UPDATE_TEMPLATE_REALTIME(item_seq, period):
    return "UPDATE tb_monitemcatalog SET realtimeyn = '%s' WHERE monitemcatseq = %s" % (period, item_seq)

def UPDATE_TEMPLATE_STATISTICS(item_seq, statistics_yn):
    return "UPDATE tb_monitemcatalog SET statistics_yn = '%s' WHERE monitemcatseq = %s" % (statistics_yn, item_seq)

def UPDATE_TEMPLATE_GUIDE(item_seq, guide):
    return """UPDATE tb_monalarmguide as ag
        SET guide = '%s'
        FROM tb_monitemcatalog as tc
        where ag.monalarmguideseq = tc.monalarmguideseq and monitemcatseq = %s
    """ % (guide, item_seq)

def GET_ITEM_CATALOG_NAME(item_seq):
    qry = """SELECT
            monitoritem
        FROM tb_monitemcatalog
        WHERE monitemcatseq = %s""" % item_seq
    return qry

def GET_TEMPLATE_SEQ(montargetcatseq):
    """vdud와 템플릿이 특정 서버에 매핑 되어 있는지 검사
    :param int montargetcatseq: tb_montargetcatalog 테이블의 시퀀스
    """
    return """SELECT montargetcatseq FROM tb_montargetcatalog WHERE montargetcatseq='%s' AND delete_dttm is null"""%str(montargetcatseq)

def GET_VDUD_TARGET_MAPPING(serverseq, montargetcatseq, vdudseq):
    return """SELECT
            serverseq, montargetcatseq, vdudseq
        FROM tb_montargetvdud
        WHERE serverseq = %s AND montargetcatseq = %s AND vdudseq = %s
        LIMIT 1
    """%(str(serverseq), str(montargetcatseq), str(vdudseq))

def INSERT_VDUD_TARGET_MAPPING(serverseq, montargetcatseq, vdudseq):
    return """INSERT INTO tb_montargetvdud (serverseq, montargetcatseq, vdudseq) VALUES('%s', '%s', '%s')"""%(str(serverseq), str(montargetcatseq), str(vdudseq))

def DELETE_VDUD_TARGET_MAPPING(serverseq, montargetcatseq):
    return """DELETE FROM tb_montargetvdud WHERE serverseq = %s AND montargetcatseq = %s""" % (serverseq, montargetcatseq)

def GET_SERVER_CNT_BY_SEQ( svr_seq ):
    return """SELECT serverseq FROM tb_maphostinstance WHERE serverseq=%s"""%str(svr_seq)

def GET_ITEM_CNT_BY_SERVER( svr_seq ):
    return """SELECT moniteminstanceseq FROM tb_moniteminstance WHERE serverseq=%s AND delete_dttm is null"""%str(svr_seq)

def GET_KEY_CNT_BY_SERVER( svr_seq ):
    return """SELECT moniteminstanceseq FROM tb_mapzbkeyinstance WHERE serverseq=%s"""%str(svr_seq)

def GET_KEY_LIST_BY_SERVER( svr_seq ):
    return """SELECT monitemkey as key FROM tb_mapzbkeyinstance WHERE serverseq=%s"""%str(svr_seq)

def GET_KEYCAT_LIST_BY_SERVER( svr_seq ):
    return """
    SELECT regexp_replace(key, '%s', '*') as key FROM tb_zbkeycatalog WHERE monitemcatseq in 
        (
        SELECT monitemcatseq
        FROM tb_moniteminstance
        WHERE monitemcatseq is not null AND delete_dttm is null and serverseq=%s
        GROUP BY monitemcatseq
        )"""%( '%s', str(svr_seq) )

def GET_KEYCAT_LIST_BY_TARGET( target_list ):
    return """
    SELECT key, count(key) cnt FROM (
        SELECT key as key
        FROM tb_monitemcatalog ic, tb_zbkeycatalog kc
        WHERE ic.delete_dttm is null AND kc.delete_dttm is null
            AND ic.montargetcatseq in %s AND ic.monitemcatseq=kc.monitemcatseq
    
        UNION
    
        SELECT dc.zbkey as key
        FROM tb_monitemcatalog ic, tb_zbdiscoverymap dm
            LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
        WHERE ic.montargetcatseq in %s AND ic.delete_dttm is null
            AND ic.monitemcatseq=dm.monitemcatseq
    ) as k
    GROUP BY key
    """%(str(target_list), str(target_list))

def GET_KEY_INFO_BY_KEY( key ):
    return """
    SELECT targetname, groupname, monitoritem
    FROM tb_zbkeycatalog kc, tb_monitemcatalog ic, tb_mongroupcatalog gc, tb_montargetcatalog tc
    WHERE kc.delete_dttm is null AND gc.delete_dttm is null AND tc.delete_dttm is null
        AND kc.key='%s' AND ic.monitemcatseq=kc.monitemcatseq
        AND ic.mongroupcatseq=gc.mongroupcatseq AND tc.montargetcatseq=ic.montargetcatseq
    """%key

def GET_KEY_FOR_ADD( targetSeq, key, keyParamType=None ):
    sql = """
    SELECT zbkeycatseq 
    FROM tb_zbkeycatalog kc
        LEFT OUTER JOIN tb_monitemcatalog ic ON kc.monitemcatseq=ic.monitemcatseq
    WHERE ic.montargetcatseq=%s AND ic.delete_dttm is null AND kc.delete_dttm is null
    """%str(targetSeq)
    
    if keyParamType != None :
        sql += """ AND key='%s' AND key_param_type='%s' """%(key, keyParamType)
    else:
        sql += """ AND key='%s' """%key
    
    return sql

def GET_TARGET_GROUP_FOR_KEY(targetSeq, groupSeq):
    return """
    SELECT targettype, groupname FROM tb_mongroupcatalog gc
        LEFT OUTER JOIN tb_montargetcatalog tc ON tc.montargetcatseq=gc.montargetseq
    WHERE gc.montargetseq=%s AND gc.mongroupcatseq=%s
    """%(str(targetSeq), str(groupSeq))

def GET_PLUGIN_BY_TARGET( target_seq ):
    return """
    SELECT pc.monplugincatseq, pc.script, pc.type, ic.mongroupcatseq
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=%s AND ic.delete_dttm is null 
        AND (ic.monplugincatseq=pc.monplugincatseq OR dc.monplugincatseq=pc.monplugincatseq)
        AND pc.type!='builtin' AND pc.script is not null AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    GROUP BY pc.monplugincatseq, pc.script, pc.type, ic.mongroupcatseq
    """%( str(target_seq) )

def GET_PLUGIN_LIB_BY_TARGET( target_seq ):
    return """
    SELECT pc.monplugincatseq, pc.libtype, pc.libscript, pc.libpath, pc.libname
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=%s AND ic.delete_dttm is null
        AND (ic.monplugincatseq=pc.monplugincatseq OR dc.monplugincatseq=pc.monplugincatseq)
        AND pc.libtype!='builtin' AND pc.libscript is not null AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    GROUP BY pc.monplugincatseq, pc.libtype, pc.libscript, pc.libpath, pc.libname
    """%( str(target_seq) )


def GET_PLUGIN_CFG_BY_TARGET( target_seq ):
    return """
    SELECT pc.monplugincatseq, pc.cfgname, pc.cfgpath, pc.cfg_input
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=%s AND ic.delete_dttm is null
        AND (ic.monplugincatseq=pc.monplugincatseq OR dc.monplugincatseq=pc.monplugincatseq)
        AND pc.cfgname is not null AND pc.cfg_input is not null AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    GROUP BY pc.monplugincatseq, pc.cfgname, pc.cfgpath, pc.cfg_input
    """%str(target_seq)

def GET_PLUGIN_BUILTIN( name, script, desc=None ):
    sql = """
    SELECT monplugincatseq FROM tb_monplugincatalog
    WHERE type='builtin' AND name='%s' AND script='%s' AND delete_dttm is null 
    """%( name, script )
    if desc != None :
        sql += """ AND description=%s"""%str(desc)
    return sql

def GET_PLUGIN_NOBUILTIN( script, targetSeq, groupSeq=None, pluginParam=None ):
    sql = """
    SELECT monplugincatseq FROM tb_monplugincatalog
    WHERE type!='builtin' AND script='%s' AND montargetcatseq=%s AND delete_dttm is null 
    """%( script, str(targetSeq) )
    if groupSeq != None:
        sql += """ AND mongroupcatseq=%s """%str(groupSeq)
    if pluginParam != None:
        sql += """ AND plugin_params='%s' """%str(pluginParam)
    return sql

def GET_PLUGIN_DISCOVERY_BY_TARGET( targetSeq, discoveryCfg ):
    return """
    SELECT pc.* 
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=%s AND ic.delete_dttm is null AND pc.monplugincatseq=dc.monplugincatseq
        AND pc.discovery_cfg_input='%s' AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    """%( str(targetSeq), discoveryCfg )

def GET_PLUGIN_CFGINPUT( targetSeq, cfgName, cfgPath ):
    return """
    SELECT pc.cfg_input
    FROM tb_monplugincatalog pc
    WHERE pc.montargetcatseq=%s AND pc.cfgname='%s' AND pc.cfgpath='%s' 
        AND pc.delete_dttm is null AND pc.cfg_input is not null
    GROUP BY pc.cfg_input
    """%( str(targetSeq), cfgName, cfgPath )

def GET_ZBCFG_NAME( targetSeq ):
    return """
    SELECT %s||'-'|| regexp_replace(targetcode, ' ', '_', 'g')||'-'||regexp_replace(targettype, ' ', '_', 'g')||
        '-'||regexp_replace(targetversion, ' ', '_', 'g') ||'.conf' as cfgname
    FROM tb_montargetcatalog tc
    WHERE montargetcatseq=%s
    """%( str(targetSeq), str(targetSeq) )

def GET_ZBCFG_INFO( svrSeq, targetSeq ):
    return """
    SELECT ic.monitemcatseq || '.i.' || regexp_replace(regexp_replace(ic.monitoritem, ' ', '-', 'g'), '/', '', 'g') as log_name, 
        regexp_replace(kc.key, '%s', '*') as key, pi.pluginpath as p_path,
        pc.plugin_params as param, pc.parameter_num as p_num, pi.monplugininstanceseq as pi_seq
    FROM tb_monplugininstance pi
        LEFT OUTER JOIN tb_monplugincatalog pc ON pc.monplugincatseq=pi.monplugincatseq
        LEFT OUTER JOIN tb_monitemcatalog ic ON pi.monplugincatseq=ic.monplugincatseq
        LEFT OUTER JOIN tb_zbkeycatalog kc ON ic.monitemcatseq=kc.monitemcatseq
    WHERE pi.serverseq=%s AND pi.montargetcatseq=%s AND pi.delete_dttm is null AND pi.monplugincatseq is not null
        AND kc.key is not null
    
    UNION
    
    SELECT dc.zbdiscoverycatseq || '.d.' || regexp_replace(regexp_replace(dc.name, ' ', '-', 'g'), '/', '', 'g') as log_name, 
        regexp_replace(dc.zbkey, '%s', '*') as key, pi.pluginpath as p_path,
        pc.plugin_params as param, pc.parameter_num as p_num, pi.monplugininstanceseq as pi_seq
    FROM tb_monplugininstance pi
        LEFT OUTER JOIN tb_monplugincatalog pc ON pc.monplugincatseq=pi.monplugincatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON pi.monplugincatseq=dc.monplugincatseq
    WHERE pi.serverseq=%s AND pi.montargetcatseq=%s AND pi.delete_dttm is null AND pi.monplugincatseq is not null 
        AND dc.zbkey is not null
    """%( '%s', str(svrSeq), str(targetSeq), '%s', str(svrSeq), str(targetSeq) )

def GET_ZBA_CFG_LIST( svrSeq ):
    return """
    SELECT cfgname FROM tb_zbaconfiginstance WHERE serverseq=%s GROUP BY cfgname
    """%str( svrSeq )

def GET_TARGET_CNT_BY_SERVER( svr_seq, targetSeq ):
    return """
    SELECT count(moniteminstanceseq) as c, tc.targetname as target_name
    FROM tb_moniteminstance ii, tb_montargetcatalog tc
    WHERE ii.delete_dttm is null AND ii.serverseq=%s 
        AND ii.montargetcatseq=tc.montargetcatseq AND tc.montargetcatseq=%s
    GROUP BY tc.targetname
    """%( str(svr_seq), str(targetSeq) )

def GET_TARGET_BY_SVR( svrSeq ):
    return """
    SELECT montargetcatseq as target_seq FROM tb_moniteminstance 
    WHERE delete_dttm is null AND serverseq='%s' GROUP BY montargetcatseq
    """%str(svrSeq)

def GET_TARGET_BY_SVR_WITHOUT_OS ( svrSeq ):
    return """
    SELECT tc.montargetcatseq target_seq from tb_montargetcatalog tc, 
        ( SELECT montargetcatseq FROM tb_moniteminstance 
        WHERE delete_dttm is null AND serverseq='%s' GROUP BY montargetcatseq ) ii
    WHERE tc.montargetcatseq = ii.montargetcatseq     
    AND tc.targetcode <> 'os'
    """%str(svrSeq)


def GET_PLUGIN_INST( svrSeq, target_list=None ):
    selSql = """ SELECT pluginpath as del_file FROM tb_monplugininstance
        WHERE delete_dttm is null AND pluginpath is not Null AND serverseq=%s """%str(svrSeq)
    
    if target_list != None :
        selSql += ( """ AND montargetcatseq in %s """%( target_list ) )
    
    selSql += ( """ GROUP BY pluginpath""" )
    return selSql

def GET_PLUGIN_INST_LIB( svrSeq, target_list=None ):
    selSql = """ SELECT libpath as del_file FROM tb_monplugininstance 
        WHERE delete_dttm is null AND libpath is not Null AND serverseq=%s """%str( svrSeq )
    
    if target_list != None :
        selSql += ( """ AND montargetcatseq in %s """%( target_list ) )
    
    selSql += ( """ GROUP BY libpath """ )
    return selSql

def GET_PLUGIN_INST_CFG( svrSeq, target_list=None ):
    selSql = """ SELECT cfgpath as del_file FROM tb_monplugininstance
        WHERE delete_dttm is null AND cfgpath is not Null AND serverseq=%s """%str( svrSeq )
    
    if target_list != None :
        selSql += ( """ AND montargetcatseq in %s """%( target_list ) )
    
    selSql += ( """ GROUP BY cfgpath """ )
    return selSql

def GET_ZBACONFIG_CFG( svrSeq, target_list=None ):
    selSql = """ SELECT cfgname as del_file FROM tb_zbaconfiginstance
        WHERE cfgname is not null AND serverseq=%s """%str( svrSeq )
    
    if target_list != None :
        selSql += ( """ AND montargetcatseq in %s """%( target_list ) )
    
    selSql += ( """ GROUP BY cfgname """ )
    return selSql

def GET_VENDOR_FOR_CREATE( vendorCode ):
    return """
    SELECT vendorcode FROM tb_vendor WHERE vendorcode='%s'
    """%vendorCode

def GET_VDUD_FOR_CREATE( vdudSeq ):
    return """
    SELECT vdudseq FROM tb_vdud WHERE vdudseq=%s
    """%str( vdudSeq )

def GET_TARGET_FOR_CREATE( targetCode, targetType, vendorCode, targetModel, 
                           targetVer=None, vdudSeq=None, targetFor=None ):
    sql = """
    SELECT tc.montargetcatseq FROM tb_montargetcatalog tc
    LEFT JOIN tb_montargetvdud tv ON tc.montargetcatseq=tv.montargetcatseq
    WHERE 
        tc.targetcode='%s' AND tc.targettype='%s' AND tc.vendorcode='%s' AND tc.targetmodel='%s' 
        AND tc.delete_dttm is null
    """%( targetCode, targetType, vendorCode, targetModel )
    if targetVer != None :
        sql += ( """ AND tc.targetversion='%s'"""%str(targetVer) )
    if vdudSeq != None :
        sql += ( """ AND tv.vdudseq=%s"""%str(vdudSeq) )
    if targetFor != None :
        sql += ( """ AND lower(tc.targetfor)='%s'"""%str(targetFor).lower() )
    
    sql += """ ORDER BY tc.creation_dttm desc """
    
    return sql

def GET_TARGET_BY_TARGETINFO( svrSeq, targetCode, targetType, vendorCode, targetModel, 
                           targetVer=None, vdudSeq=None, targetFor=None ):
    sql = """
    SELECT ii.montargetcatseq
    FROM tb_montargetcatalog tc, tb_moniteminstance ii """
    
    if vdudSeq != None :
        sql += ("""LEFT OUTER JOIN tb_montargetvdud tv ON tv.montargetcatseq = ii.montargetcatseq AND tv.serverseq=ii.serverseq """)

    sql += ( """WHERE tc.targetcode='%s' AND tc.targettype='%s' AND tc.vendorcode='%s' AND tc.targetmodel='%s' 
        AND ii.serverseq=%s AND ii.montargetcatseq=tc.montargetcatseq AND ii.delete_dttm is null
    """%( targetCode, targetType, vendorCode, targetModel, str(svrSeq) ))
    if vdudSeq != None:
        sql +=  ' AND tc.montargetcatseq=tv.montargetcatseq '
    if targetVer != None :
        sql += ( """ AND tc.targetversion='%s'"""%str(targetVer) )
    if vdudSeq != None :
        sql += ( """ AND tv.vdudseq=%s"""%str(vdudSeq) )
    if targetFor != None :
        sql += ( """ AND lower(tc.targetfor)='%s'"""%str(targetFor).lower() )
    
    sql += ' GROUP BY ii.montargetcatseq '
    
    return sql

def GET_TARGET_FOR_CHK_USED( targetSeq ):
    return """ SELECT moniteminstanceseq FROM tb_moniteminstance 
    WHERE montargetcatseq=%s AND delete_dttm is null """%str(targetSeq)

def GET_TARGET_INFO( targetSeq ) :
    return """ SELECT * FROM tb_montargetcatalog WHERE montargetcatseq=%s AND delete_dttm is null
    """%str(targetSeq)

def GET_GROUP_FOR_CREATE( targetSeq, grpName ):
    return """
    SELECT mongroupcatseq FROM tb_mongroupcatalog
    WHERE montargetseq=%s AND groupname='%s' AND delete_dttm is null
    """%(str(targetSeq), grpName)

def GET_GROUP_INFO( targetSeq ):
    return """ SELECT * FROM tb_mongroupcatalog WHERE montargetseq=%s AND delete_dttm is null
    """%str(targetSeq)

def GET_KEY_INST_BY_SVR_ITEM_FOR_MOD(svrSeq, itemSeq):
    return """
    SELECT onebox_id, CASE WHEN key_param_type is null THEN key 
        ELSE regexp_replace(key, '%s', key_param_type) END _key, zbkey, monitemkey as org_key
    FROM tb_zbkeycatalog kc, tb_server svr, tb_mapzbkeyinstance ki, tb_moniteminstance ii 
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ii.monitemcatseq 
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ii.serverseq=%s AND ii.moniteminstanceseq=%s AND ii.delete_dttm is null
        AND svr.serverseq=ii.serverseq AND kc.monitemcatseq=ii.monitemcatseq
        AND ki.moniteminstanceseq=ii.moniteminstanceseq
    """%( '%s', str(svrSeq), str(itemSeq) )

def GET_KEY_INST_BY_TEMP( svrSeq, targetList ):
    return """
    SELECT monitemkey
    FROM tb_moniteminstance ii, tb_mapzbkeyinstance ki
    WHERE ii.serverseq=%s AND ii.montargetcatseq in %s
        AND ii.delete_dttm is null AND ii.monitorobject is null
        AND ii.moniteminstanceseq=ki.moniteminstanceseq
    """%( str(svrSeq), targetList )

def GET_ITEM_INST( svrSeq, itemSeq, isSuspend=False ):
    sql =  """
    SELECT * FROM tb_moniteminstance WHERE serverseq=%s AND moniteminstanceseq=%s AND delete_dttm is null
    """%( str(svrSeq), str(itemSeq) )
    if isSuspend:
        sql += """ AND monitoryn='y' """
    
    return sql

def GET_ITEM_INST_NAME( itemSeq ):
    return """
    SELECT monitoritem FROM tb_moniteminstance WHERE moniteminstanceseq=%s
    """%str(itemSeq)

def GET_ITEM_INST_FOR_THRES( itemSeq ):
    return """
    SELECT onebox_id, serverseq,
        CASE WHEN kc_key is null THEN ki_key
        ELSE kc_key END as key, d_key, d_param
    FROM (
    SELECT hi.onebox_id onebox_id, hi.serverseq serverseq, thc.description description,
        regexp_replace(kc.key, '%s', kc.key_param_type) kc_key, ki.monitemkey ki_key, dc.zbkey d_key, kc.key_param_type d_param
    FROM tb_maphostinstance hi, tb_mapzbkeyinstance ki, tb_moniteminstance ii
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON ii.monitemcatseq=dm.monitemcatseq
        LEFT OUTER JOIN tb_zbkeycatalog kc ON kc.monitemcatseq=ii.monitemcatseq
        LEFT OUTER JOIN tb_monthresholdcatalog thc ON thc.monitemcatseq=ii.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dm.zbdiscoverycatseq=dc.zbdiscoverycatseq
    WHERE ii.moniteminstanceseq=%s AND ii.delete_dttm is null AND hi.serverseq=ii.serverseq 
        AND ki.moniteminstanceseq=ii.moniteminstanceseq
    ) as tmp
    GROUP BY onebox_id, serverseq, key, d_key, d_param
    """%( '%s', str(itemSeq) )

def GET_ITEM_INST_OBJLIST( itemSeq ):
    return """
    SELECT monitorobject FROM tb_moniteminstance ii, 
    (SELECT serverseq, monitemcatseq FROM tb_moniteminstance
        WHERE moniteminstanceseq=%s ) tmp
    WHERE tmp.serverseq=ii.serverseq AND tmp.monitemcatseq=ii.monitemcatseq
        AND ii.delete_dttm is null
    """%str(itemSeq)

def GET_ITEM_INST_BY_TARGETLIST( svr_seq, target_list ):
    return """
    SELECT ii.moniteminstanceseq, ii.monitemcatseq, ii.monitoritem
    FROM tb_moniteminstance ii
    WHERE ii.serverseq=%s AND ii.montargetcatseq in %s
        AND ii.delete_dttm is null AND ii.monitorobject is null
    """%( str(svr_seq), target_list )

def GET_ITEM_INST_FOR_ZBCHK(zbIP, zbProcName):
    return """
    SELECT ii.moniteminstanceseq as itemseq, svr.onebox_id as onebox_id, ki.monitemkey as key, thi.threshold_name || ' - ' || ii.monitorobject as t_name
    FROM tb_server svr, tb_moniteminstance ii, tb_mapzbkeyinstance ki, tb_monthresholdinstance thi
    WHERE svr.mgmtip='%s' AND ii.serverseq=svr.serverseq
        AND ii.monitortype='Service' AND ii.monitorobject='%s' AND ii.delete_dttm is null
        AND ii.moniteminstanceseq=ki.moniteminstanceseq
        AND thi.monitemcatseq=ii.monitemcatseq AND thi.serverseq=ii.serverseq
    """%(zbIP, zbProcName)

def GET_ITEM_INFO_FOR_EXTRACT( grpSeq ):
    return """
    SELECT ic.*, 
        km.type km_type, 
        pc.name pc_name, pc.type pc_type, pc.script pc_script, pc.parameter_num pc_parameter_num, 
            pc.plugin_params pc_plugin_params, pc.description pc_description, pc.libtype pc_libtype,
            pc.libscript pc_libscript, pc.libname pc_libname, pc.libpath pc_libpath, 
            pc.cfgname pc_cfgname, pc.cfgpath pc_cfgpath, pc.cfg_input pc_cfg_input,
        ag.name ag_name, ag.guide ag_guide
    FROM tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbkeycatalog kc ON ic.monitemcatseq=kc.monitemcatseq
        LEFT OUTER JOIN tb_zbkeymap km ON kc.key=km.key
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON ic.monitemcatseq=dm.monitemcatseq
        LEFT OUTER JOIN tb_monplugincatalog pc ON ic.monplugincatseq=pc.monplugincatseq
        LEFT OUTER JOIN tb_monalarmguide ag ON ic.monalarmguideseq=ag.monalarmguideseq
    WHERE ic.mongroupcatseq=%s AND ic.delete_dttm is null AND dm.zbdiscoverycatseq is null
    """%str(grpSeq)

def GET_D_ITEM_INST_BY_TARGETLIST( svr_seq, target_list ):
    return """
    SELECT ii.moniteminstanceseq, ii.monitemcatseq, ii.monitoritem
    FROM (
        SELECT ii.moniteminstanceseq, ii.monitemcatseq, ii.monitoritem,
            ROW_NUMBER() over (PARTITION BY ii.monitemcatseq ) rn
        FROM tb_moniteminstance ii
        WHERE ii.serverseq=%s AND ii.montargetcatseq in %s
            AND ii.delete_dttm is null AND ii.monitorobject is not null
    ) ii
    WHERE ii.rn=1
    """%( str(svr_seq), target_list )

def GET_CURR_ALARM_FOR_ADD_THRESHOLD( itemSeq, grade=None ):
    sql = """
    SELECT curalarmseq FROM tb_curalarm
    WHERE moniteminstanceseq=%s AND resolve_dttm is null 
    """%( str(itemSeq) )
    
    if grade != None :
        sql += ( """ AND faultgradecode='%s' """%str(grade).upper() )
    
    return sql

def GET_CURR_ALARM_FOR_REFRESH():
    return """
    SELECT curalarmseq, moniteminstanceseq, faultgradecode, monitorobject
    FROM (
        SELECT curalarmseq, moniteminstanceseq, faultgradecode, monitorobject FROM tb_curalarm
        WHERE resolve_dttm is null OR faultstagecode='조치' 
        UNION
        SELECT curalarmseq, moniteminstanceseq, faultgradecode, monitorobject FROM tb_histalarm
        WHERE resolve_dttm is null OR faultstagecode='조치'
    ) al
    GROUP BY curalarmseq, moniteminstanceseq, faultgradecode, monitorobject
    """

def GET_THRES_CAT( itemCatSeq ):
    return """
    SELECT thrc.threshold_name, thrc.fault_grade, thrc.repeat, thrc.condition, thrc.description,
        thrc.condition_type
    FROM tb_monthresholdcatalog thrc
    WHERE thrc.monitemcatseq=%s AND thrc.delete_dttm is null
    """%str(itemCatSeq)

def GET_THRES_INST( itemSeq ):
    return """
    SELECT thi.* FROM tb_monthresholdinstance thi, tb_moniteminstance ii
    WHERE ii.moniteminstanceseq=%s AND thi.delete_dttm is null
        AND ii.serverseq=thi.serverseq AND ii.monitemcatseq=thi.monitemcatseq
    """%( str(itemSeq) )

def GET_THRES_CAT_KEY( itemSeq, grade ):
    return """
    SELECT t_key
    FROM tb_moniteminstance ii, tb_monthresholdcatalog thc
    WHERE ii.moniteminstanceseq=%s AND ii.monitemcatseq=thc.monitemcatseq
        AND thc.fault_grade='%s' AND thc.delete_dttm is null AND thc.t_key is not null
    """%( str(itemSeq), grade )

def GET_ITEMINSTANCE_FOR_MOD_OBJ( svrSeq, itemCatSeq ):
    return """
    SELECT * FROM tb_moniteminstance
    WHERE serverseq=%s AND monitemcatseq=%s AND delete_dttm is null
    """%( str(svrSeq), str(itemCatSeq) )

# 2020. 4. 7 - lsh
# 기 설치된 원박스에 ping.sh  기능 추가.
def GET_ITEMCATSEQ( serverseq ):
    return """
    SELECT monitemcatseq, service_number
    FROM tb_monitemcatalog A,
        ( SELECT montargetcatseq, service_number FROM tb_moniteminstance
        WHERE delete_dttm is null 
        AND serverseq=%s GROUP BY montargetcatseq, service_number ) B
    WHERE A.montargetcatseq = b.montargetcatseq
    AND A.monitortype = 'ping'
    AND A.delete_dttm is null
    """% str(serverseq)

def INSERT_ITEM_INST( svrSeq, itemCatSeq, service_number ):
    return """
    INSERT INTO tb_moniteminstance(
        serverseq, monitemcatseq, monitorobject, period, unit, 
        monplugininstanceseq, data_type, value_type, 
        hist_save_month, stat_save_month, graphyn, displayyn, monitoryn, 
        creation_dttm, monitoritem, visiblename, monitortype, montargetcatseq, 
        mongroupcatseq, realtimeyn, monitor_method, service_number, statistics_yn)
    (
        SELECT pi.serverseq, ic.monitemcatseq, null, ic.period, ic.unit, 
            pi.monplugininstanceseq, ic.data_type, ic.value_type, 
            hist_save_month, stat_save_month, graphyn, 'y', 'y',
            now(), monitoritem, visiblename, monitortype, ic.montargetcatseq, 
            ic.mongroupcatseq, realtimeyn, ic.monitor_method, '%s',
            ic.statistics_yn
        FROM tb_monitemcatalog ic, tb_monplugininstance pi
        WHERE ic.monitemcatseq=%s AND ic.monplugincatseq=pi.monplugincatseq
            AND pi.serverseq=%s AND pi.delete_dttm is null
    )
    """%( service_number, str(itemCatSeq), str(svrSeq) )



def GET_PLUGIN_CFG_FOR_MOD_OBJ( svrSeq, itemCatSeq ):
    return """
    SELECT pc.discovery_cfg_input, svr.mgmtip, pi.cfgpath, pi.cfgdata
    FROM tb_server svr, tb_monplugininstance pi
        LEFT OUTER JOIN tb_monplugincatalog pc ON pc.monplugincatseq=pi.monplugincatseq,
        tb_zbdiscoverycatalog dc
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.zbdiscoverycatseq=dc.zbdiscoverycatseq
   WHERE dm.monitemcatseq=%s AND dc.monplugincatseq=pi.monplugincatseq
        AND pi.serverseq=%s AND pi.delete_dttm is null AND pi.serverseq=svr.serverseq
    """%( str(itemCatSeq), str(svrSeq) )

def GET_PLUGIN_INST_CFG_BY_TARGET( svrSeq, targetSeq ):
    return """
    SELECT pi.cfgpath, pi.cfgdata
    FROM tb_moniteminstance ii 
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON ii.monitemcatseq=dm.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dm.zbdiscoverycatseq=dc.zbdiscoverycatseq, 
        tb_monplugininstance pi
    WHERE ii.serverseq=%s AND ii.montargetcatseq=%s AND ii.delete_dttm is null
        AND ((ii.monplugininstanceseq=pi.monplugininstanceseq) OR
            (dc.monplugincatseq=pi.monplugincatseq AND pi.serverseq=%s))
        AND pi.cfgpath is not null AND pi.delete_dttm is null
    GROUP BY pi.cfgpath, pi.cfgdata
    """%( str(svrSeq), str(targetSeq), str(svrSeq) )

def GET_REQSTATUS( src, tid ):
    return """
    SELECT * FROM tb_monrequest WHERE src='%s' AND tid='%s'
    """%( src, tid )

# def GET_PLUGIN_INST_FOR_ADD_EXTRA(svrSeq, targetSeq, pluginScript, pluginParamNone=None ):
#     param = (lambda x: '' if x == None else x)(pluginParamNone)
#     return """
#     SELECT monplugininstanceseq FROM tb_monplugininstance 
#     WHERE serverseq=%s AND montargetcatseq=%s AND script='%s' AND plugin_params='%s'
#     """%( str(svrSeq), str(targetSeq), pluginScript, param )

def GET_TARGET_SEQ_BY_VDUD( vdudType, vdudVendor, vdudVer, isTest=False ):
    sql = """ SELECT * FROM tb_montargetcatalog 
    WHERE targettype='%s' AND vendorcode='%s' AND vdudversion='%s' AND delete_dttm is null 
    """%( vdudType, vdudVendor, vdudVer )
    
    if isTest :
        sql += """ AND lower(targetmodel) = 'test' """
    else:
        sql += """ AND lower(targetmodel) != 'test' """
    
    sql += """ ORDER BY montargetcatseq desc """
    return sql

def GET_PLUGIN_PATH( targetSeq ):
    return """
    SELECT montargetcatseq||'-'||targettype||
        (CASE WHEN targetfor is not null THEN '-'||targetfor ELSE '' END) as path
    FROM tb_montargetcatalog
    WHERE montargetcatseq=%s
    """%str(targetSeq)

def GET_DISCOVERY_INPUT_BY_TARGET(targetSeq):
    return """
    SELECT discovery_cfg_input FROM tb_monplugincatalog
    WHERE montargetcatseq=%s AND delete_dttm is null AND discovery_cfg_input is not null
    GROUP BY discovery_cfg_input
    """%str(targetSeq)

def GET_DISC_KEY( target_list ):
    return """
    SELECT dc.zbkey
    FROM tb_zbdiscoverycatalog dc
    WHERE dc.montargetcatseq in %s AND dc.delete_dttm is null
    """%(target_list)

def GET_DISC_INFO_FOR_EXTRACT( grpSeq ):
    return """
    SELECT dc.*, km.type km_type, 
        pc.name pc_name, pc.type pc_type, pc.script pc_script, pc.parameter_num pc_parameter_num, 
        pc.plugin_params pc_plugin_params, pc.description pc_description, pc.libtype pc_libtype,
        pc.libscript pc_libscript, pc.libname pc_libname, pc.libpath pc_libpath, 
        pc.cfgname pc_cfgname, pc.cfgpath pc_cfgpath, pc.cfg_input pc_cfg_input,
        pc.discovery_cfg_input pc_discovery_cfg_input
    FROM tb_zbdiscoverycatalog dc
        LEFT OUTER JOIN tb_monplugincatalog pc ON dc.monplugincatseq=pc.monplugincatseq
        LEFT OUTER JOIN tb_zbkeymap km ON dc.zbkey=km.key
    WHERE dc.mongroupcatseq=%s AND dc.delete_dttm is null
    """%str(grpSeq)

def GET_D_ITEM_INFO_FOR_EXTRACT( dSeq ):
    return """
    SELECT ic.*, 
        km.type km_type, 
        pc.name pc_name, pc.type pc_type, pc.script pc_script, pc.parameter_num pc_parameter_num, 
            pc.plugin_params pc_plugin_params, pc.description pc_description, pc.libtype pc_libtype,
            pc.libscript pc_libscript, pc.libname pc_libname, pc.libpath pc_libpath, 
            pc.cfgname pc_cfgname, pc.cfgpath pc_cfgpath, pc.cfg_input pc_cfg_input,
        ag.name ag_name, ag.guide ag_guide
    FROM tb_zbdiscoverymap dm, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbkeycatalog kc ON ic.monitemcatseq=kc.monitemcatseq
        LEFT OUTER JOIN tb_zbkeymap km ON kc.key=km.key
        LEFT OUTER JOIN tb_monplugincatalog pc ON ic.monplugincatseq=pc.monplugincatseq
        LEFT OUTER JOIN tb_monalarmguide ag ON ic.monalarmguideseq=ag.monalarmguideseq
    WHERE dm.zbdiscoverycatseq=%s AND dm.monitemcatseq=ic.monitemcatseq AND ic.delete_dttm is null
    """%str(dSeq)

def GET_ITEM_INST_SUSP_BY_TARGET( svrSeq, targetSeq ):
    return """
    SELECT moniteminstanceseq, suspend_yn FROM tb_moniteminstance
    WHERE serverseq=%s AND montargetcatseq=%s AND monitoryn='y' AND delete_dttm is null
    GROUP BY moniteminstanceseq, suspend_yn
    """%(str(svrSeq), str(targetSeq))

def GET_SVR_IP( svrSeq ):
    return """
    SELECT mgmtip, publicip, nfsubcategory, onebox_id FROM tb_server WHERE serverseq=%s
    """%str(svrSeq)

def GET_SVR_SEQ( onebox_id ):
    return """
    SELECT serverseq, mgmtip FROM tb_server WHERE onebox_id='%s'
    """% onebox_id


def GET_GROUP_FOR_ADDITEM( gSeq ):
    return """ SELECT groupname FROM tb_mongroupcatalog WHERE mongroupcatseq=%s """%str(gSeq)

def GET_ITEM_INFO_FOR_DELITEM( itemCatSeq ):
    return """
    SELECT ic.montargetcatseq, 
        CASE WHEN kc.key_param_type is null THEN kc.key ELSE regexp_replace(kc.key, '%s', kc.key_param_type) END AS key
    FROM tb_monitemcatalog ic, tb_zbkeycatalog kc
    WHERE ic.monitemcatseq=%s AND kc.monitemcatseq=ic.monitemcatseq AND kc.delete_dttm is null
    """%( '%s', str(itemCatSeq) )

def GET_ITEM_INST_FOR_DELITEM(itemCatSeq):
    return """
    SELECT ii.moniteminstanceseq FROM tb_moniteminstance ii
    WHERE ii.monitemcatseq=%s AND ii.delete_dttm is null
    """%(str(itemCatSeq))

def GET_GUIDE_FOR_DELITEM(itemSeq):
    return """
    SELECT monalarmguideseq FROM tb_monitemcatalog ic
    WHERE ic.monitemcatseq=%s
    GROUP BY monalarmguideseq
    """%str(itemSeq)

def GET_PLUGIN_FOR_DELITEM(itemSeq):
    return """ SELECT monplugincatseq FROM tb_monitemcatalog 
    WHERE monitemcatseq=%s AND monplugincatseq is not null AND delete_dttm is null 
    """%str(itemSeq)

def GET_ZB_KEY( zbType ):
    return """
    SELECT key FROM tb_zbkeymap WHERE type='%s' AND delete_dttm is null
    """%zbType

def INSERT_PLUGIN_DATA( pName, pType, targetSeq, groupSeq,
                        script=None, paramNum=None, description=None,
                        libType=None, libScript=None, libPath=None, libName=None, 
                        cfgPath=None, cfgName=None, cfgInput=None, 
                        pluginParam=None, discoveryCfg=None ):
    
    insertSql = """ INSERT INTO tb_monplugincatalog(name, type, montargetcatseq, mongroupcatseq, creation_dttm """
    valueSql = """ VALUES ( '%s', '%s', %s, %s, now() """%( pName, pType, str(targetSeq), str(groupSeq) )
    
    if script != None:
        insertSql += """ , script """
        valueSql += """ , '%s' """%(script)
    if paramNum != None :
        insertSql += """ , parameter_num """
        valueSql += """ , %s """%str(paramNum)
    if libType != None:
        insertSql += """ , libtype """
        valueSql += """ , '%s' """%(libType)
    if libScript != None:
        insertSql += """ , libscript """
        valueSql += """ , '%s' """%(libScript)
    if libPath != None:
        insertSql += """ , libpath """
        valueSql += """ , '%s' """%(libPath)
    if libName != None:
        insertSql += """ , libname """
        valueSql += """ , '%s' """%(libName)
    if description != None:
        insertSql += """ , description """
        valueSql += """ , '%s' """%(description)
    if cfgName != None:
        insertSql += """ , cfgname """
        valueSql += """ , '%s' """%(cfgName)
    if cfgPath != None:
        insertSql += """ , cfgpath """
        valueSql += """ , '%s' """%(cfgPath)
    if cfgInput != None:
        insertSql += """ , cfg_input """
        valueSql += """ , '%s' """%str(cfgInput)
    if pluginParam != None:
        insertSql += """ , plugin_params """
        valueSql += """ , '%s' """%str(pluginParam)
    if discoveryCfg != None:
        insertSql += """ , discovery_cfg_input """
        valueSql += """ , '%s' """%str(discoveryCfg)
    
    insertSql += """ ) """
    valueSql += """ ) """
    
    return insertSql + valueSql

def INSERT_PLUGIN_INST( svrSeq, pSeq, targetSeq, groupSeq, pluginPath ):
    return """
    INSERT INTO tb_monplugininstance(
                serverseq, monplugincatseq, pluginpath, montargetcatseq, mongroupcatseq, creation_dttm)
    VALUES ( %s, %s, '%s', %s, %s, now())
    """%( str(svrSeq), str(pSeq), pluginPath, str(targetSeq), str(groupSeq) )

def INSERT_ZBA_CFG( svrSeq, targetSeq, cfgName ):
    return """
    INSERT INTO tb_zbaconfiginstance(
                serverseq, monitemkey, monplugininstanceseq, 
                plugin_params, cfgname, montargetcatseq, mongroupcatseq)
    (
        SELECT pi.serverseq, regexp_replace(kc.key, '%s', '*'), pi.monplugininstanceseq, 
            pc.plugin_params, '%s', pi.montargetcatseq, pi.mongroupcatseq
        FROM tb_monitemcatalog ic, tb_zbkeycatalog kc, tb_monplugininstance pi
            LEFT OUTER JOIN tb_monplugincatalog pc ON pi.monplugincatseq=pc.monplugincatseq
        WHERE pi.monplugincatseq=ic.monplugincatseq AND ic.monitemcatseq=kc.monitemcatseq
            AND pi.serverseq=%s AND pi.montargetcatseq=%s AND pi.delete_dttm is null AND pc.type!='builtin'
        
        UNION
        
        SELECT pi.serverseq, regexp_replace(dc.zbkey, '%s', '*'), pi.monplugininstanceseq,
            pc.plugin_params, '%s', pi.montargetcatseq, pi.mongroupcatseq
        FROM tb_zbdiscoverycatalog dc, tb_monplugininstance pi
            LEFT OUTER JOIN tb_monplugincatalog pc ON pc.monplugincatseq=pi.monplugincatseq
        WHERE pi.monplugincatseq=dc.monplugincatseq
            AND pi.serverseq=%s AND pi.montargetcatseq=%s AND pi.delete_dttm is null AND pc.type!='builtin'
    )
    """%( '%s', cfgName, str(svrSeq), str(targetSeq), '%s', cfgName, str(svrSeq), str(targetSeq) )

def INSERT_SERVER( svr_seq, svr_uuid, svr_obid, svrIP, zba_port ):
    return """
    INSERT INTO tb_maphostinstance( serverseq, serveruuid, onebox_id, mgmtip, reg_dttm, zbaport) VALUES (%s, '%s', '%s', '%s', now(), %s)
    """%( str(svr_seq), svr_uuid, svr_obid, svrIP, str(zba_port) )


def INSERT_ITEMINSTANCE_NOINPUT( svr_seq, service_number, target_list ):
    if service_number == None: service_number = "null"
    else:
        service_number = "'" + service_number + "'"
    return """
    INSERT INTO tb_moniteminstance(
        serverseq, monitemcatseq, period, unit, 
        monplugininstanceseq, data_type, value_type, 
        hist_save_month, stat_save_month, graphyn, displayyn, monitoryn, suspend_yn,
        creation_dttm, monitoritem, visiblename, monitortype, montargetcatseq, 
        mongroupcatseq, realtimeyn, monitor_method, service_number, statistics_yn)
        (
        SELECT %s, ic.monitemcatseq, ic.period, ic.unit,
            pi.monplugininstanceseq, ic.data_type, ic.value_type, 
            hist_save_month, stat_save_month, graphyn, 'y', 'y', 'n',
            now(), ic.monitoritem, visiblename, monitortype, ic.montargetcatseq, 
            ic.mongroupcatseq, realtimeyn, ic.monitor_method, %s AS service_number,
            ic.statistics_yn
        FROM tb_monitemcatalog ic 
            LEFT OUTER JOIN tb_monplugininstance pi on ic.monplugincatseq=pi.monplugincatseq AND pi.serverseq=%s AND pi.delete_dttm is null
            LEFT OUTER JOIN tb_monitemstatistics as mis on mis.monitoritem = ic.monitoritem
        WHERE (ic.input_type='' or ic.input_type is null) AND ic.montargetcatseq in %s AND ic.delete_dttm is null
        )
    """%( str(svr_seq), service_number, str(svr_seq), str(target_list) )

def INSERT_ITEMINSTANCE_INPUT( svr_seq, itemObj, targetSeq, service_number, discCfg ):
    if service_number == None: service_number = "null"
    else:
        service_number = "'" + service_number + "'"
    return """
    INSERT INTO tb_moniteminstance(
        serverseq, monitemcatseq, monitorobject, period, unit, 
        monplugininstanceseq, data_type, value_type, 
        hist_save_month, stat_save_month, graphyn, displayyn, monitoryn, suspend_yn,
        creation_dttm, monitoritem, visiblename, monitortype, montargetcatseq, 
        mongroupcatseq, realtimeyn, monitor_method, service_number, statistics_yn)
    (
        SELECT pi.serverseq, ic.monitemcatseq, '%s', ic.period, ic.unit, 
            pi.monplugininstanceseq, ic.data_type, ic.value_type, 
            hist_save_month, stat_save_month, graphyn, 'y', 'y', 'n',
            now(), monitoritem, visiblename, monitortype, ic.montargetcatseq, 
            ic.mongroupcatseq, realtimeyn, ic.monitor_method, %s AS service_number,
            ic.statistics_yn
        FROM tb_monplugininstance pi,
        (
            SELECT ic.*
            FROM tb_monplugincatalog pc, tb_zbdiscoverycatalog dc
                LEFT OUTER JOIN tb_zbdiscoverymap dm ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
                LEFT OUTER JOIN tb_monitemcatalog ic ON dm.monitemcatseq=ic.monitemcatseq
            WHERE pc.discovery_cfg_input='%s' AND pc.delete_dttm is null AND pc.monplugincatseq=dc.monplugincatseq
                AND dc.montargetcatseq=%s AND dc.delete_dttm is null
        ) ic
        WHERE ic.delete_dttm is null AND ic.monplugincatseq=pi.monplugincatseq
            AND pi.delete_dttm is null AND pi.serverseq=%s
    )
    """%( itemObj, service_number, discCfg, str(targetSeq), str(svr_seq) )

def INSERT_KEYINSTANCE( svr_seq ):
    return """
    INSERT INTO tb_mapzbkeyinstance(serverseq, monitemkey, moniteminstanceseq)
        (
        SELECT %s, CASE WHEN ii.monitorobject='' or ii.monitorobject is null THEN key ELSE regexp_replace(key, '%s', ii.monitorobject) END _key, 
            moniteminstanceseq
        FROM tb_moniteminstance ii, tb_monitemcatalog ic, tb_zbkeycatalog kc
        WHERE ii.monitemcatseq=ic.monitemcatseq AND kc.monitemcatseq=ic.monitemcatseq
            AND ii.delete_dttm is null AND ii.serverseq=%s
        )
    """%( str(svr_seq), '%s', str(svr_seq) )

def INSERT_KEYINSTANCE_BY_TARGET( svr_seq, targetList ):
    return """
    INSERT INTO tb_mapzbkeyinstance(serverseq, monitemkey, moniteminstanceseq)
        (
        SELECT %s, CASE WHEN ii.monitorobject='' or ii.monitorobject is null THEN key ELSE regexp_replace(key, '%s', ii.monitorobject) END _key, 
            moniteminstanceseq
        FROM tb_moniteminstance ii, tb_monitemcatalog ic, tb_zbkeycatalog kc
        WHERE ii.monitemcatseq=ic.monitemcatseq AND kc.monitemcatseq=ic.monitemcatseq
            AND ii.delete_dttm is null AND ii.serverseq=%s AND ii.montargetcatseq in %s
        )
    """%( str(svr_seq), '%s', str(svr_seq), targetList )

def INSERT_TARGET( targetCode, targetType, vendorCode, targetModel, targetDesc, targetName, targetVName,
                   targetVer=None, targetFor=None ):
    insSql = """
    INSERT INTO tb_montargetcatalog(
        targetcode, targettype, vendorcode, targetmodel, description, creation_dttm, targetname, visiblename, targetversion 
    """
    valSql = """ VALUES ( '%s', '%s', '%s', '%s', '%s', now(), '%s', '%s', '%s' """%( targetCode, targetType, vendorCode, targetModel, targetDesc, targetName, targetVName, targetVer )
    
    if targetFor != None :
        insSql += ', targetfor '
        valSql += """, '%s' """%str(targetFor)
    
    return insSql + ')' +valSql + ')'

def INSERT_VDUDTARGET(montargetcatSeq, vdudSeq, vdudVer=None):
    return """
    INSERT INTO tb_montargetvdud(montargetcatseq, vdudseq, vdudversion)
    VALUES ('%s', '%s', '%s')
    """%( str(montargetcatSeq), str(vdudSeq), str(vdudVer) )

def INSERT_GROUP( targetSeq, grpName, grpVName, grpDesc ):
    return """
    INSERT INTO tb_mongroupcatalog( montargetseq, groupname, visiblename, description, creation_dttm)
        VALUES ( %s, '%s', '%s', '%s', now() )
    """%( str(targetSeq), grpName, grpVName, grpDesc )

# 2017.02.16  add statisticsYn
def INSERT_ITEM( targetSeq, groupSeq, iName, iVName, iType, period, pluginSeq, dataType, 
                 histSaveMon, statSaveMon, graphYN, realTimeYN, monMethod, desc, pluginType, 
                 valType=None, unit=None, inputType=None, guideSeq=None, statisticsYn=None, itemId=None):
    insSql = """
        INSERT INTO tb_monitemcatalog(
            montargetcatseq, mongroupcatseq, monitoritem, visiblename, monitortype, period, plugintype,
            data_type, hist_save_month, stat_save_month, graphyn, description, creation_dttm, realtimeyn, monitor_method, statistics_yn, item_id """
    valSql = """
        VALUES ( %s, %s, '%s', '%s', '%s', %s, '%s',
            '%s', %s, %s, '%s', '%s', now(), '%s', '%s', '%s', '%s'
    """%( str(targetSeq), str(groupSeq), iName, iVName, iType, str(period), pluginType,
          dataType, str(histSaveMon), str(statSaveMon), graphYN, desc, realTimeYN, monMethod, statisticsYn, itemId )
    
    if pluginSeq != None :
        insSql += ', monplugincatseq '
        valSql += """, %s """%pluginSeq
    
    if valType != None :
        insSql += ', value_type '
        valSql += """, '%s' """%valType
    
    if unit != None :
        insSql += ', unit '
        valSql += """, '%s' """%unit
    
    if inputType != None :
        insSql += ', input_type '
        valSql += """, '%s' """%inputType
    
    if guideSeq != None :
        insSql += ', monalarmguideseq '
        valSql += """, %s """%str(guideSeq)

    insSql += ')'
    valSql += ')'
    return insSql + valSql
    
def INSERT_GUIDE( name, guide ):
    return """
    INSERT INTO tb_monalarmguide(name, guide, creation_dttm)
    VALUES ('%s', '%s', now())
    """%( name, guide )

def INSERT_THRESHOLD( tName, itemSeq, tGrade, tCdtType, tCondition, tRepeat, tDesc, tKey=None ):
    insSql = """
    INSERT INTO tb_monthresholdcatalog(
        threshold_name, monitemcatseq, fault_grade, condition_type, condition, repeat, description, creation_dttm """
    valSql = """ VALUES ( '%s', %s, '%s', '%s', '%s', %s, '%s', now() 
    """%( tName, str(itemSeq), tGrade, tCdtType, tCondition, str(tRepeat), tDesc )
    
    if tKey != None :
        insSql += ', t_key '
        valSql += """ , '%s' """%str(tKey)
        
    insSql += ')'
    valSql += ')'
    
    return insSql + valSql

def INSERT_KEY( itemSeq, key, keyParams=None ):
    if keyParams != None :
        return """
        INSERT INTO tb_zbkeycatalog( monitemcatseq, key, key_param_type, creation_dttm )
        VALUES ( %s, '%s', '%s', now() )
        """%( str(itemSeq), key, str(keyParams) )
    else:
        return """
        INSERT INTO tb_zbkeycatalog( monitemcatseq, key, creation_dttm )
        VALUES ( %s, '%s', now() )
        """%( str(itemSeq), key )

def INSERT_DISCOVERY( targetSeq, groupSeq, dName, zbKey, dPeriod, _pluginSeq, returnField, histSaveDay, dDesc, monMethod, pluginType ) :
    pluginSeq = (lambda x: 'null' if x is None else x)(_pluginSeq)
    
    return """
    INSERT INTO tb_zbdiscoverycatalog(
        montargetcatseq, mongroupcatseq, name, zbkey, period, 
        monplugincatseq, return_field, description, creation_dttm, 
        hist_save_day, monitor_method, plugintype)
    VALUES (%s, %s, '%s', '%s', %s, 
        %s, '%s', '%s', now(), 
        %s, '%s', '%s')
    """%( str(targetSeq), str(groupSeq), dName, zbKey, str(dPeriod), pluginSeq, returnField, dDesc, str(histSaveDay), monMethod, pluginType )

def INSERT_DISCOVERY_MAP( discSeq, itemSeq ):
    return """INSERT INTO tb_zbdiscoverymap( zbdiscoverycatseq, monitemcatseq )
        VALUES (%s, %s)"""%( str(discSeq), str(itemSeq) )

def INSERT_THRES_INST( itemInstSeq, name, grade, conditions, cType, repeat, t_key, _desc=None ):
    desc = ( lambda x : """'%s'"""%x if x != None else 'null' )(_desc)
    
    insSql = """ INSERT INTO tb_monthresholdinstance( 
        serverseq, monitemcatseq, threshold_name, fault_grade, 
        condition, condition_type, repeat, creation_dttm, t_key, description ) """
    valSql = """ (
        SELECT ii.serverseq, ii.monitemcatseq, '%s', '%s', 
            '%s', '%s', %s, now(), '%s', %s
        FROM tb_moniteminstance ii
        WHERE ii.moniteminstanceseq=%s
    )
    """%( name, grade, conditions, cType, str(repeat), t_key, desc, str(itemInstSeq) )
    
    return insSql + valSql

def INSERT_EXTRA_ITEMINSTANCE_FOR_MOD_OBJ( svrSeq, itemCatSeq, obj ):
    return """
    INSERT INTO tb_moniteminstance(
        serverseq, monitemcatseq, monitorobject, period, unit, 
        monplugininstanceseq, data_type, value_type, 
        hist_save_month, stat_save_month, graphyn, displayyn, monitoryn, 
        creation_dttm, monitoritem, visiblename, monitortype, montargetcatseq, 
        mongroupcatseq, realtimeyn, monitor_method, statistics_yn)
    (
        SELECT pi.serverseq, ic.monitemcatseq, '%s', ic.period, ic.unit, 
            pi.monplugininstanceseq, ic.data_type, ic.value_type, 
            hist_save_month, stat_save_month, graphyn, 'y', 'y',
            now(), monitoritem, visiblename, monitortype, ic.montargetcatseq, 
            ic.mongroupcatseq, realtimeyn, ic.monitor_method,
            ic.statistics_yn
        FROM tb_monitemcatalog ic, tb_monplugininstance pi
        WHERE ic.monitemcatseq=%s AND ic.monplugincatseq=pi.monplugincatseq
            AND pi.serverseq=%s AND pi.delete_dttm is null
    )
    """%( str(obj), str(itemCatSeq), str(svrSeq) )

def INSERT_EXTRA_KEYINSTANCE_FOR_MOD_OBJ( itemSeq ):
    return """
    INSERT INTO tb_mapzbkeyinstance(serverseq, monitemkey, moniteminstanceseq)
    (
        SELECT ii.serverseq, regexp_replace(key, '%s', ii.monitorobject), ii.moniteminstanceseq
        FROM tb_moniteminstance ii, tb_zbkeycatalog kc
        WHERE ii.moniteminstanceseq=%s AND kc.monitemcatseq=ii.monitemcatseq
    )
    """%( '%s', str(itemSeq) )

def INSERT_REQ( src, tid, reqType, reqBody, status, state, progress ):
    return """
    INSERT INTO tb_monrequest
        ( src, tid, reqtype, reqbody, status, state, progress, req_dttm, state_dttm ) 
    VALUES ( '%s', '%s', '%s', '%s', '%s', '%s', %s, now(), now() )
    """%( src, str(tid), reqType, str(reqBody), status, state, str(progress) )

def INSERT_VIEW_INST_INIT( svrSeq ):
    return """
    INSERT INTO tb_monviewinstance( serverseq, viewseq, monitorobject )
    (SELECT %s, viewseq, defaultobject FROM tb_monviewcatalog vc ORDER BY viewseq)
    """%str(svrSeq)


# 2018. 5.10 - lsh, extra_wan 대응, 설변
def INSERT_VIEW_INST_LAN( svrSeq, lanname, ethname, targetcode ):
    return """
    INSERT INTO tb_monviewinstance( serverseq, viewseq, monitorobject )
    ( SELECT %s, viewseq, '%s' FROM tb_monviewcatalog WHERE lower(visiblename) = lower('%s')
      AND targetcode = '%s' )
    """% ( str(svrSeq), ethname, lanname, targetcode)

def UPDATE_ITEM_SELECT(param):
    return """
    UPDATE tb_moniteminstance SET statistics_yn = '%s'
    WHERE moniteminstanceseq = '%s'
    """%(param['statistics_yn'], param['moniteminstanceseq'])

def UPDATE_PLUGIN_INST_LIB( svrSeq, pSeq, libPath ):
    return """
    UPDATE tb_monplugininstance pi SET libpath='%s'
    WHERE serverseq=%s AND delete_dttm is null AND monplugincatseq=%s
    """%( libPath, str(svrSeq), str(pSeq) )

def UPDATE_PLUGIN_INST_CFG( svrSeq, pSeq, dstCfgPath, cfgData ):
    return """
    UPDATE tb_monplugininstance pi SET cfgpath='%s', cfgdata='%s'
    WHERE serverseq=%s AND delete_dttm is null AND monplugincatseq=%s
    """%( dstCfgPath, cfgData, str(svrSeq), str(pSeq) )

def UPDATE_PLUGIN_CFGINPUT( targetSeq, cfgName, cfgPath, cfgInputTotal ):
    return """
    UPDATE tb_monplugincatalog pc SET cfg_input='%s'
    WHERE pc.montargetcatseq=%s AND pc.cfgname='%s' AND pc.cfgpath='%s' AND pc.delete_dttm is null
    """%( cfgInputTotal, str(targetSeq), cfgName, cfgPath )

def UPDATE_ITEM_INST_ALL_FOR_MOD( svrSeq, itemSeq, _newPeriod=None, _newHistroy=None, _newStat=None ):
    updSql = """ UPDATE tb_moniteminstance ii SET """
    isFirst = True
    
    if _newPeriod != None :
        updSql += ( lambda x: '' if x else ', ' )(isFirst)
        updSql += ( """ period=%s """%str(_newPeriod) )
        isFirst = False
    
    if _newHistroy != None :
        updSql += ( lambda x: '' if x else ', ' )(isFirst)
        updSql += ( """ hist_save_month=%s """%str(_newHistroy) )
        isFirst = False
    
    if _newStat != None :
        updSql += ( lambda x: '' if x else ', ' )(isFirst)
        updSql += ( """ stat_save_month=%s """%str(_newStat) )
        isFirst = False
    
    updSql += """
    FROM ( SELECT monitemcatseq FROM tb_moniteminstance WHERE moniteminstanceseq=%s ) ii_cat
    WHERE ii.serverseq=%s AND ii.monitemcatseq=ii_cat.monitemcatseq AND ii.delete_dttm is null
    """%( str(itemSeq), str(svrSeq) )

    return updSql

def UPDATE_ITEM_INST_EACH_FOR_MOD( svrSeq, itemSeq, _newMonYN=None, _newRealTimeYN=None, _newSuspend=None ):
    updSql = """ UPDATE tb_moniteminstance ii SET """
    isFirst = True
    
    if _newMonYN != None :
        updSql += ( lambda x: '' if x else ', ' )(isFirst)
        updSql += ( """ monitoryn='%s' """%str(_newMonYN) )
        isFirst = False
    
    if _newRealTimeYN != None :
        updSql += ( lambda x: '' if x else ', ' )(isFirst)
        updSql += ( """ realtimeyn='%s' """%str(_newRealTimeYN) )
        isFirst = False
    
    if _newSuspend != None :
        updSql += ( lambda x: '' if x else ', ' )(isFirst)
        updSql += ( """ suspend_yn='%s' """%str(_newSuspend) )
        isFirst = False
    
    updSql += """
    WHERE ii.serverseq=%s AND ii.moniteminstanceseq=%s AND ii.delete_dttm is null
    """%( str(svrSeq), str(itemSeq) )

    return updSql

def UPDATE_ITEM_INST_NAME( svrSeq, itemSeq, itemNewName ):
    return """
    UPDATE tb_moniteminstance SET visiblename='%s'
    WHERE moniteminstanceseq=%s
    """%( itemNewName, str(itemSeq) )

def UPDATE_D_ITEM_INST_NAME( svrSeq, itemSeq, itemNewName ):
    return """
    UPDATE tb_moniteminstance SET visiblename='%s'
    WHERE serverseq=%s AND delete_dttm is null AND monitemcatseq=(
        SELECT monitemcatseq FROM tb_moniteminstance WHERE moniteminstanceseq=%s)
    """%( itemNewName, str(svrSeq), str(itemSeq) )

def UPDATE_THRES_INST( thrInstKey, conditions, cType, repeat ):
    return """
    UPDATE tb_monthresholdinstance SET condition='%s', condition_type='%s', repeat=%s 
    WHERE t_key='%s';
    """%( conditions, cType, str(repeat), thrInstKey )

def UPDATE_PLUGIN_INST_CFG_FOR_MOD( svrSeq, cfgPath, sendData ):
    return """
    UPDATE tb_monplugininstance SET cfgdata='%s'
    WHERE serverseq=%s AND cfgpath='%s' AND delete_dttm is null
    """%( sendData, str(svrSeq), cfgPath )

def UPDATE_REQ_STATUS(src, tid, status, state, progress):
    return """
    UPDATE tb_monrequest
    SET status='%s', state='%s', progress=%s, state_dttm=now()
    WHERE src='%s' AND tid='%s' AND result is null;
    """%( status, state, str(progress), src, tid )

def UPDATE_REQ_STATE(src, tid, state, progress):
    return """
    UPDATE tb_monrequest
    SET state='%s', progress=%s, state_dttm=now()
    WHERE src='%s' AND tid='%s' AND result is null;
    """%( state, str(progress), src, tid )

def UPDATE_REQ_PROG(src, tid, progress):
    return """
    UPDATE tb_monrequest
    SET progress=%s, state_dttm=now()
    WHERE src='%s' AND tid='%s' AND result is null;
    """%( str(progress), src, tid )

def UPDATE_REQ_COMPLETE(src, tid, result, status, state ):
    return """
    UPDATE tb_monrequest
    SET status='%s', state='%s', result='%s', progress=100, res_dttm=now()
    WHERE src='%s' AND tid='%s' AND result is null;
    """%( status, state, result, src, tid )

def UPDATE_REQ_FAIL(src, tid, result, error):
    return """
    UPDATE tb_monrequest
    SET result='%s', error='%s', res_dttm=now()
    WHERE src='%s' AND tid='%s' AND result is null;
    """%( result, error, src, tid )

def UPDATE_TARGET_VDUDSEQ( targetSeq, vdudSeq):
    return """
    UPDATE tb_montargetcatalog SET vdudseq=%s
    WHERE montargetcatseq=%s
    """%( str(vdudSeq), str(targetSeq) )

def UPDATE_VIEW_INST_OBJ( svrSeq, mapKey, param ):
    if param == None :
        return """
        UPDATE tb_monviewinstance vi SET monitorobject=null
        FROM tb_monviewcatalog vc
        WHERE vi.serverseq=%s AND vc.viewname like '%s' AND vc.viewseq=vi.viewseq
        """%(str(svrSeq), str(mapKey))
    else:
        return """
        UPDATE tb_monviewinstance vi SET monitorobject='%s'
        FROM tb_monviewcatalog vc
        WHERE vi.serverseq=%s AND vc.viewname like '%s' AND vc.viewseq=vi.viewseq
        """%(str(param), str(svrSeq), str(mapKey))

def INSERT_VIEW_INST_OBJ( svrSeq, mapKey, param ):
    return """
    INSERT INTO tb_monviewinstance(serverseq, viewseq, monitorobject)
    (
        SELECT distinct vi.serverseq, vc.viewseq, '%s' FROM tb_monviewinstance vi, tb_monviewcatalog vc
        WHERE vi.serverseq=%s AND vc.viewname like '%s' AND vc.viewseq=vi.viewseq
    )
    """%(str(param), str(svrSeq), str(mapKey))

def UPDATE_VIEW_INST_SEQ(svrSeq):
    return """
    UPDATE tb_monviewinstance vi SET moniteminstanceseq=vv.moniteminstanceseq
    FROM (
        SELECT ii.serverseq, ii.moniteminstanceseq, vm.monitorobject, vm.viewseq
        FROM (SELECT vi.serverseq, vi.viewseq, viewname, targetcode, targettype, groupname, monitortype, monitorobject 
            FROM tb_monviewinstance vi, tb_monviewcatalog vc
            WHERE vi.viewseq=vc.viewseq AND vi.serverseq=%s) vm, tb_moniteminstance ii
        LEFT OUTER JOIN tb_montargetcatalog tc ON ii.montargetcatseq=tc.montargetcatseq
        LEFT OUTER JOIN tb_mongroupcatalog gc ON ii.mongroupcatseq=gc.mongroupcatseq
        WHERE ii.delete_dttm is null AND ii.serverseq=vm.serverseq
            AND vm.groupname=gc.groupname AND vm.monitortype=ii.monitortype
            AND ( (vm.targettype is not null AND vm.targettype=tc.targettype) OR (vm.targettype is null AND vm.targetcode=tc.targetcode) )
            AND ( (vm.monitorobject is not null AND ii.monitorobject=vm.monitorobject ) OR (vm.monitorobject is null AND ii.monitorobject is null) )
        ORDER BY serverseq, vm.viewseq ) vv
    WHERE vi.serverseq=vv.serverseq AND vi.viewseq=vv.viewseq 
        AND ( (vi.monitorobject is not null AND vi.monitorobject=vv.monitorobject ) OR (vi.monitorobject is null AND vv.monitorobject is null) )
    """%str(svrSeq)

def DEL_ITEMINSTANCE( svr_seq, target_list=None ):
    updSql = """ UPDATE tb_moniteminstance SET delete_dttm=now() WHERE serverseq=%s AND delete_dttm is null """%str(svr_seq)
    if target_list != None :
        updSql += ( """ AND montargetcatseq in %s """%( target_list ) )
    return updSql

def DEL_ITEMINSTANCE_FOR_DEL_ITEMCAT( itemCatSeq ):
    return """
    UPDATE tb_moniteminstance SET delete_dttm=now()
    WHERE monitemcatseq=%s AND delete_dttm is null 
    """%str(itemCatSeq)

def DEL_PLUGININSTANCE( svr_seq, target_list ):
    updSql = """ UPDATE tb_monplugininstance pi SET delete_dttm=now() 
    WHERE pi.serverseq=%s AND pi.delete_dttm is null """%(svr_seq)
    
    if target_list != None :
        updSql += ( """ AND pi.montargetcatseq in %s """%target_list )
    
    return updSql

def DEL_TARGET( targetSeq ):
    return """
    UPDATE tb_montargetcatalog SET delete_dttm=now()
    WHERE montargetcatseq=%s AND delete_dttm is null"""%str(targetSeq)

def DEL_GROUP( targetSeq ):
    return """
    UPDATE tb_mongroupcatalog SET delete_dttm=now()
    WHERE montargetseq=%s AND delete_dttm is null"""%str(targetSeq)

def DEL_PLUGIN( targetSeq ):
    return """
    UPDATE tb_monplugincatalog SET delete_dttm=now()
    WHERE montargetcatseq=%s AND delete_dttm is null"""%str(targetSeq)

def DEL_ITEM( targetSeq ):
    return """
    UPDATE tb_monitemcatalog SET delete_dttm=now()
    WHERE montargetcatseq=%s AND delete_dttm is null"""%str(targetSeq)

def DEL_GUIDE( targetSeq ):
    return """
    UPDATE tb_monalarmguide ag SET delete_dttm=now() 
    FROM tb_monitemcatalog ic
    WHERE ic.montargetcatseq=%s AND ic.monalarmguideseq=ag.monalarmguideseq 
        AND ag.delete_dttm is null 
    """%str(targetSeq)

def DEL_THRESHOLD( targetSeq ):
    return """
    UPDATE tb_monthresholdcatalog thc SET delete_dttm=now()
    FROM tb_monitemcatalog ic
    WHERE thc.delete_dttm is null AND ic.montargetcatseq=%s AND thc.monitemcatseq=ic.monitemcatseq
    """%str(targetSeq)

def DEL_KEY( targetSeq ):
    return """
    UPDATE tb_zbkeycatalog kc SET delete_dttm=now() FROM tb_monitemcatalog ic
    WHERE kc.delete_dttm is null AND ic.montargetcatseq=%s AND kc.monitemcatseq=ic.monitemcatseq
    """%str(targetSeq)

def DEL_DISCOVERY( targetSeq ):
    return """
    UPDATE tb_zbdiscoverycatalog dc SET delete_dttm=now() 
    FROM tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
    WHERE dc.delete_dttm is null AND ic.montargetcatseq=%s AND dm.zbdiscoverycatseq=dc.zbdiscoverycatseq
    """%str(targetSeq)

def DEL_ITEMINSTANCE_FOR_MOD_OBJ( itemSeq ):
    return """
    UPDATE tb_moniteminstance SET delete_dttm=now() WHERE moniteminstanceseq=%s AND delete_dttm is null
    """%str(itemSeq)

def DEL_KEY_BY_ITEM(itemSeq):
    return """
    UPDATE tb_zbkeycatalog SET delete_dttm=now() WHERE monitemcatseq=%s AND delete_dttm is null
    """%str(itemSeq)

def DEL_THRESOLD_BY_ITEM(itemSeq):
    return """
    UPDATE tb_monthresholdcatalog SET delete_dttm=now() WHERE monitemcatseq=%s AND delete_dttm is null
    """%str(itemSeq)

def DEL_GUIDE_BY_SEQ(gSeq):
    return """
    UPDATE tb_monalarmguide SET delete_dttm=now() WHERE monalarmguideseq=%s AND delete_dttm is null
    """%str(gSeq)

def DEL_ITEM_BY_SEQ(itemSeq):
    return """
    UPDATE tb_monitemcatalog SET delete_dttm=now() WHERE monitemcatseq=%s AND delete_dttm is null
    """%str(itemSeq)

def DEL_PLUGIN_BY_SEQ(pSeq):
    return """
    UPDATE tb_monplugincatalog pc SET delete_dttm=now() 
    WHERE pc.monplugincatseq=%s AND pc.delete_dttm is null
    """%str(pSeq)

def DEL_VIEW_INST_SEQ(svr_seq):
    return """
    UPDATE tb_monviewinstance vi SET moniteminstanceseq=null FROM 
    (
    SELECT vi.serverseq, viewseq FROM tb_monviewinstance vi, tb_moniteminstance ii
    WHERE vi.serverseq=%s AND vi.moniteminstanceseq is not null AND 
        vi.moniteminstanceseq=ii.moniteminstanceseq AND ii.delete_dttm is not null
    UNION
    SELECT vi.serverseq, viewseq FROM tb_monviewinstance vi
    WHERE vi.serverseq=%s AND vi.moniteminstanceseq not in 
        (SELECT moniteminstanceseq FROM tb_moniteminstance WHERE serverseq=%s)
    ) dvi
    WHERE vi.serverseq=dvi.serverseq AND vi.viewseq=dvi.viewseq
    """%(str(svr_seq), str(svr_seq), str(svr_seq))

def REMOVE_KEYINSTANCE( svr_seq, target_list=None ):
    delSql = """ DELETE FROM tb_mapzbkeyinstance ki USING tb_moniteminstance ii 
    WHERE ki.serverseq=%s """%str(svr_seq)
    
    if target_list != None:
        delSql += ( """ AND ki.moniteminstanceseq=ii.moniteminstanceseq
                        AND ii.serverseq=%s AND ii.montargetcatseq in %s 
                    """%( str(svr_seq), target_list ) )
    
    return delSql

def REMOVE_KEYINSTANCE_FOR_DEL_ITEMCAT( itemCatSeq ):
    return """
    DELETE FROM tb_mapzbkeyinstance ki USING tb_moniteminstance ii 
    WHERE ii.monitemcatseq=%s AND ii.moniteminstanceseq=ki.moniteminstanceseq
    """%str(itemCatSeq)

def REMOVE_REALTIMEPERF( svr_seq, target_list=None ):
    delSql = """ DELETE FROM tb_realtimeperf rp USING tb_moniteminstance ii 
    WHERE rp.serverseq=%s """%str(svr_seq)
    
    if target_list != None :
        delSql += ( """ AND rp.moniteminstanceseq=ii.moniteminstanceseq
                        AND ii.serverseq=%s AND ii.montargetcatseq in %s
                    """%( str(svr_seq), target_list ) )
    
    return delSql

def REMOVE_MONVIEWINSTANCE_ITEM( iiseq ):
    return """
    DELETE FROM tb_monviewinstance 
    WHERE moniteminstanceseq=%s
    """%str(iiseq)

def REMOVE_REALTIMEPERF_FOR_DEL_ITEMCAT( itemCatSeq ):
    return """
    DELETE FROM tb_realtimeperf rp USING tb_moniteminstance ii 
    WHERE ii.monitemcatseq=%s AND ii.delete_dttm is null AND ii.moniteminstanceseq=rp.moniteminstanceseq
    """%str(itemCatSeq)

def REMOVE_REALTIMEPERF_ITEM( svrSeq, itemSeq ):
    return """
    DELETE FROM tb_realtimeperf WHERE serverseq=%s AND moniteminstanceseq=%s
    """%( str(svrSeq), str(itemSeq) )

def REMOVE_HOSTINSTANCE_BY_SERVER( svr_seq ):
    return """DELETE FROM tb_maphostinstance WHERE serverseq=%s"""%str(svr_seq)

def REMOVE_ZBACONFIGINSTANCE( svr_seq, target_list=None ):
    delSql = """ DELETE FROM tb_zbaconfiginstance zc WHERE zc.serverseq=%s """%str(svr_seq)
    
    if target_list != None :
        delSql += ( """ AND zc.montargetcatseq in %s """%( target_list ) )
    
    return delSql

def REMOVE_DISCOVERY_MAP( targetSeq ):
    return """
    DELETE FROM tb_zbdiscoverymap dm USING tb_monitemcatalog ic
    WHERE ic.montargetcatseq=%s AND dm.monitemcatseq=ic.monitemcatseq
    """%(str(targetSeq))

def REMOVE_THRES_INST( svrSeq, tKey ):
    return """
    DELETE FROM tb_monthresholdinstance WHERE serverseq=%s AND t_key='%s';
    """%( str(svrSeq), tKey )

def REMOVE_KEY_FOR_MOD_OBJ( itemSeq ):
    return """
    DELETE FROM tb_mapzbkeyinstance WHERE moniteminstanceseq=%s
    """%str(itemSeq)

def REMOVE_REALTIME_ITEM_UNUSED():
    return """
    DELETE FROM tb_realtimeperf rp USING tb_moniteminstance ii
    WHERE rp.moniteminstanceseq=ii.moniteminstanceseq AND ii.delete_dttm is not null
    """

def REMOVE_THRESHOLD_INST( svr_seq, target_list ):
    sql = """
    DELETE FROM tb_monthresholdinstance thri USING tb_monitemcatalog ic
    WHERE thri.serverseq=%s AND thri.monitemcatseq=ic.monitemcatseq 
    """%str(svr_seq)
    
    if target_list != None:
        sql += ( """ AND ic.montargetcatseq in %s """%target_list )

    return sql

def REMOVE_THRESHOLD_INST_FOR_DEL_ITEMCAT( itemCatSeq ):
    return """ DELETE FROM tb_monthresholdinstance WHERE monitemcatseq=%s """%str(itemCatSeq)

def REMOVE_WEB_MAPPING( svrSeq ):
    return """ DELETE FROM tb_monviewinstance WHERE serverseq=%s
    """%str(svrSeq)

def REMOVE_CURR_ALARM():
    return """ DELETE FROM tb_curalarm
    WHERE resolve_dttm is not null AND resolve_dttm < (now() - interval '24 hour')
    """

# 17.10.10 - lsh Daemon VPN 감시기능 추가로
# 디폴트 UTM Daemon 의 realtimeyn 이 'n' 이라
# VPN 이 n 로 들어가는 문제
# monview 에서 item seq 가 있는것만 일괄 'y' 로 update
def UPDATE_REALTIME_YN (svrSeq):
    return """ UPDATE tb_moniteminstance  SET realtimeyn = 'y'
    WHERE moniteminstanceseq IN ( SELECT moniteminstanceseq 
	    FROM tb_monviewinstance
	    WHERE serverseq = %s
	    AND moniteminstanceseq IS NOT NULL)
	""" % str(svrSeq)


# 17.10.12 - lsh
# OB 가 First_notify 이벤트를 보냈을때
# M 쪽 DB 를 체크하여 OB 쪽으로 Plugin 파일을 다시 전송
def GET_TARGET_CAT_SEQ (svrSeq):
    return """ SELECT montargetcatseq catseq
    FROM tb_monplugininstance
    WHERE serverseq = %s
    GROUP BY montargetcatseq
""" % str(svrSeq)


def GET_PLUGIN_INFO (svrSeq, targetseq):
    return """ SELECT pluginpath, script, type
    FROM tb_monplugininstance pi, tb_monplugincatalog pc
    WHERE serverseq = %s
    AND pi.monplugincatseq = pc.monplugincatseq
    AND pi.montargetcatseq = %s
    AND pi.delete_dttm is null
    GROUP BY pluginpath, script, type
""" % ( str(svrSeq) , str(targetseq) )


def GET_PLUGIN_LIB (svrSeq, targetseq):
    return """SELECT pi.libpath, libscript, libtype, pc.libname
    FROM tb_monplugininstance pi, tb_monplugincatalog pc
    WHERE serverseq = %s
    AND pi.monplugincatseq = pc.monplugincatseq
    AND pi.montargetcatseq = %s
    AND pi.libpath <> ''
    AND pi.delete_dttm is null
    GROUP BY pi.libpath, libscript, libtype, pc.libname
""" % ( str(svrSeq) , str(targetseq) )


def GET_PLUGIN_CFG (svrSeq):
    return """SELECT pc.cfgname, pi.cfgpath, pc.cfg_input, pi.cfgdata
    FROM tb_monplugininstance pi, tb_monplugincatalog pc, tb_mongroupcatalog gc
    WHERE serverseq = %s
    AND pi.monplugincatseq = pc.monplugincatseq
    AND pc.montargetcatseq = gc.montargetseq
    AND pi.delete_dttm is null
    AND pi.cfgpath <> ''
    GROUP BY  pc.cfgname, pi.cfgpath, pc.cfg_input, pi.cfgdata
""" % ( str(svrSeq) )

def GET_ZBCONFIG_INST_SEQ (svrSeq):
    return """ SELECT montargetcatseq catseq
    FROM tb_zbaconfiginstance
    WHERE serverseq = %s
    GROUP BY montargetcatseq
""" % str(svrSeq)

def GET_ZBCONFIG_INST_CFGNAME (svrSeq, targetseq):
    return """ SELECT cfgname
    FROM tb_zbaconfiginstance
    WHERE serverseq = %s
    AND montargetcatseq = %s
    GROUP BY cfgname
""" % ( str(svrSeq) , str(targetseq) )

def DEL_SMSSCHEDULE (svrSeq):
    return """ DELETE FROM tb_smsschedule WHERE serverseq = %s """ % str(svrSeq)


def GET_TARGET_NO (svrSeq, targetcode):
    return """ SELECT ii.montargetcatseq targetseq
    FROM tb_moniteminstance ii, tb_montargetcatalog tc
    WHERE ii.serverseq = %s
    AND ii.montargetcatseq = tc.montargetcatseq
    AND tc.targetcode = '%s'
    AND ii.delete_dttm is null
    GROUP BY ii.montargetcatseq """ % ( str(svrSeq), targetcode)


def GET_TARGETCATSEQ  (targetcode, targettype, vendorcode, targetmodel):
    return """ select montargetcatseq from tb_montargetcatalog
    where targetcode = '%s'
    and targettype = '%s'
    and vendorcode = '%s'
    and targetmodel = '%s' """ % ( targetcode, targettype, vendorcode, targetmodel)


def INSERT_ITEM_PING (serverseq):
    return """
    INSERT INTO tb_monplugininstance( serverseq, monplugincatseq, pluginpath, montargetcatseq, mongroupcatseq, creation_dttm) 
    ( SELECT serverseq, pc.monplugincatseq, replace(pi.pluginpath, '/net-status.sh', '/ping.sh')  pluginpath, pi.montargetcatseq, pi.mongroupcatseq, now()
        FROM tb_monplugininstance pi, tb_monplugincatalog pc
        where serverseq='%s'
        and pc.montargetcatseq = pi.montargetcatseq
        and pc.mongroupcatseq = pi.mongroupcatseq
        and pi.pluginpath like '%%/net-status.sh%%'
        and pc.name = 'ping'
        limit 1
    ) """ % serverseq 


def INSERT_ZBA_INST (serverseq, pluginseq):
    return """
    INSERT INTO tb_zbaconfiginstance( serverseq, monitemkey, monplugininstanceseq, 
        plugin_params, cfgname, montargetcatseq, mongroupcatseq)
    ( SELECT serverseq, replace(monitemkey, '.net.Status[*]', '.net.ping')  monitemkey, %s, '', cfgname, montargetcatseq, mongroupcatseq
    FROM tb_zbaconfiginstance
    WHERE serverseq = %s
    AND monitemkey like '%%.net.Status%%'
    ) """ % ( serverseq, pluginseq )


def GET_PING_ITEM (serverseq):
    return """
    SELECT *
    FROM tb_moniteminstance
    where serverseq='%s'
    and monitortype = 'ping'    
    """ % serverseq


def GET_NETWORK_TRAFFIC_TOP (customerseq, rank_mode, rank_count):

    if rank_mode.upper() == 'TOP' :
        rank = 'rank'
        condition = ' rank <= %s ' % rank_count
    else : 
        ## 역순일경우 1.2.3 표시 해주기 위해
        rank = 'total_count - rank + 1 as rank'
        condition = ' total_count -%s < rank ' % rank_count

    return """
    SELECT servername, serverseq, orgnamescode, rank, MAX(RX_KEY) rx_key, MAX(TX_KEY) tx_key
    FROM 
    (
        SELECT A.*,
            CASE WHEN POSITION ( 'Rx' in monitemkey ) > 0 THEN monitemkey END RX_KEY ,
            CASE WHEN POSITION ( 'Tx' in monitemkey ) > 0 THEN monitemkey END TX_KEY 
        FROM 
        (
            SELECT A.servername, A.serverseq, A.sum, A.orgnamescode, %s
            FROM 
            (
                SELECT svr.servername servername, 
                    svr.serverseq serverseq,
                    svr.orgnamescode,
                    sum(mtd.avg_int), ROW_NUMBER() OVER (order by sum(mtd.avg_int) DESC ) rank,
                    count(*) over () as total_count
                FROM tb_server svr, tb_server_wan wan, tb_moniteminstance mii, tb_monitemtrend_day mtd
                WHERE customerseq = %s
                AND svr.serverseq = wan.serverseq
                AND wan.name = 'R0'
                AND svr.serverseq = mii.serverseq
                AND mii.monitorobject = wan.nic
                AND mii.monitoritem in ( 'Network RX_Rate', 'Network TX_Rate')
                AND mii.moniteminstanceseq = mtd.moniteminstanceseq
                AND to_date(mtd.day, 'YYYY-MM-DD') > CURRENT_DATE -7
                GROUP BY svr.servername, svr.serverseq
            ) A
            WHERE 1=1
            AND %s
        ) A, tb_mapzbkeyinstance map, tb_server_wan wan, tb_moniteminstance mii
        WHERE A.serverseq = map.serverseq
        AND A.serverseq = mii.serverseq
        AND A.serverseq = wan.serverseq
        AND wan.name = 'R0'
        AND mii.monitorobject = wan.nic
        AND mii.monitoritem in ( 'Network RX_Rate', 'Network TX_Rate')
        AND mii.moniteminstanceseq = map.moniteminstanceseq
    ) A
    GROUP BY servername, serverseq, orgnamescode, rank
    ORDER BY rank
    """ % ( rank, customerseq, condition )


def GET_ZB_NETWORK_TRAFFIC_TOP (host, orgnamescode, rank, key1,  key2):

    yester_day = int(time.time()) - 86400

    return """
    SELECT host
        , '%s' as orgnamescode
        , '%s' as rank
        , TO_TIMESTAMP( clock/3600*3600 )::TIMESTAMP AS datetime
        , round(avg(rx)) AS rx
        , round(avg(tx)) AS tx
    FROM 
    (
        SELECT h.host
            ,his.clock
            ,CASE WHEN POSITION ( 'Rx' in i.key_ ) > 0 THEN his.value END RX 
            ,CASE WHEN POSITION ( 'Tx' in i.key_ ) > 0 THEN his.value END TX 
        FROM hosts h, items i, history_uint his
        WHERE h.host = '%s'
        AND h.hostid = i.hostid
        AND i.key_ IN ( '%s', '%s')
        AND i.itemid = his.itemid
        AND his.clock >= %s
    ) A
    GROUP BY host, orgnamescode, rank, datetime
    """ % ( orgnamescode, rank, host, key1, key2, yester_day)

def GET_ZB_ONEBOX_NETWORK_TRAFFIC_24HOUR (host):

    yester_day = int(time.time()) - 86400

    return """
    SELECT TO_TIMESTAMP( clock )::TIMESTAMP AS datetime
        , SUBSTRING(i.name, 9,2) AS ethmode
        , SUBSTRING(i.name, 19,5) AS ethname
        , t.value_avg AS value
    FROM hosts h, items i, trends_uint t
    WHERE h.host = '%s'
    AND h.hostid = i.hostid
    AND i.templateid IS Null 
    AND i.description IN ('Network RX Rate Monitor', 'Network TX Rate Monitor')
    AND i.itemid = t.itemid
    AND t.clock >= %s
    ORDER BY ethname, datetime, ethmode
    """ % ( host, yester_day )

## 추후 삭제
def GET_ZB_ONEBOX_NETWORK_TRAFFIC_24HOUR_OLD (host):
    return """
    SELECT TO_TIMESTAMP( clock/3600*3600 )::TIMESTAMP AS datetime
        , SUBSTRING(i.name, 9,2) AS ethmode
        , SUBSTRING(i.name, 19,5) AS ethname
        , ROUND(avg(value)) AS value
    FROM hosts h, items i, history_uint hu
    WHERE h.host = '%s'
    AND h.hostid = i.hostid
    AND i.templateid IS Null 
    AND i.description IN ('Network RX Rate Monitor', 'Network TX Rate Monitor')
    AND i.itemid = hu.itemid
    AND hu.clock >= EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day' )
    GROUP BY ethname, datetime, ethmode
    ORDER BY ethname, datetime, ethmode
    """ % host 

def IS_KT_VNF (svrseq):
    return """
    SELECT 'KT-VNF' as vnf_type 
    FROM tb_server svr, tb_nfr nfr
    WHERE svr.serverseq = %s
    AND svr.nsseq = nfr.nsseq
    AND nfr.name = 'KT-VNF'
    """ % ( svrseq )

def INSERT_PING_KEYINSTANCE( itemSeq ):
    return """
    INSERT INTO tb_mapzbkeyinstance(serverseq, monitemkey, moniteminstanceseq)
    (
        SELECT ii.serverseq, key, ii.moniteminstanceseq
        FROM tb_moniteminstance ii, tb_zbkeycatalog kc
        WHERE ii.moniteminstanceseq=%s AND kc.monitemcatseq=ii.monitemcatseq
    )
    """%( itemSeq )


def GET_ONEBOX_ID_IN_GROUP ( groupseq ) :
    substr = '' if groupseq == 'ALL' else "AND c.group_seq = %s" % groupseq
    return """
    SELECT svr.servername onebox_id, svr.orgnamescode, c.customername, grp.group_name
    FROM tb_server svr, tb_customer c
    LEFT OUTER JOIN tb_customer_group grp ON c.group_seq = grp.seq
    WHERE 1=1 
    %s
    AND svr.customerseq = c.customerseq
    """%( substr )


def GET_ZB_RTT_TOP (lst_servername, sDttm, eDttm, count) :
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    
    # 22.1.13  servername 이 1개일때 tuple 변환시 뒷자리 컴마로 오류발생
    # 개선
    str_serverlist = tuple(lst_servername) if len(lst_servername) > 1 else  "( '%s' )" % lst_servername[0]
    
    return """
    SELECT A.host onebox_id
    , ROUND(MAX(hist.value_max),2) as max
    , ROUND(AVG(hist.value_avg),2) as avg
    , ROUND(MIN(hist.value_MIN),2) as min
	, ROW_NUMBER() OVER (order by avg(hist.value_avg) DESC ) rank    
    FROM trends hist,
        ( SELECT h.host, i.itemid
        FROM hosts h, items i
        WHERE h.host IN %s
        AND i.name = 'SVR Ping'
        AND i.hostid = h.hostid ) A
    WHERE hist.clock BETWEEN %s AND %s
    AND   hist.itemid = A.itemid
    GROUP BY host
    ORDER BY avg DESC
    LIMIT %s
    """%( str_serverlist, stm_epoch, etm_epoch, count )

def GET_ZB_RTT_DATA_DETAIL(host_name, item_key, sDttm, eDttm):
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    sql = """
    SELECT clk, min_val, avg_val, max_val
    FROM (
            -- 기간 지정 상세.
            SELECT clock/600*600 as clk, round(max(value), 2) as max_val, round(avg(value), 2) as avg_val, round(min(value), 2) as min_val
            FROM history hist, items i, hosts h
            WHERE i.key_='%s' AND h.host='%s' AND i.hostid=h.hostid AND hist.itemid=i.itemid 
            AND hist.clock BETWEEN %s AND %s
            GROUP BY clk
    ) as stat
    ORDER BY clk 
    """ % (item_key, host_name, stm_epoch, etm_epoch)
    return sql

def GET_ZB_RTT_DATA_TRENDS(host_name, item_key, sDttm, eDttm):
    stm_epoch=int(time.mktime(time.strptime(sDttm, '%Y-%m-%d %H:%M:%S')))
    etm_epoch=int(time.mktime(time.strptime(eDttm, '%Y-%m-%d %H:%M:%S')))
    sql = """
    SELECT clk, min_val, avg_val, max_val
    FROM (
            SELECT clock as clk, round(value_max,2) as max_val, round(value_avg,2) as avg_val, round(value_min,2) as min_val
            FROM trends tr, items i, hosts h
            WHERE i.key_= '%s' 
            AND h.host='%s' 
            AND i.hostid=h.hostid 
            AND tr.itemid=i.itemid 
            AND tr.clock BETWEEN %s AND %s
    ) as stat
    ORDER BY clk             
    """ % (item_key, host_name, stm_epoch, etm_epoch)
    return sql

def GET_PING_ZBKEY (onebox_id) :
    sql = """
    SELECT monitemkey
    FROM tb_mapzbkeyinstance tm, tb_server svr
    WHERE svr.serverseq = tm.serverseq
    AND svr.onebox_id = '%s'
    AND monitemkey like '%%net.ping%%'
    """ % ( onebox_id )
    return sql

def GET_ITEM_KEY_ALL():
    return """
    SELECT DISTINCT ikey.monitemkey AS item_key, period
    FROM tb_mapzbkeyinstance ikey, 
    (
        SELECT moniteminstanceseq, period 
        FROM tb_moniteminstance mii, tb_server svr
        WHERE mii.serverseq=svr.serverseq
        AND mii.delete_dttm IS NULL
        AND mii.realtimeyn='y' 
        AND mii.monitoryn='y'  ) item
    WHERE item.moniteminstanceseq = ikey.moniteminstanceseq
    """
    
# 2022. 5.11 - lsh 
# SNMP HOST INFO    
def GET_SNMP_HOST_INFO( serverseq ):
    return """
    SELECT a.*, ob_service_number as service_number, serveruuid, svr.nfsubcategory AS zabbix_group, svr.onebox_flavor 
    FROM tb_server_snmp a, tb_server svr
    WHERE a.serverseq = svr.serverseq
    AND a.serverseq = '%s'
    """ % ( serverseq )
    
def GET_ONEBOX_ID( serverseq ):
    return """
    SELECT onebox_id FROM tb_server
    WHERE serverseq = '%s'
    """ % ( serverseq )
    
def GET_SNMP_HOST_STATUS():
    return """
    SELECT svr.nfsubcategory AS zabbix_group, snmp.* 
    FROM tb_server svr, tb_server_snmp snmp
    WHERE svr.serverseq = snmp.serverseq
    AND active_dttm is null
    """
def UPDATE_SNMP_HOST_STATUS(serverseq):
    return """
    UPDATE tb_server_snmp 
    SET active_dttm = now()
    WHERE serverseq = %s
    """ % ( serverseq )
    
def INSERT_VIEW_SNMP( svrSeq ):
    return """
    INSERT INTO tb_monviewinstance( serverseq, viewseq, monitorobject )
    (SELECT %s, viewseq, defaultobject FROM tb_monviewcatalog vc WHERE targetcode = 'snmp' ORDER BY viewseq)
    """%str(svrSeq)
    
def INSERT_VIEW_ICMP( svrSeq ):
    return """
    INSERT INTO tb_monviewinstance( serverseq, viewseq, monitorobject )
    (SELECT %s, viewseq, defaultobject FROM tb_monviewcatalog vc WHERE targetcode = 'icmp' ORDER BY viewseq)
    """%str(svrSeq)


def INSERT_ITEMINSTANCE_SNMP( svr_seq, service_number, target_list ):
    if service_number == None: service_number = "null"
    else:
        service_number = "'" + service_number + "'"
    return """
    INSERT INTO tb_moniteminstance(
        serverseq, monitemcatseq, period, unit, monitorobject,
        monplugininstanceseq, data_type, value_type, 
        hist_save_month, stat_save_month, graphyn, displayyn, monitoryn, suspend_yn,
        creation_dttm, monitoritem, visiblename, monitortype, montargetcatseq, 
        mongroupcatseq, realtimeyn, monitor_method, service_number, statistics_yn)
        (
        SELECT %s, ic.monitemcatseq, ic.period, ic.unit, ic.monitoritem,
            pi.monplugininstanceseq, ic.data_type, ic.value_type, 
            hist_save_month, stat_save_month, graphyn, 'y', 'y', 'n',
            now(), ic.monitoritem, visiblename, monitortype, ic.montargetcatseq, 
            ic.mongroupcatseq, realtimeyn, ic.monitor_method, %s AS service_number,
            ic.statistics_yn
        FROM tb_monitemcatalog ic 
            LEFT OUTER JOIN tb_monplugininstance pi on ic.monplugincatseq=pi.monplugincatseq AND pi.serverseq=%s AND pi.delete_dttm is null
            LEFT OUTER JOIN tb_monitemstatistics as mis on mis.monitoritem = ic.monitoritem
        WHERE (ic.input_type='' or ic.input_type is null) AND ic.montargetcatseq in %s AND ic.delete_dttm is null
        )
    """%( str(svr_seq), service_number, str(svr_seq), str(target_list) )


def UPDATE_OS_VERSION( serverseq, os_version ):
    return """
    UPDATE tb_onebox_sw 
    SET operating_system = '%s'
    where serverseq = %s
    """% ( os_version, serverseq )



def REMOVE_THRESHOLD_INST_SNMP( svr_seq):
    sql = """
    DELETE FROM tb_monthresholdinstance thri USING tb_monitemcatalog ic
    WHERE thri.serverseq=%s AND thri.monitemcatseq=ic.monitemcatseq 
    """%str(svr_seq)
    return sql


def REMOVE_KEYINSTANCE_SNMP ( svr_seq ):
    delSql = """ DELETE FROM tb_mapzbkeyinstance ki USING tb_moniteminstance ii 
    WHERE ki.serverseq=%s """%str(svr_seq)
    return delSql

def DEL_ITEMINSTANCE_SNMP( svr_seq ):
    updSql = """ UPDATE tb_moniteminstance SET delete_dttm=now() WHERE serverseq=%s AND delete_dttm is null """%str(svr_seq)
    return updSql

def REMOVE_REALTIMEPERF_SNMP( svr_seq):
    delSql = """ DELETE FROM tb_realtimeperf rp USING tb_moniteminstance ii 
    WHERE rp.serverseq=%s """%str(svr_seq)
    return delSql


def UPDATE_CURR_ALARM_FOR_DEL_SVR_SNMP( svr_obid, resolveDetail ):
    sql = """
    UPDATE tb_curalarm SET resolve_dttm=now(), resolve_methodcode='%s', faultstagecode='해제'
    WHERE onebox_id='%s' AND resolve_dttm is null
    """%( resolveDetail, svr_obid )    
    return sql


def GET_ONEBOX_TEMPLATE_MODEL():
    sql = """
        SELECT hw_model, template_type
        FROM tb_onebox_template_model
        """
    return sql