1. zabbix 서버 설정 변경
취득불가 갱신 주기 변경: 관리->일반->기타-> 갱신간격 조정

2. template 생성 시
한글 가능 항목: target의 name, description, vendorcode
		group/discovery의 description, item/trigger의 name, description


3. SMS 서비스
LANG=ko_KR.eucKR
접속IP 확인:
	telnet 119.205.196.225 80
	telnet 119.205.196.240 80
	telnet 119.205.196.241 80
	telnet 119.205.196.242 80
	telnet 119.205.196.243 80
	telnet 119.205.196.244 80
	telnet 119.205.196.245 80
	telnet 119.205.196.211 80
	telnet 210.105.195.140 80
	telnet 210.105.195.151 80
	telnet 210.105.195.152 80
	telnet 210.105.195.153 80
	telnet 210.105.195.154 80
	telnet 210.105.195.155 80
	telnet 210.105.195.145 80
	telnet 210.105.195.146 80
	telnet 210.105.195.147 80
정보: test1onebox/onebox1112!, 2센터
	1000건/월, ~16년 9월 17일까지
mysql 설치: apt-get install mysql-server
	계정 생성:
		# mysql -u root -p
		> use mysql;
		-- 외부접속 설정
		> GRANT ALL PRIVILEGES ON *.* to 'root'@'%' IDENTIFIED BY '비밀번호';
		> create user '아이디'@'%' identified by '비밀번호';
		> create database DB명 default character set utf8;
		> grant all privileges on DB명.* to 아이디@'%';
		> flush privileges;
		-->nfv/nfv1234!, nfv_sms_db
	설정 수정:
		-------------------------
		1. bind-address = 127.0.0.1 주석 처리
		2. [mysqld]에 추가
		    character-set-server=utf8
		    collation-server=utf8_general_ci
		    init_connect = set collation_connection = utf8_general_ci
		    init_connect = set names utf8
		3. [mysql]에 추가
		    default-character-set=utf8
		4. [mysqld_safe]에 추가
		    default-character-set=utf8
		5. [client]에 추가
		    default-character-set=utf8
		6. [mysqldump]에 추가
			default-character-set=utf8
		----------------------------
	# /etc/init.d/mysql restart
	# pip install MySQL-python
agent 설치:
	인증서 복사 : McsAgent/file/auth 에 저장, test1onebox.cert
	설치 문서 참조
		log 저장 테이블 고려: 월단위로 신규 생성할지 고정해서 쓸지..
	설정: sms, mms 송신 서비스만 사용, 로그 fix테이블, 연동규격(1.신규), 한글(1)
SMS 발송: 정해진 회신번호로만 전송가능, 0428708729
	
	
	