SELECT tbs.category
, tbs.categoryseq
, tbs.mon
, tbs.tue
, tbs.wed
, tbs.thur
, tbs.fri
, tbs.sat
, tbs.sun
, tbs.dayhh
, tbs.daymm
, tbs.monthday
, tbs.monthhh
, tbs.monthmm
, tbs.dayuse_yn
, tbs.monthuse_yn
, tbs.reg_id    

, to_char((SELECT max(tbh.modify_dttm)
		FROM tb_backup_history tbh
		WHERE tbh.category = lower(tbs.category)
		AND tbh.trigger_type = 'scheduled'
		AND CASE WHEN tbs.category = 'ONEBOX' THEN tbs.categoryseq = tbh.serverseq
				WHEN tbs.category = 'NS' THEN tbs.categoryseq = tbh.nsseq
				WHEN tbs.category = 'VNF' THEN tbs.categoryseq = tbh.nfseq 
		END), 'yyyy-mm-dd hh24:mi:ss') modify_dttm
		
, (CASE WHEN tbs.category = 'NS' THEN 
	(SELECT CUSTOMERNAME 
	FROM TB_CUSTOMER
	WHERE CUSTOMERSEQ = (
		SELECT TNS.CUSTOMERSEQ
		FROM TB_NFR TNF
		INNER JOIN TB_NSR TNS ON (TNF.NSSEQ = TNS.NSSEQ)
		WHERE TNS.NSSEQ = tbs.categoryseq
		ORDER BY TNS.CUSTOMERSEQ LIMIT 1 )
	)	
END) customername

FROM tb_backup_scheduler tbs



SELECT * FROM tb_backup_history