select * from tb_server order by serverseq


SELECT TII.*,
       TD.DAY,
       TD.AVG_INT
FROM TB_MONITEMTREND_DAY TD,
  (SELECT II.MONITEMINSTANCESEQ,
          II.MONITORTYPE,
          II.MONITOROBJECT
   FROM TB_MONITEMINSTANCE II
   LEFT OUTER JOIN TB_MONTARGETCATALOG TC ON (II.MONTARGETCATSEQ=TC.MONTARGETCATSEQ)
   LEFT OUTER JOIN TB_MONGROUPCATALOG GC ON (II.MONGROUPCATSEQ=GC.MONGROUPCATSEQ)
   LEFT OUTER JOIN TB_MONITEMCATALOG IC ON (II.MONITEMCATSEQ=IC.MONITEMCATSEQ)
   WHERE II.SERVERSEQ = 1604
     AND II.DELETE_DTTM IS NULL
     AND (( TC.TARGETCODE='vnf' or TC.TARGETCODE='pnf' )  
          AND GC.GROUPNAME='vnet'
          AND II.MONITORTYPE IN ('Tx Rate',
                                 'Rx Rate'))
     AND II.MONITOROBJECT IN ('eth0',
                              'eth1',
                              'eth2',
                              'eth3',
                              'eth4',
                              'eth5',
                              'eth6',
                              'eth7',
                              'eth8',
                              'eth9') ) TII
WHERE TD.MONITEMINSTANCESEQ=TII.MONITEMINSTANCESEQ
  AND TO_DATE(TD.DAY, 'YYYY-MM-DD') BETWEEN CURRENT_DATE-7 AND CURRENT_DATE -1
ORDER BY TD.DAY desc

