#-*- coding: utf-8 -*-
import urllib2
import json
import datetime

HEADER = { "content-Type": "application/json;charset=UTF-8", "accept":"application/json" }

# 상용
ALLINHOME_URL = 'http://10.220.175.123/api/lineInfo/ONEBOX/'

METHOD='POST'

def callAPI( line_info ):
    try :
        line_info.dttm = datetime.datetime.now()        

        url = ALLINHOME_URL + line_info.encrypt_line_num
        req = urllib2.Request(url, '', HEADER)

        response = urllib2.urlopen(req)
        retBody = json.loads(response.read())

        line_info.value = retBody['modem_status']
        line_info.ErrMessage = retBody['return_msg']
        
        #value, line_info.ErrMessage = fetch(handler)

    except Exception, e:
        print e
        line_info.value = '0'
        line_info.ErrMessage = str(e)

    return line_info