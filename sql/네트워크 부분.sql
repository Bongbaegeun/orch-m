select COALESCE(trt.monitoredyn, 'n')  active_yn
	, concat (tsr.orgnamescode, '/'||tsr.servername) location_info
	, tsr.servername  servername
	, tsr.serverseq serverseq
	, tmtg.visiblename  targetname --감시대상
	, tmgc.visiblename  groupname --감시그룹
	, tmi.monitorobject ethername
	, concat (tmi.visiblename, '['||tmi.monitorobject||']') detail_monitor --감시item
	, trt.monitorvalue as monitorvaluecheck
	, case when tmi.monitortype = 'Rx Rate' or tmi.monitortype = 'Tx Rate' then (cast(trt.monitorvalue as numeric)/ (1024*1024))
	else cast(trt.monitorvalue as numeric)
	end monitorvalue
	, coalesce(case when tmi.monitortype = 'Rx Rate' or tmi.monitortype = 'Tx Rate' then 'Mbps'
	else tmi.unit
	end, '') unit
	, tsr.orgnamescode  orgnamescode --국사명(hidden)
	, tmi.value_type
	/* 성능그래프 사용 변수*/
	, tsr.serveruuid  serveruuid    --성능그래프 svr-uuid
	, tmi.moniteminstanceseq itemseq    --성능그래프 itemseq
	, to_char(NOW(), 'yyyy-mm-dd hh24:mi:ss') stime --성능그래프 stime
	, to_char(now(), 'yyyy-mm-dd hh24:mi:ss') etime --성능그래프 etime
	, (select max(tmc.visiblename)
		from tb_monviewinstance tmv
		, tb_monviewcatalog tmc
		where tmv.viewseq = tmc.viewseq
		and tmv.serverseq = tsr.serverseq
		and tmv.monitorobject = tmi.monitorobject
		and tmc.targetcode =  tmtg.targetcode
		and tmc.groupname = tmgc.groupname
		) as detail_object
	, tsr.ob_service_number
	, tcu.customername
	, tmi.service_number
	, tmi.monitoryn  --감시 on/off
	, case when trt.monitoredyn is null then 'n' -- 실시간 감시데이터 여부
		else trt.monitoredyn
		end as monitoredyn
	from tb_server tsr
	left outer join tb_moniteminstance tmi on(tsr.serverseq = tmi.serverseq)
	inner join tb_mongroupcatalog tmgc on( tmi.mongroupcatseq = tmgc.mongroupcatseq and tmgc.groupname = 'net')
	left outer join tb_realtimeperf trt on(tsr.serverseq = trt.serverseq and tmi.moniteminstanceseq = trt.moniteminstanceseq )
	left outer join tb_montargetcatalog tmtg on(tmi.montargetcatseq = tmtg.montargetcatseq)
	left outer join tb_customer tcu on(tsr.customerseq = tcu.customerseq)
	where tmi.delete_dttm is null
	and tmtg.montargetcatseq = 9
	--and tmi.monitoryn = 'y'
	--and tmi.realtimeyn = 'y'
	and tsr.serverseq = 356        
	order by tmtg.visiblename
	, tmgc.visiblename
	, concat (tmi.visiblename, '['||tmi.monitorobject||']') asc
	