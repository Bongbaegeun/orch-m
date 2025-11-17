SELECT p.*
FROM
  (SELECT q.*,
          (row_number() over()) record_num
   FROM
     (SELECT DISTINCT a.faultgradecode faultgradecode,
                      a.servername servername,
                      a.serveruuid serveruuid,
                      a.targetname targetname,
                      a.item item,
                      a.itemCode itemCode,
                      CASE
                          WHEN a.detail_object IS NULL THEN a.monitortype
                          WHEN a.detail_object IS NOT NULL THEN a.monitortype || ',[' || a.detail_object || ']'
                      END monitortype,
                      a.obj obj,
                      a.orgnamescode orgnamescode,
                      a.customername customername,
                      a.faultstagecode faultstagecode,
                      a.faultsummary faultsummary,
                      a.mon_dttm resolve_dttm,
                      a.curalarmseq curalarmseq,
                      a.sorting_event,
                      a.sorting_grade,
                      a.sorting_date
      FROM
        (SELECT a.*,
                b.visiblename detail_object
         FROM
           (SELECT CASE
                       WHEN tc.faultstagecode = '해제' THEN '5'
                       WHEN tc.faultstagecode = '조치' THEN '5'
                       WHEN tc.faultstagecode = '인지' THEN '5'
                       WHEN tc.faultgradecode = 'CRITICAL' THEN '4'
                       WHEN tc.faultgradecode = 'MAJOR' THEN '3'
                       WHEN tc.faultgradecode = 'MINOR' THEN '2'
                       WHEN tc.faultgradecode = 'WARNING' THEN '1'
                       ELSE '0'
                   END sorting_grade, -- 기초코드 관리가 되지 않아 기본 등급별 우선순위 컬럼임
                   CASE
                       WHEN tc.faultstagecode = '발생' THEN '2'
                       ELSE '1'
                   END sorting_event,
                   to_char(tc.mon_dttm, 'yyyymmddhh24miss') sorting_date,
                   count(tc.faultgradecode) over(PARTITION BY tc.faultgradecode) AS main_count,
                   tc.faultgradecode faultgradecode, -- 장애등급
                   tser.servername servername, -- 서버명
                   tmt.visiblename targetname, -- 감시대상
                   tmg.visiblename item, -- 감시그룹
                   tmg.mongroupcatseq itemCode, -- 감시그룹코드
                   concat (tmi.visiblename, '[' || tmi.monitorobject || ']') monitortype, --감시item
                   CASE
                       WHEN tmi.monitorobject IS NULL THEN tmg.groupname
                       WHEN tmi.monitorobject IS NOT NULL THEN tmi.monitorobject
                   END obj, -- 상세측정대상
                   tc.orgnamescode orgnamescode, -- 지역본부
                   tcu.customername customername, -- 고객
                   tc.faultstagecode faultstagecode, -- 단계
                   tc.faultsummary faultsummary, -- 장애요약
                   to_char(tc.mon_dttm, 'yyyy-mm-dd hh24:mi:ss') mon_dttm -- 발생시간
 -- , tc.mon_dttm  mon_dttm           -- 발생시간
 /* 추가 참고 정보 컬럼*/ ,
                   tc.serveruuid serveruuid, --서버코드
                   tc.customerseq customerseq, --고객코드
                   trg.orgname orgname,
                   trg.officecode officecode,
                   tc.montargetcatseq montargetcatseq,
                   tc.monitorvalue monitorvalue, -- 측정값
                   tc.curalarmseq curalarmseq,
                   tc.perceive_detail perceive_detail, -- 인지내용
                   tc.perceive_user perceive_user, -- 인지자
                   tc.perceive_dttm perceive_dttm, -- 인지일시
                   tc.resolve_detail resolve_detail, -- 조치내용
                   tc.resolve_user resolve_user, -- 조치자
                   tc.resolve_dttm resolve_dttm, -- 조치일시
                   tmg.mongroupcatseq mongroupcatseq, --ITEM SEQ
                   CASE
                       WHEN tc.perceive_dttm IS NOT NULL THEN 'Y'
                       WHEN tc.perceive_dttm IS NULL THEN 'N'
                   END per_check, -- 인지유무 flag
                   CASE
                       WHEN tc.resolve_dttm IS NOT NULL THEN 'Y'
                       WHEN tc.resolve_dttm IS NULL THEN 'N'
                   END res_check, -- 조치유무 flag
                   tser.serverseq,
                   tmi.monitorobject,
                   tmt.targetcode,
                   tmg.groupname
            FROM tb_curalarm tc
            LEFT OUTER JOIN tb_org_new trg ON (tc.orgnamescode = trg.orgnamescode)
            LEFT OUTER JOIN tb_customer tcu ON (tc.customerseq = tcu.customerseq)
            LEFT OUTER JOIN tb_server tser ON (tc.serveruuid = tser.serveruuid)
            LEFT OUTER JOIN tb_montargetcatalog tmt ON (tc.montargetcatseq = tmt.montargetcatseq)
            LEFT OUTER JOIN tb_mongroupcatalog tmg ON (tc.mongroupcatseq = tmg.mongroupcatseq)
            LEFT OUTER JOIN tb_moniteminstance tmi ON (tc.moniteminstanceseq = tmi.moniteminstanceseq
                                                       AND tmi.delete_dttm IS NULL)) a
         LEFT OUTER JOIN
           (SELECT max(tmc.visiblename) visiblename,
                   tmv.serverseq,
                   tmv.monitorobject,
                   tmc.targetcode,
                   tmc.groupname
            FROM tb_monviewinstance tmv,
                 tb_monviewcatalog tmc
            WHERE tmv.viewseq = tmc.viewseq
            GROUP BY tmv.serverseq,
                     tmv.monitorobject,
                     tmc.targetcode,
                     tmc.groupname) b ON (b.serverseq = a.serverseq
                                          AND b.monitorobject = a.monitorobject
                                          AND b.targetcode = a.targetcode
                                          AND b.groupname = a.groupname)) a
      WHERE (a.resolve_dttm IS NULL
             OR a.resolve_dttm >= now() - '1 day'::interval)-- 조치일자가 없는데이터 혹은 24시간 이전까지 조치일자만 조회
        AND a.orgnamescode IN
          (SELECT DISTINCT b.orgnamescode
           FROM tb_org_new a,
                tb_org_new b
           WHERE a.orgnamescode = '목동'
             AND (CASE
                      WHEN a.orglevel = 1 THEN a.orgseq = b.orgpid
                      WHEN a.orglevel = 2 THEN a.orgseq = b.orgseq
                      WHEN a.orglevel = 3 THEN a.orgseq = b.orgseq
                  END))-- and a.customername = #{customerName}
 -- and a.servername = #{serverUuid}
 -- and a.mongroupcatseq = #{intItemMask} -->
 -- and a.targetname = #{monitorTarget}
 -- and a.faultstagecode = #{statusMask}
 -- and a.faultgradecode = #{gradeMask} # 장애등급
) q) p -- where record_num <![CDATA[>=]]> #{startIndex} and record_num <![CDATA[<=]]> #{endIndex}
ORDER BY p.sorting_event DESC,
         p.sorting_grade DESC,
         p.sorting_date DESC