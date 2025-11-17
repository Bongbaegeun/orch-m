select p.*		
	from(select q.*, (row_number() over()) record_num
		from ( 
			select distinct a.faultgradecode faultgradecode
		     , a.servername servername
		     , a.serveruuid serveruuid   
		     , a.targetname targetname
		     , a.item item
		     , a.itemCode itemCode
		     , case when a.detail_object is null then a.monitortype
  		            when a.detail_object is not null then a.monitortype||',['||a.detail_object||']'
		       end  monitortype
		     , a.obj obj
		     , a.orgnamescode orgnamescode
		     , a.customername customername
		     , a.faultstagecode faultstagecode
		     , a.faultsummary faultsummary
		     , a.mon_dttm resolve_dttm
		     , a.curalarmseq curalarmseq
		     , a.sorting_event 
		     , a.sorting_grade 
		     , a.sorting_date
		  from (
		  	select case when tc.faultstagecode = '해제' then '5'
		                    when tc.faultstagecode = '조치' then '5'
		                    when tc.faultstagecode = '인지' then '5'
		                    when tc.faultgradecode = 'CRITICAL' then '4'
		                    when tc.faultgradecode = 'MAJOR' then '3'
		                    when tc.faultgradecode = 'MINOR' then '2'
		                    when tc.faultgradecode = 'WARNING' then '1'
		               else '0'
		               end sorting_grade  -- 기초코드 관리가 되지 않아 기본 등급별 우선순위 컬럼임 
		             , case when tc.faultstagecode = '발생' then '2'
	                       else '1'
	                       end sorting_event
	                     , to_char(tc.mon_dttm, 'yyyymmddhh24miss') sorting_date
		             , COUNT(tc.faultgradecode) OVER(PARTITION BY tc.faultgradecode ) as main_count 
		             , tc.faultgradecode faultgradecode  -- 장애등급         	     
			     , tser.servername servername   -- 서버명
			     , tmt.visiblename  targetname   -- 감시대상
			     , tmg.visiblename   item        -- 감시그룹
			     , tmg.mongroupcatseq itemCode   -- 감시그룹코드 
			     , concat (tmi.visiblename, '['||tmi.monitorobject||']') monitortype --감시item
			     , case when tmi.monitorobject is null then tmg.groupname
		                    when tmi.monitorobject is not null then tmi.monitorobject
		                end obj   -- 상세측정대상	     
			     , tc.orgnamescode orgnamescode   -- 지역본부
			     , tcu.customername customername  -- 고객
			     , tc.faultstagecode faultstagecode -- 단계
			     , tc.faultsummary faultsummary    -- 장애요약
			     , to_char(tc.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') mon_dttm           -- 발생시간   
			    -- , tc.mon_dttm  mon_dttm           -- 발생시간
			     /* 추가 참고 정보 컬럼*/ 
			     , tc.serveruuid serveruuid       --서버코드	     
			     , tc.customerseq  customerseq    --고객코드  
			     , trg.orgname orgname            
			     , trg.officecode officecode 
			     , tc.montargetcatseq montargetcatseq	  
			     , tc.monitorvalue  monitorvalue     -- 측정값   
			     , tc.curalarmseq curalarmseq
			     , tc.perceive_detail  perceive_detail -- 인지내용
			     , tc.perceive_user  perceive_user  -- 인지자
			     , tc.perceive_dttm  perceive_dttm  -- 인지일시
			     , tc.resolve_detail resolve_detail -- 조치내용
			     , tc.resolve_user  resolve_user  -- 조치자	     
			     , tc.resolve_dttm  resolve_dttm  -- 조치일시
			     , tmg.mongroupcatseq mongroupcatseq --ITEM SEQ 	     
			     , case when tc.perceive_dttm is not null then 'Y'
			            when tc.perceive_dttm is null then 'N'
			       end per_check  -- 인지유무 flag
			     , case when tc.resolve_dttm is not null then 'Y'
			            when tc.resolve_dttm is null then 'N'
			       end res_check  -- 조치유무 flag 
				 , (select max(tmc.visiblename) 
				      from tb_monviewinstance tmv
				         , tb_monviewcatalog tmc
			  	     where tmv.viewseq = tmc.viewseq   
				       and tmv.serverseq = tser.serverseq
				       and tmv.monitorobject = tmi.monitorobject
				       and tmc.targetcode = tmt.targetcode
				       and tmc.groupname = tmg.groupname
			       ) as detail_object     
			 from tb_curalarm tc
			      left outer join tb_org_new trg on(tc.orgnamescode = trg.orgnamescode)
			      left outer join tb_customer tcu on(tc.customerseq = tcu.customerseq)
			      left outer join tb_server tser on(tc.serveruuid = tser.serveruuid)
			      left outer join tb_montargetcatalog tmt on(tc.montargetcatseq = tmt.montargetcatseq)
			      left outer join tb_mongroupcatalog tmg on(tc.mongroupcatseq = tmg.mongroupcatseq)
			      left outer join tb_moniteminstance tmi on(tc.moniteminstanceseq = tmi.moniteminstanceseq)
			      
			      ) a
			-- WHERE (a.resolve_dttm is null or a.resolve_dttm >= NOW() - '1 day'::INTERVAL) -- 조치일자가 없는데이터 혹은 24시간 이전까지 조치일자만 조회
			WHERE a.orgnamescode in(select distinct b.orgnamescode      
                                    from  tb_org_new a
                                        , tb_org_new b
                                   where a.orgnamescode = '목동'
                                     and (case when a.orglevel = 1 then a.orgseq = b.orgpid 
                                               when a.orglevel = 2 then a.orgseq = b.orgseq 
                                               when a.orglevel = 3 then a.orgseq = b.orgseq           
                                           end ))
			-- and a.customername = #{customerName}
			-- and a.servername = #{serverUuid}
			-- and a.mongroupcatseq = #{intItemMask} -->
			-- and a.targetname = #{monitorTarget}
			-- and a.faultstagecode = #{statusMask}
			-- and a.faultgradecode = #{gradeMask} # 장애등급
		) q) p
		-- where record_num <![CDATA[>=]]> #{startIndex} and record_num <![CDATA[<=]]> #{endIndex}
		order by p.sorting_event desc, p.sorting_grade desc, p.sorting_date desc
