select a.code as code
               , a.value as value 
               , case when a.code = 'ALL' then 1
                 else 2
                 end sorting  
             from (
                select 'ALL' as code
                            , '전체' as value                
                union
                select distinct targetcode as code
                     , case when targetcode = 'os' then '운영체제' 
                         when targetcode = 'vim' then 'VIM'
                         when targetcode = 'vnf' then 'VNF(UTM/XMS/WIMS)'
                         when targetcode = 'hw' then '서버'
                         when targetcode = 'pnf' then 'PNF' 
                    end as value 
                from tb_montargetcatalog
             ) a
       order by sorting

       
       