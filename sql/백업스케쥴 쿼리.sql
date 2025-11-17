SELECT category, serverseq, nsseq, nfseq, MAX(modify_dttm )
FROM tb_backup_history
WHERE trigger_type = 'scheduled' 
GROUP BY category, serverseq, nsseq, nfseq

LIMIT 10



SELECT tbs.category , 
	tbs.categoryseq , 
	tbh.maxdttm,
(CASE WHEN tbs.category = 'NS'
                      THEN (SELECT CUSTOMERNAME
                      FROM TB_CUSTOMER
                      WHERE CUSTOMERSEQ = (
                      SELECT TNS.CUSTOMERSEQ
                      FROM TB_NFR TNF
                      INNER JOIN TB_NSR TNS ON (TNF.NSSEQ = TNS.NSSEQ)
                      WHERE TNS.NSSEQ = tbs.categoryseq
                      ORDER BY TNS.CUSTOMERSEQ LIMIT 1
                      )
                      )
                      WHEN tbs.category = 'VNF'
                      THEN (SELECT CUSTOMERNAME
                      FROM TB_CUSTOMER
                      WHERE CUSTOMERSEQ = (
                      SELECT TNS.CUSTOMERSEQ
                      FROM TB_NFR TNF
                      INNER JOIN TB_NSR TNS ON (TNF.NSSEQ = TNS.NSSEQ)
                      WHERE TNF.NFSEQ = tbs.categoryseq
                      ORDER BY TNS.CUSTOMERSEQ LIMIT 1
                      )
                      )
                      WHEN tbs.category = 'ONEBOX'
                      THEN (SELECT CUSTOMERNAME
                      FROM TB_CUSTOMER
                      WHERE CUSTOMERSEQ = (
                      SELECT CUSTOMERSEQ
                      FROM TB_SERVER
                      WHERE SERVERSEQ = tbs.categoryseq
                      ORDER BY CUSTOMERSEQ LIMIT 1
                      )
                      )
                      END) customername
FROM tb_backup_scheduler tbs,
	(SELECT UPPER(category) category, serverseq, nsseq, nfseq, to_char(( max(modify_dttm) ), 'yyyy-mm-dd hh24:mi:ss') maxdttm
	FROM tb_backup_history
	WHERE trigger_type = 'scheduled' 
	GROUP BY category, serverseq, nsseq, nfseq) tbh
WHERE tbh.category = tbs.category
	AND 	CASE 
		WHEN tbh.category = 'ONEBOX' THEN tbs.categoryseq = tbh.serverseq 
		WHEN tbh.category = 'NS' THEN tbs.categoryseq = tbh.nsseq 
		WHEN tbh.category = 'VNF' THEN tbs.categoryseq = tbh.nfseq 
	END






	CASE    WHEN tbs.category = 'ONEBOX' THEN
        (
            SELECT customername
            FROM   tb_customer cust, tb_server svr
            WHERE  cust.customerseq = svr.customerseq
            AND     svr.serverseq = tbs.categoryseq
        )
        WHEN tbs.category = 'NS' THEN
        (
            SELECT customername
            FROM   tb_customer cust, tb_nsr tns, tb_nfr tnf
            WHERE  cust.customerseq = tns.customerseq
            AND     tnf.nsseq = tns.nsseq
            AND     tns.nsseq = tbs.categoryseq
        )
        WHEN tbs.category = 'VNF' THEN
        (
            SELECT customername
            FROM   tb_customer cust, tb_nsr tns, tb_nfr tnf
            WHERE  cust.customerseq = tns.customerseq
            AND     tnf.nsseq = tns.nsseq
            AND     tnf.nfseq = tbs.categoryseq
        )        
    END customername  




	CASE    WHEN tbs.category = 'ONEBOX' THEN
        (
            SELECT customername
            FROM   tb_customer cust, tb_server svr
            WHERE  cust.customerseq = svr.customerseq
            AND     svr.serverseq = tbs.categoryseq
        )
        WHEN tbs.category = 'NS' THEN
        (
            SELECT customername
            FROM   tb_customer cust, tb_nsr tns, tb_nfr tnf
            WHERE  cust.customerseq = tns.customerseq
            AND     tnf.nsseq = tns.nsseq
            AND     tns.nsseq = tbs.categoryseq
        )
        WHEN tbs.category = 'VNF' THEN
        (
            SELECT customername
            FROM   tb_customer cust, tb_nsr tns, tb_nfr tnf
            WHERE  cust.customerseq = tns.customerseq
            AND     tnf.nsseq = tns.nsseq
            AND     tnf.nfseq = tbs.categoryseq
        )        
    END customername  





