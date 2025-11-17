/*selectPerFormMonitorList*/
      SELECT
               svr.router,
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
            CASE when ha is not null then svr.servername || '|' || ha 
                     else svr.servername
                 END servername,
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

             case when cast(cicmp as int) > 0 then 'UP' 
             when cast(cicmp as int) is null then null 
             else 'DOWN' 
             end cicmp, 
                          
            -- 시스템
            to_number(c4,'FM999.99') c4, 
            c5, c6, c7,
            -- Network(WAN)
            c8, c9, c10,
            -- Network(Office)
            c11, c12, c13,'' c14,'' c15,'' c16,
            -- Network(Server)
            c17, c18, c19,
            -- Network(EX_WAN)
            ex_wan_status, ex_wan_rx,ex_wan_tx,
            -- Network(Other)
            lan_other_status, lan_other_rx,lan_other_tx,
            
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
            end c32,   -- VPN

            case when cast(VpnTotalCount as int) > 0 then 
               trim(to_char(VpnActiveCount::int, '9,999')) || '/' || trim(to_char(VpnTotalCount::int, '9,999'))
                 else null
            end Vpn_Status,
            
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
               
            -- vlan (other)
            vlan_other_rx, vlan_other_tx,
               
            -- vCallBox
            to_number(c65,'FM999.99') c65, 
            to_number(c66,'FM999.99') c66, 
            to_number(c67,'FM999.99') c67, 
            case when c68::int > 0 then 'UP' 
               when c68 is null then null
               else 'DOWN' 
               end c68,
            case when c69::int > 0 then 'UP' 
               when c69 is null then null
               else 'DOWN' 
               end c69,
               
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
            h58, h59, h60,

            -- Network(EX_WAN)
            h_ex_wan_status, h_ex_wan_rx, h_ex_wan_tx,
            
            -- Network(OTHER)
            h_lan_other_status, h_lan_other_rx, h_lan_other_tx,
            
            -- vCallBox
            h65, h66, h67, h68, h69, hicmp,
            
            -- vLan (other)
            h_vlan_other_rx, h_vlan_other_tx
             
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

	       -- icmp
               max(case when mvi.viewseq = 87 then rtp.monitorvalue end) cicmp,
               
               -- System
               max(case when mvi.viewseq = 4 then rtp.monitorvalue end) c4,
               max(case when mvi.viewseq = 5 then rtp.monitorvalue end) c5,
               sum((case when mvi.viewseq in(6, 74, 93) then rtp.monitorvalue end)::int)::text c6,
               -- max(case when mvi.viewseq = 6 then rtp.monitorvalue end) c6,
               max(case when mvi.viewseq = 7 then rtp.monitorvalue end) c7,

               -- Network(NIC): Wan
               COALESCE(count((case when mvi.viewseq in ( 8, 92, 94) then rtp.monitorvalue end)::int)::text, '0') || '/' ||
               sum((case when mvi.viewseq in ( 8, 92, 94) then 1 else 0 end)::int)::text c8,
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

               -- Network(NIC): EX_WAN
               COALESCE(sum((case when mvi.viewseq = 62 then rtp.monitorvalue end)::int)::text, '0') || '/' ||
               sum((case when mvi.viewseq = 62 then 1 else 0 end)::int)::text ex_wan_status,
               sum((case when mvi.viewseq = 63 then rtp.monitorvalue end)::int) / (1000000) ex_wan_rx,
               sum((case when mvi.viewseq = 64 then rtp.monitorvalue end)::int) / (1000000) ex_wan_tx,

               -- Network(NIC): OTHER
               COALESCE(sum((case when mvi.viewseq = 75 then rtp.monitorvalue end)::int)::text, '0') || '/' ||
               sum((case when mvi.viewseq = 75 then 1 else 0 end)::int)::text lan_other_status,
               sum((case when mvi.viewseq = 76 then rtp.monitorvalue end)::int) / (1000000) lan_other_rx,
               sum((case when mvi.viewseq = 77 then rtp.monitorvalue end)::int) / (1000000) lan_other_tx,
               
               -- 관제
               max(case when mvi.viewseq = 29 then rtp.monitorvalue end) c20, -- XMS 상태정보

               -- UTM
               max(case when mvi.viewseq = 34 then rtp.monitorvalue end) c28,
               max(case when mvi.viewseq = 35 then rtp.monitorvalue end) c29,
               max(case when mvi.viewseq = 36 then rtp.monitorvalue end) c30,
               max(case when mvi.viewseq = 37 then rtp.monitorvalue end) c31,
               max(case when mvi.viewseq in ( 61, 97 ) then rtp.monitorvalue end) c32, -- VPN
               
               max(case when mvi.viewseq in ( 72, 95 ) then rtp.monitorvalue end) VpnTotalCount, -- VPN TotalCount
               max(case when mvi.viewseq in ( 73, 96 ) then rtp.monitorvalue end) VpnActiveCount, -- VPN ActiveCount
               
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
               CASE WHEN svr.nfsubcategory = 'One-Box' THEN 
                  sum((case when mvi.viewseq = 54 or mvi.viewseq = 38 then rtp.monitorvalue end)::int) / (1000000)
               ELSE 
                  sum((case when mvi.viewseq = 9 then rtp.monitorvalue end)::int) / (1000000) END c54,
               CASE WHEN svr.nfsubcategory = 'One-Box' THEN 
                  sum((case when mvi.viewseq = 55 or mvi.viewseq = 40 then rtp.monitorvalue end)::int) / (1000000)
               ELSE 
                  sum((case when mvi.viewseq = 10 then rtp.monitorvalue end)::int) / (1000000) END c55,

               -- Network(vNIC): Office
               CASE WHEN svr.nfsubcategory = 'One-Box' THEN 
                  sum((case when mvi.viewseq = 56 or mvi.viewseq = 39 then rtp.monitorvalue end)::int) / (1000000) 
               ELSE
                  sum((case when mvi.viewseq = 52 or mvi.viewseq = 12 or mvi.viewseq = 15 then rtp.monitorvalue end)::int) / (1000000) END c56,

               CASE WHEN svr.nfsubcategory = 'One-Box' THEN 
                  sum((case when mvi.viewseq = 57 or mvi.viewseq = 41 then rtp.monitorvalue end)::int) / (1000000)
               ELSE
                  sum((case when mvi.viewseq = 53 or mvi.viewseq = 13 or mvi.viewseq = 16 then rtp.monitorvalue end)::int) / (1000000) END c57,

               -- Network(vNIC): Server
               CASE WHEN svr.nfsubcategory = 'One-Box' THEN 
                  sum((case when mvi.viewseq = 58 then rtp.monitorvalue end)::int) / (1000000) 
               ELSE
                  sum((case when mvi.viewseq = 18 then rtp.monitorvalue end)::int) / (1000000) END c58,

               CASE WHEN svr.nfsubcategory = 'One-Box' THEN 
                  sum((case when mvi.viewseq = 59 then rtp.monitorvalue end)::int) / (1000000) 
               ELSE
                  sum((case when mvi.viewseq = 19 then rtp.monitorvalue end)::int) / (1000000) END c59,

               -- Network(vNIC): Other
               sum((case when mvi.viewseq = 84 then rtp.monitorvalue end)::int) / (1000000) vlan_other_rx,
               sum((case when mvi.viewseq = 85 then rtp.monitorvalue end)::int) / (1000000) vlan_other_tx,

               -- vCallbox 
               max(case when mvi.viewseq = 65 then rtp.monitorvalue end) c65,
               max(case when mvi.viewseq = 66 then rtp.monitorvalue end) c66,
               max(case when mvi.viewseq = 67 then rtp.monitorvalue end) c67,
               max(case when mvi.viewseq = 68 then rtp.monitorvalue end) c68,
               max(case when mvi.viewseq = 69 then rtp.monitorvalue end) c69,

               max(case when mvi.viewseq = 86 then rtp.monitorvalue end) ha,
                              




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
               
               -- Network(NIC): EX_WAN
               min(case when mvi.viewseq = 62 then ca.faultgradecode end) h_ex_wan_status,
               min(case when mvi.viewseq = 63 then ca.faultgradecode end) h_ex_wan_rx,
               min(case when mvi.viewseq = 64 then ca.faultgradecode end) h_ex_wan_tx,

               -- Network(NIC): OTHER
               min(case when mvi.viewseq = 75 then ca.faultgradecode end) h_lan_other_status,
               min(case when mvi.viewseq = 76 then ca.faultgradecode end) h_lan_other_rx,
               min(case when mvi.viewseq = 77 then ca.faultgradecode end) h_lan_other_tx,

               
               -- 관제
               max(case when mvi.viewseq = 29 then ca.faultgradecode end) h20, -- XMS 상태정보
               -- UTM
               max(case when mvi.viewseq = 34 then ca.faultgradecode end) h28,
               max(case when mvi.viewseq = 35 then ca.faultgradecode end) h29,
               max(case when mvi.viewseq = 36 then ca.faultgradecode end) h30,
               max(case when mvi.viewseq = 37 then ca.faultgradecode end) h31,
               max(case when mvi.viewseq in ( 61, 97) then ca.faultgradecode end) h32,
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
               min(case when mvi.viewseq = 59 then ca.faultgradecode end) h59,

               -- Network(vNIC): Other
               min(case when mvi.viewseq = 84 then ca.faultgradecode end) h_vlan_other_rx,
               min(case when mvi.viewseq = 85 then ca.faultgradecode end) h_vlan_other_tx,

               -- vCallBox
               max(case when mvi.viewseq = 65 then ca.faultgradecode end) h65,
               max(case when mvi.viewseq = 66 then ca.faultgradecode end) h66,
               max(case when mvi.viewseq = 67 then ca.faultgradecode end) h67,
               max(case when mvi.viewseq = 68 then ca.faultgradecode end) h68,
               max(case when mvi.viewseq = 87 then ca.faultgradecode end) hicmp,               
               max(case when mvi.viewseq = 69 then ca.faultgradecode end) h69

                 -- 서버별 매핑 정보 발췌
                 FROM tb_monviewinstance AS mvi
                 -- PNF 형 onebox-type 를 가져오기 위해 server table 추가
                 LEFT OUTER JOIN tb_server AS svr ON mvi.serverseq = svr.serverseq
                 -- 매핑 정보에 해당 하는 감시 항목 발췌
                 LEFT OUTER JOIN tb_moniteminstance AS mii ON mvi.moniteminstanceseq = mii.moniteminstanceseq
                 
                
            -- 감시항목별 현재 모니터링된 값 발췌
            LEFT OUTER JOIN tb_realtimeperf AS rtp ON rtp.moniteminstanceseq = mii.moniteminstanceseq AND rtp.monitoredyn = 'y' -- 최신 정보인 경우에만 rtp.monitoredyn 필드의 값이 'y'다.
            -- 감시항목별 장애 여부를 판단하기 위해
            LEFT OUTER JOIN tb_curalarm AS ca ON mii.moniteminstanceseq = ca.moniteminstanceseq AND ca.faultstagecode = '발생'
            
            WHERE mvi.moniteminstanceseq is not null -- mvi.moniteminstanceseq 필드의 값이 null이 아닌 경우는 실제 감시항목이 있는 항목
               AND mii.delete_dttm is null -- 감시항목중 삭제되지 않은 감시항목
               AND mvi.serverseq = svr.serverseq
               -- AND svr.customerseq in (934,935)
GROUP BY mvi.serverseq, svr.nfsubcategory
         ) AS item
         
         LEFT OUTER JOIN (
            -- 유효한 원박스 목록만 발췌
            SELECT
               svr.onebox_id, svr.serverseq, svr.customerseq, svr.nsseq, svr.servername, svr.mgmtip, svr.orgnamescode, customer.customername, svr.router
            FROM tb_maphostinstance AS mhi
            LEFT OUTER JOIN tb_server AS svr ON mhi.serverseq = svr.serverseq -- 20160317 김승주 전임 추가요청 (tb_maphostinstance 서버만 표시)
            LEFT OUTER JOIN tb_customer AS customer ON svr.customerseq = customer.customerseq
            WHERE svr.nfsubcategory != 'System'   -- 20160229 김승주 전임 추가요청
         ) AS svr ON item.serverseq = svr.serverseq
         
ORDER BY ordergrade,svr.customername  collate "C" ASC

