    SELECT pc.monplugincatseq, pc.script, pc.type, ic.mongroupcatseq
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=45 AND ic.delete_dttm is null 
        AND (ic.monplugincatseq=pc.monplugincatseq OR dc.monplugincatseq=pc.monplugincatseq)
        AND pc.type!='builtin' AND pc.script is not null AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    GROUP BY pc.monplugincatseq, pc.script, pc.type, ic.mongroupcatseq





select * from tb_montargetcatalog    



