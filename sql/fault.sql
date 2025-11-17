SELECT faultgradecode "장애등급"
	, faultstagecode "단계"
	, tcu.customername "고객"
	, to_char(his.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') "발생시간"
	, his.onebox_id "서버명"
	, his.service_number "서비스번호"
	, tmt.visiblename  "감시대상"
	, tmg.visiblename  "감시그룹"
	, concat (tmi.visiblename, '['||tmi.monitorobject||']') "감시 item"
	, his.faultsummary "장애요약"
FROM tb_histalarm his
LEFT OUTER JOIN tb_customer tcu ON (his.customerseq = tcu.customerseq)
LEFT OUTER JOIN tb_montargetcatalog tmt on(his.montargetcatseq = tmt.montargetcatseq)
LEFT OUTER JOIN tb_mongroupcatalog tmg on(his.mongroupcatseq = tmg.mongroupcatseq)
LEFT OUTER JOIN tb_moniteminstance tmi ON (his.moniteminstanceseq = tmi.moniteminstanceseq) 
WHERE his.faultgradecode = 'CRITICAL'
ORDER BY his.mon_dttm DESC
--limit 100
