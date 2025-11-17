	/*selectPerFormMonitorList*/
	   SELECT
				svr.serverseq,
				svr.onebox_id,
				item.faultgradecode,
				(CASE 
				WHEN item.faultgradecode = 'CRITICAL' THEN 1
				WHEN item.faultgradecode = 'MAJOR' THEN 2
				WHEN item.faultgradecode = 'MINOR' THEN 3
				WHEN item.faultgradecode = 'WARNING' THEN 4
				WHEN item.faultgradecode is null and cast(c3 as int) <= 0 THEN 5
				ELSE 6 END )  ordergrade,
				svr.customername,
				svr.customerseq,
				svr.orgnamescode,
				svr.servername,
				svr.mgmtip
				-- 데이타                            
				, case when cast(c1 as int) > 0 then 'UP' 
					   when cast(c1 as int) is null then null
				  else 'DOWN' 
				  end c1
				, case when cast(c2 as int) > 0 then 'UP' 
					   when cast(c2 as int) is null then null
				  else 'DOWN' 
				  end c2
				, case when cast(c3 as int) > 0 then 'UP' 
					   when cast(c3 as int) is null then null
				  else 'DOWN' 
				  end c3,
				 case when cast(c60 as int) > 0 then 'UP' 
				 when cast(c60 as int) is null then null 
				 else 'DOWN' 
				 end c60, 
								  
				-- 시스템
				to_number(c4,'FM999.99') c4, 
				c5, c6, c7,
				-- Network(WAN)
				c8, c9, c10,
				-- Network(Office)
				c11, c12, c13,'' c14,'' c15,'' c16,
				-- Network(Server)
				c17, c18, c19,
				-- 관제
				CASE 
					WHEN c20::int > 0 THEN 'UP' 
					WHEN c20 is null then null
					ELSE 'DOWN' 
					END c20,
				-- UTM
				to_number(c28,'FM999.99') c28, 
				to_number(c29,'FM999.99') c29, 
				to_number(c30,'FM999.99') c30, 
				c31,
				case when cast(c32 as int) > 0 then 'UP' 
				   when cast(c32 as int) is null then null
				else 'DOWN' 
				end c32,	-- VPN
				-- WAF
				c36, c37, c38, c39,
				-- APC(추가정보)
				c40, c41, c42, c43, c44,
				-- OpenStack
				case when c45::int > 0 then 'UP' 
					when c45::int is null then null
					else 'DOWN' 
					end c45,
				case when c46::int > 0 then 'UP' 
					when c46 is null then null
					else 'DOWN' 
					end c46,
				case when c47::int > 0 then 'UP' 
					when c47 is null then null
					else 'DOWN' 
					end c47,
				case when c48::int > 0 then 'UP' 
					when c48 is null then null
					else 'DOWN' 
					end c48,
				case when c49::int > 0 then 'UP' 
					when c49 is null then null
					else 'DOWN' 
					end c49,
				case when c50::int > 0 then 'UP' 
					when c50 is null then null
					else 'DOWN' 
					end c50,
				-- 장애등급(기본)
				h1, h2, h3,
				-- 시스템
				h4, h5, h6, h7,
				-- Network
				h8, h9, h10,
				h11, h12, h13,
				h17, h18, h19,
				-- 관제
				h20,
				-- UTM
				h28, h29, h30, h31,h32,c54,c55,c56,c57,c58,c59,
				-- WAF
				h36, h37, h38, h39,
				-- APC
				h40, h41, h42, h43, h44,
				-- OpenStack
				h45, h46, h47, h48, h49, h50,
				-- Network(vNIC)
				h54, h55,
				-- Network(vNIC): Office
				h56, h57,
				-- Network(vNIC): Server
				h58, h59, h60
			FROM (
				-- 매핑된 감시항목 데이터를 세로 데이터를 가로 데이터로 변경
				SELECT
					mvi.serverseq,
					-- CRITICAL > MAJOR > MINOR > WARNING
					-- 해당 원박스의 감시항목 중 가장 높은 등급의 장애 등급 발췌.
					-- 장애 등급이 영문으로 'CRITICAL, MAJOR, MINOR, WARNING'를 가지기 때문에 min 함수를 사용함
					min(ca.faultgradecode) faultgradecode,
					-- 기본정보
					max(case when mvi.viewseq = 1 then rtp.monitorvalue end) c1,
					max(case when mvi.viewseq = 2 then rtp.monitorvalue end) c2,
					max(case when mvi.viewseq = 3 then rtp.monitorvalue end) c3,
					max(case when mvi.viewseq = 60 then rtp.monitorvalue end) c60,
					-- System
					max(case when mvi.viewseq = 4 then rtp.monitorvalue end) c4,
					max(case when mvi.viewseq = 5 then rtp.monitorvalue end) c5,
					max(case when mvi.viewseq = 6 then rtp.monitorvalue end) c6,
					max(case when mvi.viewseq = 7 then rtp.monitorvalue end) c7,

					-- Network(NIC): Wan
					COALESCE(sum((case when mvi.viewseq = 8 then rtp.monitorvalue end)::int)::text, '0') || '/' ||
					sum((case when mvi.viewseq = 8 then 1 else 0 end)::int)::text c8,
							 -- 정상인 회선수 / 전체 회선 수
					sum((case when mvi.viewseq = 9 then rtp.monitorvalue end)::int) / (1000000) c9, -- 네트워크 트래픽 정보는 bps 단위를 Mbps로 변화을 위해서 1000000 (1024*1024)로 나눔
					sum((case when mvi.viewseq = 10 then rtp.monitorvalue end)::int) / (1000000) c10,

					-- Network(NIC): Office
					COALESCE(sum((case when mvi.viewseq = 51 or mvi.viewseq = 11 or mvi.viewseq = 14 then rtp.monitorvalue end)::int)::text, '0') || '/' ||
					sum((case when mvi.viewseq = 51 or mvi.viewseq = 11 or mvi.viewseq = 14 then 1 else 0 end)::int)::text c11,
					
					sum((case when mvi.viewseq = 52 or mvi.viewseq = 12 or mvi.viewseq = 15 then rtp.monitorvalue end)::int) / (1000000) c12,
					sum((case when mvi.viewseq = 53 or mvi.viewseq = 13 or mvi.viewseq = 16 then rtp.monitorvalue end)::int) / (1000000) c13,

					-- Network(NIC): Server
					COALESCE(sum((case when mvi.viewseq = 17 then rtp.monitorvalue end)::int)::text, '0') || '/' ||
					sum((case when mvi.viewseq = 17 then 1 else 0 end)::int)::text c17,
					
					sum((case when mvi.viewseq = 18 then rtp.monitorvalue end)::int) / (1000000) c18,
					sum((case when mvi.viewseq = 19 then rtp.monitorvalue end)::int) / (1000000) c19,
					-- 관제
					max(case when mvi.viewseq = 29 then rtp.monitorvalue end) c20, -- XMS 상태정보

					-- UTM
					max(case when mvi.viewseq = 34 then rtp.monitorvalue end) c28,
					max(case when mvi.viewseq = 35 then rtp.monitorvalue end) c29,
					max(case when mvi.viewseq = 36 then rtp.monitorvalue end) c30,
					max(case when mvi.viewseq = 37 then rtp.monitorvalue end) c31,
					max(case when mvi.viewseq = 61 then rtp.monitorvalue end) c32, -- VPN
					
					-- WAF
					max(case when mvi.viewseq = 42 then rtp.monitorvalue end) c36,
					max(case when mvi.viewseq = 43 then rtp.monitorvalue end) c37,
					max(case when mvi.viewseq = 44 then rtp.monitorvalue end) c38,
					max(case when mvi.viewseq = 45 then rtp.monitorvalue end) c39,
					-- 추가정보
					max(case when mvi.viewseq = 46 then rtp.monitorvalue end) c40,
					max(case when mvi.viewseq = 47 then rtp.monitorvalue end) c41,
					max(case when mvi.viewseq = 48 then rtp.monitorvalue end) c42,
					max(case when mvi.viewseq = 49 then rtp.monitorvalue end) c43,
					max(case when mvi.viewseq = 50 then rtp.monitorvalue end) c44,
					-- Openstack
					max(case when mvi.viewseq = 20 then rtp.monitorvalue end) c45,
					max(case when mvi.viewseq = 21 then rtp.monitorvalue end) c46,
					max(case when mvi.viewseq = 22 then rtp.monitorvalue end) c47,
					max(case when mvi.viewseq = 23 then rtp.monitorvalue end) c48,
					max(case when mvi.viewseq = 24 then rtp.monitorvalue end) c49,
					max(case when mvi.viewseq = 25 then rtp.monitorvalue end) c50,
					-- Network(vNIC): Wan
					sum((case when mvi.viewseq = 54 or mvi.viewseq = 38 then rtp.monitorvalue end)::int) / (1000000) c54,
                    sum((case when mvi.viewseq = 55 or mvi.viewseq = 40 then rtp.monitorvalue end)::int) / (1000000) c55,
					-- Network(vNIC): Office
					sum((case when mvi.viewseq = 56 or mvi.viewseq = 39 then rtp.monitorvalue end)::int) / (1000000) c56,
                    sum((case when mvi.viewseq = 57 or mvi.viewseq = 41 then rtp.monitorvalue end)::int) / (1000000) c57,
					-- Network(vNIC): Server
					sum((case when mvi.viewseq = 58 then rtp.monitorvalue end)::int) / (1000000) c58,
					sum((case when mvi.viewseq = 59 then rtp.monitorvalue end)::int) / (1000000) c59,
					
					
					-- tb_curalarm 테이블에서 감시항목별 장애 등급 정보 불러오기
					-- 기본정보
					max(case when mvi.viewseq = 1 then ca.faultgradecode end) h1,
					max(case when mvi.viewseq = 2 then ca.faultgradecode end) h2,
					max(case when mvi.viewseq = 3 then ca.faultgradecode end) h3,
					max(case when mvi.viewseq = 60 then ca.faultgradecode end) h60,
					-- System
					max(case when mvi.viewseq = 4 then ca.faultgradecode end) h4,
					max(case when mvi.viewseq = 5 then ca.faultgradecode end) h5,
					max(case when mvi.viewseq = 6 then ca.faultgradecode end) h6,
					max(case when mvi.viewseq = 7 then ca.faultgradecode end) h7,
					-- Network(NIC): Wan
					min(case when mvi.viewseq = 8 then ca.faultgradecode end) h8,
					min(case when mvi.viewseq = 9 then ca.faultgradecode end) h9,
					min(case when mvi.viewseq = 10 then ca.faultgradecode end) h10,
					-- Network(NIC): Office
					min(case when mvi.viewseq = 51 or mvi.viewseq = 11 or mvi.viewseq = 14 then ca.faultgradecode end) h11,
					min(case when mvi.viewseq = 52 or mvi.viewseq = 12 or mvi.viewseq = 15 then ca.faultgradecode end) h12,
					min(case when mvi.viewseq = 53 or mvi.viewseq = 13 or mvi.viewseq = 16 then ca.faultgradecode end) h13,
					-- Network(NIC): Server
					min(case when mvi.viewseq = 17 then ca.faultgradecode end) h17,
					min(case when mvi.viewseq = 18 then ca.faultgradecode end) h18,
					min(case when mvi.viewseq = 19 then ca.faultgradecode end) h19,
					-- 관제
					max(case when mvi.viewseq = 29 then ca.faultgradecode end) h20, -- XMS 상태정보
					-- UTM
					max(case when mvi.viewseq = 34 then ca.faultgradecode end) h28,
					max(case when mvi.viewseq = 35 then ca.faultgradecode end) h29,
					max(case when mvi.viewseq = 36 then ca.faultgradecode end) h30,
					max(case when mvi.viewseq = 37 then ca.faultgradecode end) h31,
					max(case when mvi.viewseq = 61 then ca.faultgradecode end) h32,
					-- WAF
					max(case when mvi.viewseq = 42 then ca.faultgradecode end) h36,
					max(case when mvi.viewseq = 43 then ca.faultgradecode end) h37,
					max(case when mvi.viewseq = 44 then ca.faultgradecode end) h38,
					max(case when mvi.viewseq = 45 then ca.faultgradecode end) h39,
					-- 추가정보
					max(case when mvi.viewseq = 46 then ca.faultgradecode end) h40,
					max(case when mvi.viewseq = 47 then ca.faultgradecode end) h41,
					max(case when mvi.viewseq = 48 then ca.faultgradecode end) h42,
					max(case when mvi.viewseq = 49 then ca.faultgradecode end) h43,
					max(case when mvi.viewseq = 50 then ca.faultgradecode end) h44,
					-- Openstack
					max(case when mvi.viewseq = 20 then ca.faultgradecode end) h45,
					max(case when mvi.viewseq = 21 then ca.faultgradecode end) h46,
					max(case when mvi.viewseq = 22 then ca.faultgradecode end) h47,
					max(case when mvi.viewseq = 23 then ca.faultgradecode end) h48,
					max(case when mvi.viewseq = 24 then ca.faultgradecode end) h49,
					max(case when mvi.viewseq = 25 then ca.faultgradecode end) h50,
					-- Network(vNIC): Wan
                    min(case when mvi.viewseq = 54 or mvi.viewseq = 38 then ca.faultgradecode end) h54,
                    min(case when mvi.viewseq = 55 or mvi.viewseq = 40 then ca.faultgradecode end) h55,
                    -- Network(vNIC): Office
                    min(case when mvi.viewseq = 56 or mvi.viewseq = 39 then ca.faultgradecode end) h56,
                    min(case when mvi.viewseq = 57 or mvi.viewseq = 41 then ca.faultgradecode end) h57,
					-- Network(vNIC): Server
					min(case when mvi.viewseq = 58 then ca.faultgradecode end) h58,
					min(case when mvi.viewseq = 59 then ca.faultgradecode end) h59
			
				-- 서버별 매핑 정보 발췌
				FROM tb_monviewinstance AS mvi 
				-- 매핑 정보에 해당 하는 감시 항목 발췌
				LEFT OUTER JOIN tb_moniteminstance AS mii ON mvi.moniteminstanceseq = mii.moniteminstanceseq
				-- 감시항목별 현재 모니터링된 값 발췌
				LEFT OUTER JOIN tb_realtimeperf AS rtp ON rtp.moniteminstanceseq = mii.moniteminstanceseq AND rtp.monitoredyn = 'y' -- 최신 정보인 경우에만 rtp.monitoredyn 필드의 값이 'y'다.
				-- 감시항목별 장애 여부를 판단하기 위해
				LEFT OUTER JOIN tb_curalarm AS ca ON mii.moniteminstanceseq = ca.moniteminstanceseq AND ca.faultstagecode = '발생'
				
				WHERE
					mvi.moniteminstanceseq is not null -- mvi.moniteminstanceseq 필드의 값이 null이 아닌 경우는 실제 감시항목이 있는 항목
					AND mii.delete_dttm is null -- 감시항목중 삭제되지 않은 감시항목
				GROUP BY mvi.serverseq
			) AS item
			
			LEFT OUTER JOIN (
				-- 유효한 원박스 목록만 발췌
				SELECT
					svr.onebox_id, svr.serverseq, svr.customerseq, svr.nsseq, svr.servername, svr.mgmtip, svr.orgnamescode, customer.customername
				FROM tb_maphostinstance AS mhi
				LEFT OUTER JOIN tb_server AS svr ON mhi.serverseq = svr.serverseq -- 20160317 김승주 전임 추가요청 (tb_maphostinstance 서버만 표시)
				LEFT OUTER JOIN tb_customer AS customer ON svr.customerseq = customer.customerseq
				WHERE svr.nfsubcategory = 'One-Box' -- 20160229 김승주 전임 추가요청
					-- 기존 코드에 있어서 넣기는 했는데 왜 조건에 들어가는지 모르겠음
					AND svr.orgnamescode IN (
						SELECT DISTINCT b.orgnamescode      
						FROM  tb_org_new a , tb_org_new b, tb_user c
						WHERE a.orgnamescode = c.orgnamescode
							AND c.userid = 'admin'
							AND (CASE WHEN a.orglevel = 1 THEN a.orgseq = b.orgpid 
								WHEN a.orglevel = 2 THEN a.orgseq = b.orgseq 
								WHEN a.orglevel = 3 THEN a.orgseq = b.orgseq           
								END )
						)
					-- 로그인한 사용자가 관리하는 고객사 목록만 발췌하는 조건
					AND svr.customerseq in (
				   		select customerseq 
						from tb_user_mp_customer
						where userid = 'admin'
				   )
			) AS svr ON item.serverseq = svr.serverseq