LEFT OUTER JOIN tb_server svr ON rca.onebox_id=svr.onebox_id

	to_char (( 
		SELECT max(tbh.modify_dttm)
		FROM   tb_backup_history tbh
		WHERE  tbh.trigger_type = 'scheduled' 
		AND tbh.category = Lower(tbs.category)		
		AND 	CASE 
				WHEN tbh.category = 'onebox' THEN tbs.categoryseq = tbh.serverseq 
				--WHEN tbh.category = 'ns' THEN tbs.categoryseq = tbh.nsseq 
				--WHEN tbh.category = 'vnf' THEN tbs.categoryseq = tbh.nfseq 
			END
		), 'yyyy-mm-dd hh24:mi:ss') modify_dttm 

		
;




select * from tb_backup_scheduler

EXPLAIN  SELECT tbs.category , 
	tbs.categoryseq , 
	To_char( 
		( 
                SELECT tbh.modify_dttm
                FROM   tb_backup_history tbh 
                WHERE  tbh.category = lower(tbs.category)
                AND    tbh.trigger_type = 'scheduled' 
                AND 	CASE 
                               WHEN tbs.category = 'ONEBOX' THEN tbh.serverseq = 1421
                        END
		ORDER BY  tbh.modify_dttm desc LIMIT 1
                ), 'yyyy-mm-dd hh24:mi:ss') modify_dttm 
FROM   tb_backup_scheduler tbs
;





EXPLAIN SELECT 	tbs.category ,  
	tbs.categoryseq , 
	To_char( 
		( 
                SELECT Max(tbh.modify_dttm) 
                FROM   tb_backup_history tbh 
                WHERE  tbh.category = tbs.category
                AND    tbh.trigger_type = 'scheduled' 
                AND 	CASE 
                               WHEN tbs.category = 'ONEBOX' THEN tbs.categoryseq = tbh.serverseq
                               WHEN tbs.category = 'NS' THEN tbs.categoryseq = tbh.nsseq 
                               WHEN tbs.category = 'VNF' THEN tbs.categoryseq = tbh.nfseq 
                        END), 'yyyy-mm-dd hh24:mi:ss') modify_dttm 
FROM   tb_backup_scheduler tbs





SELECT 	tbs.category , 
	tbs.categoryseq , 
	To_char( 
		( 
                SELECT Max(tbh.modify_dttm) 
                FROM   tb_backup_history tbh 
                WHERE  UPPER(tbh.category) = tbs.category
                AND    tbh.trigger_type = 'scheduled' 
                AND 	CASE 
                               WHEN tbs.category = 'ONEBOX' THEN tbs.categoryseq = tbh.serverseq
                        END), 'yyyy-mm-dd hh24:mi:ss') modify_dttm 
FROM   tb_backup_scheduler tbs



SELECT tbs.category , 
tbs.categoryseq , 
To_char(                
( 
                SELECT Max(tbh.modify_dttm) 
                FROM   tb_backup_history tbh 
                WHERE  tbh.category = tbs.category
                AND    tbh.trigger_type = 'scheduled' 
                AND CASE 
                               WHEN tbs.category = 'ONEBOX' THEN tbs.categoryseq = tbh.serverseq
                               WHEN tbs.category = 'NS' THEN tbs.categoryseq = tbh.nsseq 
                               WHEN tbs.category = 'VNF' THEN tbs.categoryseq = tbh.nfseq 
                        END), 'yyyy-mm-dd hh24:mi:ss') modify_dttm 
FROM   tb_backup_scheduler tbs
;




select * from tb_nfr 


select * from tb_backup_scheduler
 where serverseq = 731


			SELECT customername 
			FROM   tb_customer cust, tb_server svr
			WHERE  cust.customerseq = svr.customerseq
			AND 	svr.serverseq = 731
