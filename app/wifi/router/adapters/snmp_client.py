"""Read-only pure-Python ASN.1/BER SNMP v1/v2c client (UDP/161).

Only queries SNMP when enabled and answering locally. Never assumes SNMP read access
grants write access, and never attempts brute-force community guessing.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# Standard MIB-2 read-only OIDs
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"

OID_PREFIX_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_PREFIX_IF_TYPE = "1.3.6.1.2.1.2.2.1.3"
OID_PREFIX_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
OID_PREFIX_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_PREFIX_IP_NET_TO_MEDIA_PHYS = "1.3.6.1.2.1.4.22.1.2"  # ARP MACs
OID_PREFIX_IP_NET_TO_MEDIA_NET = "1.3.6.1.2.1.4.22.1.3"  # ARP IPs


def _encode_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])
    raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(raw)]) + raw


def _encode_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def encode_oid(oid: str) -> bytes:
    parts = [int(p) for p in oid.strip(".").split(".")]
    if len(parts) < 2:
        raise ValueError(f"Invalid OID: {oid}")
    out = bytearray([40 * parts[0] + parts[1]])
    for num in parts[2:]:
        if num == 0:
            out.append(0)
            continue
        chunks = []
        n = num
        while n > 0:
            chunks.append(n & 0x7F)
            n >>= 7
        chunks.reverse()
        for i, c in enumerate(chunks):
            out.append(c | (0x80 if i < len(chunks) - 1 else 0))
    return _encode_tlv(0x06, bytes(out))


def decode_oid(raw: bytes) -> str:
    if not raw:
        return ""
    first = raw[0]
    parts = [first // 40, first % 40]
    val = 0
    for b in raw[1:]:
        val = (val << 7) | (b & 0x7F)
        if not (b & 0x80):
            parts.append(val)
            val = 0
    return ".".join(str(p) for p in parts)


def _read_length(data: bytes, offset: int) -> Tuple[int, int]:
    first = data[offset]
    offset += 1
    if not (first & 0x80):
        return first, offset
    nbytes = first & 0x7F
    val = int.from_bytes(data[offset : offset + nbytes], "big")
    return val, offset + nbytes


def _decode_tlv(data: bytes, offset: int) -> Tuple[int, bytes, int]:
    tag = data[offset]
    length, pos = _read_length(data, offset + 1)
    end = pos + length
    return tag, data[pos:end], end


def build_snmp_packet(
    *,
    community: str,
    oid: str,
    pdu_type: int = 0xA0,  # 0xA0=GetRequest, 0xA1=GetNextRequest
    request_id: int = 1001,
    version: int = 1,  # 0=v1, 1=v2c
) -> bytes:
    varbind = _encode_tlv(0x30, encode_oid(oid) + _encode_tlv(0x05, b""))
    vblist = _encode_tlv(0x30, varbind)
    pdu_body = (
        _encode_tlv(0x02, request_id.to_bytes(4, "big", signed=True).lstrip(b"\x00") or b"\x01")
        + _encode_tlv(0x02, b"\x00")
        + _encode_tlv(0x02, b"\x00")
        + vblist
    )
    pdu = _encode_tlv(pdu_type, pdu_body)
    ver_tlv = _encode_tlv(0x02, bytes([version]))
    comm_tlv = _encode_tlv(0x04, community.encode("utf-8"))
    return _encode_tlv(0x30, ver_tlv + comm_tlv + pdu)


def parse_snmp_response(data: bytes) -> List[Tuple[str, object]]:
    """Decode SNMP GetResponse varbinds to (oid_str, python_value)."""
    tag, msg_body, _ = _decode_tlv(data, 0)
    if tag != 0x30:
        return []
    pos = 0
    _, _, pos = _decode_tlv(msg_body, pos)  # version
    _, _, pos = _decode_tlv(msg_body, pos)  # community
    pdu_tag, pdu_body, _ = _decode_tlv(msg_body, pos)
    if pdu_tag != 0xA2:  # GetResponse
        return []
    ppos = 0
    _, _, ppos = _decode_tlv(pdu_body, ppos)  # request-id
    _, err_bytes, ppos = _decode_tlv(pdu_body, ppos)
    err_status = int.from_bytes(err_bytes, "big", signed=True) if err_bytes else 0
    _, _, ppos = _decode_tlv(pdu_body, ppos)  # error-index
    if err_status != 0:
        return []
    vb_tag, vblist_body, _ = _decode_tlv(pdu_body, ppos)
    if vb_tag != 0x30:
        return []
    results: List[Tuple[str, object]] = []
    vpos = 0
    while vpos < len(vblist_body):
        _, vb_body, vpos = _decode_tlv(vblist_body, vpos)
        _, oid_raw, oend = _decode_tlv(vb_body, 0)
        vtag, vval, _ = _decode_tlv(vb_body, oend)
        oid_str = decode_oid(oid_raw)
        if vtag in (0x80, 0x81, 0x82):  # noSuchObject / noSuchInstance / endOfMibView
            continue
        if vtag == 0x04:  # OCTET STRING
            try:
                val: object = vval.decode("utf-8")
                if any(ord(c) < 32 and c not in "\r\n\t" for c in val):
                    val = vval.hex(":")
            except UnicodeDecodeError:
                val = vval.hex(":")
        elif vtag in (0x02, 0x41, 0x42, 0x43):  # INTEGER / Counter32 / Gauge32 / TimeTicks
            val = int.from_bytes(vval, "big", signed=(vtag == 0x02))
        elif vtag == 0x40:  # IpAddress
            val = ".".join(str(b) for b in vval) if len(vval) == 4 else vval.hex()
        elif vtag == 0x06:  # OBJECT IDENTIFIER
            val = decode_oid(vval)
        else:
            val = vval.hex()
        results.append((oid_str, val))
    return results


@dataclass
class SnmpSnapshot:
    reachable: bool
    community_used: str = "public"
    sys_descr: Optional[str] = None
    sys_name: Optional[str] = None
    sys_object_id: Optional[str] = None
    sys_uptime_ticks: Optional[int] = None
    interfaces: List[Dict[str, object]] = field(default_factory=list)
    arp_entries: List[Dict[str, str]] = field(default_factory=list)
    write_supported: bool = False  # Read-only inspection never assumes write
    notes: List[str] = field(default_factory=list)


class SnmpReadOnlyClient:
    """Bounded local-only SNMP v2c/v1 read-only inspector."""

    def __init__(self, host: str, *, port: int = 161, community: str = "public", timeout_s: float = 0.6) -> None:
        addr = ipaddress.ip_address(host)
        if not (addr.is_private or addr.is_loopback or addr.is_link_local):
            raise ValueError("SNMP queries are strictly restricted to local/private router IPs.")
        self.host = host
        self.port = port
        self.community = community
        self.timeout_s = timeout_s

    def _query_one(self, oid: str, *, pdu_type: int = 0xA0, req_id: int = 1001) -> List[Tuple[str, object]]:
        pkt = build_snmp_packet(
            community=self.community,
            oid=oid,
            pdu_type=pdu_type,
            request_id=req_id,
            version=1,
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout_s)
        try:
            sock.sendto(pkt, (self.host, self.port))
            data, _ = sock.recvfrom(4096)
            return parse_snmp_response(data)
        except OSError:
            return []
        finally:
            try:
                sock.close()
            except OSError:
                pass

    def walk_prefix(self, prefix: str, *, max_items: int = 24) -> Dict[str, object]:
        out: Dict[str, object] = {}
        current = prefix
        req_id = 2000
        for _ in range(max_items):
            req_id += 1
            vars_ = self._query_one(current, pdu_type=0xA1, req_id=req_id)
            if not vars_:
                break
            next_oid, val = vars_[0]
            if not next_oid.startswith(prefix + ".") or next_oid == current:
                break
            out[next_oid] = val
            current = next_oid
        return out

    def inspect_readonly(self) -> SnmpSnapshot:
        sys_descr_res = self._query_one(OID_SYS_DESCR, req_id=101)
        if not sys_descr_res:
            return SnmpSnapshot(
                reachable=False,
                community_used=self.community,
                notes=["SNMP UDP/161 did not respond to read-only sysDescr query."],
            )
        sys_descr = str(sys_descr_res[0][1])
        sys_name_res = self._query_one(OID_SYS_NAME, req_id=102)
        sys_obj_res = self._query_one(OID_SYS_OBJECT_ID, req_id=103)
        sys_up_res = self._query_one(OID_SYS_UPTIME, req_id=104)

        if_descrs = self.walk_prefix(OID_PREFIX_IF_DESCR, max_items=16)
        if_speeds = self.walk_prefix(OID_PREFIX_IF_SPEED, max_items=16)
        if_status = self.walk_prefix(OID_PREFIX_IF_OPER_STATUS, max_items=16)
        interfaces: List[Dict[str, object]] = []
        for oid, descr in if_descrs.items():
            idx = oid.rsplit(".", 1)[-1]
            speed_bps = if_speeds.get(f"{OID_PREFIX_IF_SPEED}.{idx}")
            status_code = if_status.get(f"{OID_PREFIX_IF_OPER_STATUS}.{idx}")
            interfaces.append(
                {
                    "index": idx,
                    "name": str(descr),
                    "speed_mbps": round(int(speed_bps) / 1_000_000.0, 2) if isinstance(speed_bps, int) else None,
                    "oper_up": (status_code == 1) if isinstance(status_code, int) else None,
                }
            )

        arp_macs = self.walk_prefix(OID_PREFIX_IP_NET_TO_MEDIA_PHYS, max_items=32)
        arp_ips = self.walk_prefix(OID_PREFIX_IP_NET_TO_MEDIA_NET, max_items=32)
        arp_entries: List[Dict[str, str]] = []
        for oid, mac_val in arp_macs.items():
            suffix = oid[len(OID_PREFIX_IP_NET_TO_MEDIA_PHYS) + 1 :]
            ip_val = str(arp_ips.get(f"{OID_PREFIX_IP_NET_TO_MEDIA_NET}.{suffix}", ""))
            if ip_val or mac_val:
                arp_entries.append({"ip": ip_val, "mac": str(mac_val).lower()})

        return SnmpSnapshot(
            reachable=True,
            community_used=self.community,
            sys_descr=sys_descr,
            sys_name=str(sys_name_res[0][1]) if sys_name_res else None,
            sys_object_id=str(sys_obj_res[0][1]) if sys_obj_res else None,
            sys_uptime_ticks=int(sys_up_res[0][1]) if sys_up_res and isinstance(sys_up_res[0][1], int) else None,
            interfaces=interfaces,
            arp_entries=arp_entries,
            write_supported=False,
            notes=["SNMP read-only inspection succeeded; write capability is never inferred from read access."],
        )
