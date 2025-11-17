select t.active_yn
         , t.location_info
         , t.servername
         , t.serverseq
         , t.targetname
         , t.groupname
         , t.detail_monitor
         , case when t.detail_object is null or t.detail_object = '' then t.detail_monitor
               when t.detail_object is not null then t.detail_monitor||',['||t.detail_object||']'
            end  detail_monitor
         , (case when t.value_type = 'status' and t.monitorvalue2 > 0 then 'UP'
                     when t.value_type = 'status' and t.monitorvalue2 <= 0 then 'DOWN'
                     else t.monitorvalue
                  end || ' '|| case when t.unit = 'Mb' then 'Mbps' else t.unit end) monitorvalue
         , t.monitorvalue2     
         , t.unit      
         , t.value_type       
         , t.orgnamescode
         , t.serveruuid
         , t.itemseq
         , t.stime
         , t.etime
         , t.ob_service_number
         , t.customername
         , t.service_number
         , t.monitoryn
         , t.monitoredyn
      from(
            select t.active_yn
               , t.location_info
               , t.servername
               , t.serverseq
               , t.targetname
               , t.groupname
               , t.detail_monitor
               , (case when position('.' in t.monitorvaluecheck) > 0 then  to_char(t.monitorvalue, 'FM999,999,999,990.00')
                           when position('.' in t.monitorvaluecheck) <= 0 then  to_char(t.monitorvalue, 'FM999,999,999,999')
                           else to_char(t.monitorvalue, 'FM999,999,999,999')
                        end) as monitorvalue
               , cast(t.monitorvalue as numeric) monitorvalue2   
               , t.unit 
               , t.value_type
               , t.orgnamescode
               , t.serveruuid
               , t.itemseq
               , t.stime
               , t.etime
               , t.detail_object
               , t.ob_service_number
               , t.customername
               , t.service_number
               , t.monitoryn
               , t.monitoredyn
            from (
                  select COALESCE(trt.monitoredyn, 'n')  active_yn
                     , concat (tsr.orgnamescode, '/'||tsr.servername) location_info
                     , tsr.servername  servername
                     , tsr.serverseq serverseq
                     , tmtg.visiblename  targetname   --감시대상   
                     , tmgc.visiblename  groupname   --감시그룹
                     , case when tmi.monitorobject is null or tmi.monitorobject = '' then tmi.visiblename
                           when tmi.monitorobject is not null then concat (tmi.visiblename, '['||tmi.monitorobject||']')
                        end detail_monitor
                     --, concat (tmi.visiblename, '['||tmi.monitorobject||']') detail_monitor   --감시item            
                     , trt.monitorvalue as monitorvaluecheck
                     , case when tmi.monitortype = 'Rx Rate' or tmi.monitortype = 'Tx Rate' then (cast(trt.monitorvalue as numeric)/ (1024*1024))
                           else cast(trt.monitorvalue as numeric)
                        end monitorvalue
                     , coalesce(case when tmi.monitortype = 'Rx Rate' or tmi.monitortype = 'Tx Rate' then 'Mbps'
                                 else tmi.unit
                              end, '') unit
                     , tsr.orgnamescode  orgnamescode   --국사명(hidden)
                     , tmi.value_type
                     /* 성능그래프 사용 변수*/
                     , tsr.serveruuid   serveruuid               --성능그래프 svr-uuid
                     , tmi.moniteminstanceseq itemseq               --성능그래프 itemseq
                     , to_char(NOW(), 'yyyy-mm-dd hh24:mi:ss') stime   --성능그래프 stime
                     , to_char(now(), 'yyyy-mm-dd hh24:mi:ss') etime   --성능그래프 etime
                     
                     , (
                        select max(tmc.visiblename) 
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
                        left outer join tb_mongroupcatalog tmgc on(tmi.mongroupcatseq = tmgc.mongroupcatseq)
                        left outer join tb_realtimeperf trt on(tsr.serverseq = trt.serverseq and tmi.moniteminstanceseq = trt.moniteminstanceseq )
                        left outer join tb_montargetcatalog tmtg on(tmi.montargetcatseq = tmtg.montargetcatseq)
                        left outer join tb_customer tcu on(tsr.customerseq = tcu.customerseq)
                  where tmi.delete_dttm is null
                           and tsr.serverseq = 2147
                  order by tmtg.visiblename
                     , tmgc.visiblename
                     , concat (tmi.visiblename, '['||tmi.monitorobject||']') asc 
               )t
         ) t