-- DROP FUNCTION change_lan(integer,character varying,character varying,character varying);
-- 
CREATE OR REPLACE FUNCTION change_lan (
	svrseq INTEGER,
	bf_eth TEXT,
	af_eth TEXT,
	lan_name TEXT )
RETURNS BOOLEAN AS $$
DECLARE 
	STATUS integer;
	RX integer;
	TX integer;
	RTN Boolean;
BEGIN
	-- viewseq = 8,9,10 = wan
	-- viewseq = 17,18,19 = server
	-- viewseq  = 51,52,53 = office

	RTN = False;
	
	IF upper(lan_name) = 'WAN' THEN
		STATUS = 8;
		RX =  9;
		TX = 10;
	ELSIF upper(lan_name) = 'SERVER' THEN
		STATUS = 17;
		RX =  18;
		TX = 19;		
	ELSIF upper(lan_name) = 'OFFICE' THEN
		STATUS = 51;
		RX =  52;
		TX = 53;		
	END IF;

	-- stuts
	UPDATE tb_monviewinstance SET
		viewseq = STATUS,
		monitorobject = af_eth
	WHERE viewseq in (8,17,51)
	AND serverseq = svrseq 
	AND monitorobject = bf_eth;

	-- rx
	UPDATE tb_monviewinstance SET
		viewseq = RX,
		monitorobject = af_eth
	WHERE viewseq in (9, 18, 52)
	AND serverseq = svrseq
	AND monitorobject = bf_eth;
	
	-- tx
	UPDATE tb_monviewinstance SET
		viewseq = TX,
		monitorobject = af_eth
	WHERE viewseq in (10, 19, 53)
	AND serverseq = svrseq
	AND monitorobject = bf_eth;

	RTN = True;

	RETURN RTN;
	
END; $$
LANGUAGE 'plpgsql';
