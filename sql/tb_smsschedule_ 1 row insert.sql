INSERT INTO tb_smsschedule(
            monday, tuesday, wednesday, thursday, friday, saturday, sunday, 
            allow_stm, allow_etm, deny_yn, deny_sdt, deny_edt)
    VALUES ('Y', 'Y', 'Y','Y', 'Y','Y', 'Y'
	,TO_TIMESTAMP('09:00:00', 'HH24:MI:SS')
	,TO_TIMESTAMP('18:00:00', 'HH24:MI:SS')
	,'Y'
	,  to_date('2016-01-19', 'YYYY-MM-DD')       
	,  to_date('2016-01-19', 'YYYY-MM-DD')       
	);
