select q.*
                      from ( 
                                  select distinct a.faultgradecode faultgradecode
                           , a.servername servername
                           , a.nfsubcategory nfsubcategory
                           , a.serveruuid serveruuid   
                           , a.targetname targetname
                           , a.targetcode targetcode
                           , a.item item
                           , a.itemCode itemCode
                          -- , a.monitortype monitortype 
                           , case when a.detail_object is null then a.monitortype
                                  when a.detail_object is not null then a.monitortype||',['||a.detail_object||']'
                             end  monitortype
                           , a.obj obj
                           , a.orgnamescode orgnamescode
                           , a.customername customername
                           , a.faultstagecode faultstagecode
                           , case when position( 'license' in a.obj ) > 0 then a.faultsummary || '( ' || a.monitorvalue || ' 일 남음 )' 
                                  else a.faultsummary 
                             end  faultsummary
                           , a.mon_dttm resolve_dttm
                           , a.curalarmseq curalarmseq
                           , a.sorting_event 
                           , a.sorting_grade 
                           , a.sorting_date
                          -- , (row_number() over()) record_num
                           /* 참고 컬럼
                           , a.customerseq  curalarmseq
                           , a.per_check
                           , a.res_check      
                           , a.perceive_detail  
                           , a.perceive_user
                           , a.perceive_dttm
                           , a.resolve_detail
                           , a.resolve_user  
                           , a.resolve_dttm
                           , a.curalarmseq  -- 장애상세 인지, 조치시 필요한 key  
                           , a.mongroupcatseq
                           , a.main_count
                           , a.sorting 
                           */     
                           , a.ob_service_number
                           , a.service_number
                        from (select case when tc.faultstagecode = '해제' then '5'
                                          when tc.faultstagecode = '조치' then '5'
                                          when tc.faultstagecode = '인지' then '5'
                                          when tc.faultgradecode = 'CRITICAL' then '4'
                                          when tc.faultgradecode = 'MAJOR' then '3'
                                          when tc.faultgradecode = 'MINOR' then '2'
                                          when tc.faultgradecode = 'WARNING' then '1'
                                     else '0'
                                     end sorting_grade  -- 기초코드 관리가 되지 않아 기본 등급별 우선순위 컬럼임 
                                   , case when tc.faultstagecode = '발생' then '3'
                                          when tc.faultstagecode = '인지' then '2'
                                  else '1'
                                  end sorting_event
                                , to_char(tc.mon_dttm, 'yyyymmddhh24miss') sorting_date
                                   , COUNT(tc.faultgradecode) OVER(PARTITION BY tc.faultgradecode ) as main_count 
                                   , tc.faultgradecode faultgradecode  -- 장애등급                     
                                       , tser.servername servername   -- 서버명
                                       , tser.nfsubcategory nfsubcategory   -- nfsubcategory
                                      -- , tmt.targetname  targetname   -- 감시대상
                                      -- , tmg.groupname   item         -- item
                                      -- , concat (tmi.monitoritem, '['||tmi.monitorobject||']') monitortype                             
                                       , tmt.visiblename  targetname   -- 감시대상
                                       , tmt.targetcode targetcode --감시코드
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
                                   ,tmc.visiblename AS detail_object    
                                         , tser.ob_service_number
                                         , tc.service_number
                                   from tb_curalarm tc
                                        left outer join tb_org_new trg on(tc.orgnamescode = trg.orgnamescode)
                                        left outer join tb_customer tcu on(tc.customerseq = tcu.customerseq)
                                        left outer join tb_server tser on(tc.serveruuid = tser.serveruuid)
                                        left outer join tb_montargetcatalog tmt on(tc.montargetcatseq = tmt.montargetcatseq)
                                        left outer join tb_mongroupcatalog tmg on(tc.mongroupcatseq = tmg.mongroupcatseq)
                                left outer join tb_moniteminstance tmi on(tc.moniteminstanceseq = tmi.moniteminstanceseq)
                                left outer join tb_monviewinstance tmv ON (tc.moniteminstanceseq = tmv.moniteminstanceseq and tmv.monitorobject = tmi.monitorobject) 
                                               left outer join tb_monviewcatalog tmc ON (tmv.viewseq = tmc.viewseq and tmc.targetcode = tmt.targetcode and tmc.groupname = tmg.groupname ) 
                                      --  order by sorting asc, tc.mon_dttm desc 
  ) a
          
order by a.sorting_event desc, a.sorting_grade desc, a.sorting_date desc

           ) q
