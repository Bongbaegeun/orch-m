#-*- coding: utf-8 -*-
'''
Created on 2017. 4. 4.

@author: sut
'''
import logging
import pprint

import yaml

TITLE = 'orchm'
logger = logging.getLogger(TITLE)

# 개발시 로그표시 유무.
DEBUG_LOG_YN = 'n'



### common
# 한글 인코딩 처리
class myPrettyPrinter(pprint.PrettyPrinter):
	def format(self, _object, context, maxlevels, level):
		if isinstance(_object, unicode):
			return "'%s'" % _object.encode('utf8'), True, False
		elif isinstance(_object, str):
			_object = unicode(_object,'utf8')
			return "'%s'" % _object.encode('utf8'), True, False
		return pprint.PrettyPrinter.format(self, _object, context, maxlevels, level)


def dictValuesinList(dictinList, resultList=None, strKey=None, dictWhere=None):
    """
    - FUNC: list의 값중 dict형태의 value만 추출하여 list형태로 반환
    - INPUT
        dictinList: input list
        resultList: output list
        strKey: dict의 key
    - OUTPUT : list형태의 dict의 value
    """
    if resultList is None or type(resultList) != list:
        resultList = []

    if type(dictinList) is list:
        for dl in dictinList:
            if type(dl) is dict:
                if strKey is None:
                    for dlkey, dlvalue in dl.items():
                        if dictWhere is None:
                            resultList.append(dlvalue)
                        else:
                            if dictWhere in dl.values():
                                resultList.append(dlvalue)
                else:
                    if dictWhere is None:
                        resultList.append(dl[strKey])
                    else:
                        if dictWhere in dl.values():
                            resultList.append(dl[strKey])
            else:
                continue

    return resultList









### SMS





### ZB





### zba





### Perf





### Fault
## v2
def getGrade( grade ):
    """
    - FUNC: 장애 코드를 장애등급으로 변환(현재 사용하는 장애코드:2,3,4,5), 정의되지 않은 코드는 사용하지 않음
    - INPUT
        grade(M): 장애 코드
    - OUTPUT : 장애 등급
    """
    if grade == 0 :         return 'NORMAL'
    elif grade == 1:        return 'INFO'
    elif grade == 2:        return 'WARNING'
    elif grade == 3:        return 'MINOR'
    elif grade == 4:        return 'MAJOR'
    elif grade == 5:        return 'CRITICAL'
    else:                   return 'UNKNOWN'

def getGradeCode( grade ):
    """
    - FUNC: 장애 등급을 장애코드로 변환(현재 사용하는 장애등급:WARNING, MINOR, MAJOR, CRITICAL), 정의되지 않은 등급는 사용하지 않음
    - INPUT
        grade(M): 장애 등급
    - OUTPUT : 장애 코드
    """
    if str(grade).upper() == 'NORMAL' :  return 0
    elif str(grade).upper() == 'INFO':   return 1
    elif str(grade).upper() == 'WARNING':return 2
    elif str(grade).upper() == 'MINOR':  return 3
    elif str(grade).upper() == 'MAJOR':  return 4
    elif str(grade).upper() == 'CRITICAL':return 5
    else:                   return -1

def getState(state):
    """
    - FUNC: 장애 상태(발생/해제) 코드를 readable 한 코드로 변환
    - INPUT:
        state(M): 장애 상태 코드
    - OUTPUT : 장애 상태 Text
    """
    if state == 1:        return '발생'
    else:                 return '해제'

def getState_short(state):
    """
    - FUNC: 장애 상태(발생/해제) 코드를 readable 한 코드로 변환
    - INPUT
        state(M): 장애 상태 코드
    - OUTPUT : 장애 상태 Text
    """
    if state == 1:        return "발"
    else:                 return "해"

def getGrade_short( grade ):
    """
    - FUNC: 장애 코드를 장애등급으로 변환(현재 사용하는 장애코드:2,3,4,5), 정의되지 않은 코드는 사용하지 않음
    - INPUT
        grade(M): 장애 코드
    - OUTPUT : 장애 등급
    """
    if grade == 0 :         return 'N'
    elif grade == 1:        return 'I'
    elif grade == 2:        return 'W'
    elif grade == 3:        return 'm'
    elif grade == 4:        return 'M'
    elif grade == 5:        return 'C'
    else:                   return 'U'


### Perf





### Mon
def checkMapInfoNum(mapName, mapInfo={}):
    """
    - FUNC: 매핑 감시항목 이중화 체크
    - INPUT
        mapName(M): 확인할 맵정보
        mapInfo(M): 매핑정보
    - OUTPUT: 이중화 건수 결과
    """
    mapinfoNum = 0

    if mapName in mapInfo.keys() and type(mapInfo[mapName]) is list:
        mapinfoNum = len(mapInfo[mapName])
        if DEBUG_LOG_YN == 'y': logger.info('[checkMapInfoNum_1] ==========> %s : %s' % (mapName, str(mapInfo[mapName])))
    else:
        if mapName in mapInfo.keys()  :
            mapinfoNum = 1
        else :
            mapinfoNum = 0

    return mapinfoNum



# 직접 호출하는 테스트 코드
if __name__ == '__main__':
    print(getGrade(5))                      # CRITICAL
    print(getGradeCode('MAJOR'))            # 4
    print(getState(1))                      # 발생

    a = ['aaa', {'name': 'kim', 'phone': '01099993333', 'birth': '1118'}, 'str', {'name': 'lee', 'phone': '0107778888', 'birth': '7778'}]
    b = ['bbb']
    c = dictValuesinList(a, b, None)
    print(1, c)     # (1, ['bbb', '01099993333', 'kim', '1118', '0107778888', 'lee', '7778'])
    b = ['ccc']
    c = dictValuesinList(a, b, 'name')
    print(2, c)     # (2, ['ccc', 'kim', 'lee'])
    b = dictValuesinList(a, b, 'phone')
    print(3, b)     # (3, ['ccc', 'kim', 'lee', '01099993333', '0107778888'])
    d = [{'grade': 'critical', 'value_type': 'status'}, {'grade': 'major', 'value_type': 'status'}, {'grade': 'minor', 'value_type': 'status'}, {'grade': 'critical', 'value_type': 'perf'}, {'grade': 'major', 'value_type': 'perf'}]
    e = []
    f = dictValuesinList(d, e, 'grade', 'cc')
    print(4, f)     # (4, ['critical', 'major', 'minor'])
    g = dictValuesinList(d, None, 'grade', 'perf')
    print(5, g)     # (5, ['critical', 'major'])

    # print(INSERT_SMS_HIST(False, 123, 'sendStatus', 'error', 456))
    smsUserList = [{'smsuserseq': 1, 'phone_num': '01000001111', 'name': '\xec\x86\xa1\xec\x9d\x98\xed\x83\x9d'},
                   {'smsuserseq': 2, 'phone_num': '01012345678', 'name': '\xea\xb9\x80\xec\x8a\xb9\xec\xa3\xbc'}]
    # myPrettyPrinter().pprint(smsUserList)
    print myPrettyPrinter().pformat(smsUserList)

    print(__name__)                         # __main__



