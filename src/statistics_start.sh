nohup python c_copyZbToOrchm.py > /dev/null 2>&1 &
# 통계 데이터 생성
nohup python c_generator.py > /dev/null 2>&1 &
# 오래된 데이터 삭제
#nohup python c_removeData.py > /dev/null 2>&1 &
