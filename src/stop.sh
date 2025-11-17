P_NAME='orchm.py'

PID=$(ps -ef | grep python | grep -v 'grep' | grep "$P_NAME" | awk '{print $2}')

kill -9 $PID
