#-*- coding: utf-8 -*-
'''
Created on 2020. 6. 26.

@author: lsh
'''

def GET_LINE_INFO (db_type, BeforeTime):
    sql = """
    SELECT *
    FROM tb_onebox_line_detail 
    WHERE snmp_read <> ''
    AND del_yn = 'N' """

    if db_type == 'postgresql' :
        sql += """ AND modify_dttm > now() - interval'%s minute' """ % BeforeTime
    else : 
        sql += """ AND modify_dttm > DATE_FORMAT(DATE_ADD(now(),INTERVAL -%s MINUTE), '%s') """ % ( BeforeTime, "%Y-%m-%d %H:%i:%s")

    return sql


def GET_LINE_INFO_ALL ():
    return """
    SELECT *
    FROM tb_onebox_line_detail 
    WHERE snmp_read <> ''
    AND del_yn = 'N'
    """ 

def UPDATE_STATUS_N ():
    return """
    UPDATE tb_onebox_line_detail 
    SET status = 'N'
    WHERE snmp_read is null
    AND del_yn = 'N'    
    """ 


def GET_LINENUM_TO_SERVERNAME(line_number):
    return """
    SELECT svr.servername, svr.mgmtip 
    FROM tb_server svr, tb_onebox_line line
    WHERE svr.serverseq = line.serverseq
    AND line.line_number = '%s'
    """ % line_number