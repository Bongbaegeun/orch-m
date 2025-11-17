P_NAME='orchm'

if [ "$1" == "" ]
then
	tail -fn 100 ./log/$P_NAME.log ./log/faultmsg.log ./log/apimsg.log
elif [ "$1" == "err" ] || [ "$1" == "ERR" ]
then
	tail -fn 200 ./log/$P_NAME.err
elif [ "$1" == "exc" ] || [ "$1" == "EXC" ]
then
	tail -fn 200 ./log/$P_NAME.exc
elif [ "$1" == "msg" ] || [ "$1" == "MSG" ]
then
	tail -fn 200 ./log/apimsg.log
elif [ "$1" == "fault" ] || [ "$1" == "fault" ]
then
	tail -fn 200 ./log/faultmsg.log
fi
	
