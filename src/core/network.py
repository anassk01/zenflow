"""
network.py - Network management with packet inspection and connection tracking
"""
import subprocess
import threading
import time
import logging
from typing import Dict, List, Set, Optional, Tuple
import os
from netfilterqueue import NetfilterQueue
from scapy.all import IP, TCP, Raw

logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self):
        """Initialize network manager"""
        self._verify_root()
        self.nfqueue_num = "1"
        self.is_blocking = False
        self.allowed_domains: Set[str] = set()
        self.connection_states = {}
        self.state_lock = threading.Lock()
        self.nfqueue: Optional[NetfilterQueue] = None
        self.nfqueue_thread: Optional[threading.Thread] = None

    def _verify_root(self) -> None:
        """Verify root privileges"""
        if os.geteuid() != 0:
            raise PermissionError("Root privileges required for network management")

    def _extract_http_host(self, payload: bytes) -> Optional[str]:
        """Extract hostname from HTTP Host header"""
        try:
            headers = payload.decode(errors="ignore")
            for line in headers.split("\r\n"):
                if line.lower().startswith("host:"):
                    return line.split(":", 1)[1].strip()
        except Exception:
            pass
        return None

    def _extract_tls_sni(self, payload: bytes) -> Optional[str]:
        """Extract hostname from TLS SNI"""
        try:
            if len(payload) < 5:
                return None
            
            # Check for TLS handshake
            content_type = payload[0]
            if content_type != 22:  # Handshake
                return None
                
            record_length = int.from_bytes(payload[3:5], byteorder="big")
            if len(payload) < 5 + record_length:
                return None
                
            handshake = payload[5:5+record_length]
            if len(handshake) < 4:
                return None
                
            # Check for ClientHello
            handshake_type = handshake[0]
            if handshake_type != 1:  # ClientHello
                return None
                
            # Skip static fields
            pointer = 4  # handshake header
            pointer += 2  # version
            pointer += 32  # random
            
            if pointer >= len(handshake):
                return None
                
            # Skip session ID
            session_id_length = handshake[pointer]
            pointer += 1 + session_id_length
            
            if pointer + 2 > len(handshake):
                return None
                
            # Skip cipher suites
            cipher_suites_length = int.from_bytes(handshake[pointer:pointer+2], byteorder="big")
            pointer += 2 + cipher_suites_length
            
            if pointer >= len(handshake):
                return None
                
            # Skip compression methods
            compression_methods_length = handshake[pointer]
            pointer += 1 + compression_methods_length
            
            if pointer + 2 > len(handshake):
                return None
                
            # Process extensions
            extensions_length = int.from_bytes(handshake[pointer:pointer+2], byteorder="big")
            pointer += 2
            end = pointer + extensions_length
            
            while pointer + 4 <= end and pointer + 4 <= len(handshake):
                ext_type = int.from_bytes(handshake[pointer:pointer+2], byteorder="big")
                pointer += 2
                ext_length = int.from_bytes(handshake[pointer:pointer+2], byteorder="big")
                pointer += 2
                
                if ext_type == 0:  # server_name extension
                    if pointer + 2 > len(handshake):
                        break
                    list_length = int.from_bytes(handshake[pointer:pointer+2], byteorder="big")
                    pointer += 2
                    list_end = pointer + list_length
                    
                    while pointer + 3 < list_end:
                        name_type = handshake[pointer]
                        pointer += 1
                        name_length = int.from_bytes(handshake[pointer:pointer+2], byteorder="big")
                        pointer += 2
                        if pointer + name_length > len(handshake):
                            break
                        server_name = handshake[pointer:pointer+name_length].decode(errors="ignore")
                        return server_name
                else:
                    pointer += ext_length
                    
        except Exception as e:
            logger.debug(f"Error extracting SNI: {e}")
        return None

    def _is_allowed_domain(self, hostname: str) -> bool:
        """Check if hostname is allowed"""
        if not hostname:
            return False
        hostname = hostname.lower().strip()
        return any(hostname == domain or hostname.endswith("." + domain) 
                  for domain in self.allowed_domains)

    def _setup_iptables(self) -> None:
        """Setup iptables rules"""
        rules = [
            # Queue HTTP traffic
            ["iptables", "-I", "OUTPUT", "-p", "tcp", "--dport", "80", 
             "-j", "NFQUEUE", "--queue-num", self.nfqueue_num],
            # Queue HTTPS traffic
            ["iptables", "-I", "OUTPUT", "-p", "tcp", "--dport", "443", 
             "-j", "NFQUEUE", "--queue-num", self.nfqueue_num],
            # Allow DNS queries
            ["iptables", "-I", "OUTPUT", "-p", "udp", "--dport", "53", "-j", "ACCEPT"],
            # Allow loopback
            ["iptables", "-I", "OUTPUT", "-o", "lo", "-j", "ACCEPT"],
        ]

        try:
            # First flush existing rules
            subprocess.check_call(["iptables", "-F"])
            
            # Add rules in order
            for rule in rules:
                subprocess.check_call(rule)
                logger.debug(f"Installed rule: {' '.join(rule)}")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup iptables: {e}")
            self._clear_iptables()
            raise

    def _clear_iptables(self) -> None:
        """Remove iptables rules"""
        rules_to_remove = [
            ["iptables", "-D", "OUTPUT", "-p", "tcp", "--dport", "80", 
             "-j", "NFQUEUE", "--queue-num", self.nfqueue_num],
            ["iptables", "-D", "OUTPUT", "-p", "tcp", "--dport", "443", 
             "-j", "NFQUEUE", "--queue-num", self.nfqueue_num],
        ]
        
        for rule in rules_to_remove:
            try:
                subprocess.check_call(rule)
            except subprocess.CalledProcessError:
                pass

    def _process_packet(self, packet):
        """Process each packet and make blocking decision"""
        try:
            payload = packet.get_payload()
            ip_pkt = IP(payload)
            if not ip_pkt.haslayer(TCP):
                packet.accept()
                return

            tcp_pkt = ip_pkt[TCP]
            conn_tuple = (ip_pkt.src, tcp_pkt.sport, ip_pkt.dst, tcp_pkt.dport)
            now = time.time()

            with self.state_lock:
                state = self.connection_states.get(conn_tuple)

                # New connection: if SYN and not ACK, mark as pending.
                if tcp_pkt.flags & 0x02 and not (tcp_pkt.flags & 0x10):
                    if state is None:
                        self.connection_states[conn_tuple] = {
                            "state": "pending",
                            "timestamp": now,
                            "hostname": None
                        }
                    packet.accept()
                    return

                # If no state, create pending.
                if state is None:
                    self.connection_states[conn_tuple] = {
                        "state": "pending",
                        "timestamp": now,
                        "hostname": None
                    }
                    state = self.connection_states[conn_tuple]

                # If already allowed, let it pass.
                if state["state"] == "allowed":
                    packet.accept()
                    return

                # If already blocked, drop it.
                if state["state"] == "blocked":
                    packet.drop()
                    return

                # Try to extract hostname if payload exists
                if tcp_pkt.haslayer(Raw):
                    raw_data = bytes(tcp_pkt[Raw].load)
                    hostname = None
                    if tcp_pkt.dport == 80:
                        hostname = self._extract_http_host(raw_data)
                    elif tcp_pkt.dport == 443:
                        hostname = self._extract_tls_sni(raw_data)

                    if hostname:
                        state["hostname"] = hostname
                        if self._is_allowed_domain(hostname):
                            state["state"] = "allowed"
                            logger.debug(f"Allowed connection to {hostname}")
                            packet.accept()
                            return
                        else:
                            state["state"] = "blocked"
                            logger.debug(f"Blocked connection to {hostname}")
                            packet.drop()
                            return

                # Handle pending timeout
                if now - state["timestamp"] > 2:  # 2 second grace period
                    state["state"] = "blocked"
                    logger.debug(f"Blocked connection (timeout)")
                    packet.drop()
                    return

                # Allow during grace period
                packet.accept()

        except Exception as e:
            logger.error(f"Error processing packet: {e}")
            packet.drop()

    def _start_packet_inspection(self):
        """Start packet inspection thread"""
        self.nfqueue = NetfilterQueue()
        try:
            self.nfqueue.bind(int(self.nfqueue_num), self._process_packet)
            logger.info("Started packet inspection")
            self.nfqueue.run()
        except Exception as e:
            logger.error(f"Error in packet inspection: {e}")
            self.unblock_all()

    def block_all_except_allowed(self, allowed_domains: List[str]) -> None:
        """Block all traffic except for allowed domains"""
        try:
            # Update allowed domains
            self.allowed_domains = {domain.lower().strip() 
                                  for domain in allowed_domains if domain.strip()}
            
            if not self.is_blocking:
                # Setup new blocking
                self._setup_iptables()
                self.nfqueue_thread = threading.Thread(target=self._start_packet_inspection)
                self.nfqueue_thread.daemon = True
                self.nfqueue_thread.start()
                self.is_blocking = True
                logger.info(f"Blocking enabled with {len(self.allowed_domains)} allowed domains")
            else:
                # Update existing blocking
                logger.info(f"Updated allowed domains: {len(self.allowed_domains)} domains")

            # Clear existing connection states
            with self.state_lock:
                self.connection_states.clear()

        except Exception as e:
            logger.error(f"Failed to setup blocking: {e}")
            self.unblock_all()
            raise

    def unblock_all(self) -> None:
        """Remove all blocking and stop packet inspection"""
        try:
            if self.nfqueue:
                self.nfqueue.unbind()
                self.nfqueue = None

            if self.nfqueue_thread and self.nfqueue_thread.is_alive():
                self.nfqueue_thread.join(timeout=2)

            self._clear_iptables()
            self.is_blocking = False
            
            with self.state_lock:
                self.connection_states.clear()
                
            logger.info("All blocking rules removed")

        except Exception as e:
            logger.error(f"Failed to unblock: {e}")
            raise

    def get_allowed_domains(self) -> Set[str]:
        """Get currently allowed domains"""
        return self.allowed_domains.copy()