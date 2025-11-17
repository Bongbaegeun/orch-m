    SELECT pc.monplugincatseq, pc.script, pc.type, ic.mongroupcatseq
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=11 AND ic.delete_dttm is null 
        AND (ic.monplugincatseq=pc.monplugincatseq OR dc.monplugincatseq=pc.monplugincatseq)
        AND pc.type!='builtin' AND pc.script is not null AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    GROUP BY pc.monplugincatseq, pc.script, pc.type, ic.mongroupcatseq



SELECT pluginpath, script, type, pi.libpath, libscript, libtype, pi.cfgpath, cfgdata
FROM tb_monplugininstance pi, tb_monplugincatalog pc
WHERE serverseq = 481
AND pi.monplugincatseq = pc.monplugincatseq
AND pi.montargetcatseq = 10
AND pi.delete_dttm is null
GROUP BY pluginpath, script, type, pi.libpath, libscript, libtype, pi.cfgpath, cfgdata



SELECT pluginpath, script, type
FROM tb_monplugininstance pi, tb_monplugincatalog pc
WHERE serverseq = 481
AND pi.monplugincatseq = pc.monplugincatseq
AND pi.montargetcatseq = 10
AND pi.delete_dttm is null
GROUP BY pluginpath, script, type




tb_zbaconfiginstance




SELECT pi.libpath, libscript, libtype, pc.libname
FROM tb_monplugininstance pi, tb_monplugincatalog pc
WHERE serverseq = 481
AND pi.monplugincatseq = pc.monplugincatseq
AND pi.montargetcatseq = 10
AND pi.libpath <> ''
AND pi.delete_dttm is null
GROUP BY pi.libpath, libscript, libtype, pc.libname





    SELECT pc.monplugincatseq, pc.cfgname, pc.cfgpath, pc.cfg_input
    FROM tb_monplugincatalog pc, tb_monitemcatalog ic
        LEFT OUTER JOIN tb_zbdiscoverymap dm ON dm.monitemcatseq=ic.monitemcatseq
        LEFT OUTER JOIN tb_zbdiscoverycatalog dc ON dc.zbdiscoverycatseq=dm.zbdiscoverycatseq
    WHERE ic.montargetcatseq=10 AND ic.delete_dttm is null
        AND (ic.monplugincatseq=pc.monplugincatseq OR dc.monplugincatseq=pc.monplugincatseq)
        AND pc.cfgname is not null AND pc.cfg_input is not null AND pc.delete_dttm is null
        AND pc.monplugincatseq is not null
    GROUP BY pc.monplugincatseq, pc.cfgname, pc.cfgpath, pc.cfg_input



SELECT pc.cfgname, pi.cfgpath, pc.cfg_input
FROM tb_monplugininstance pi, tb_monplugincatalog pc
WHERE serverseq = 481
AND pi.monplugincatseq = pc.monplugincatseq
AND pi.montargetcatseq = 10
AND pi.delete_dttm is null
AND pi.cfgpath <> ''
GROUP BY  pc.cfgname, pi.cfgpath, pc.cfg_input


select * 
from tb_monplugincatalog

