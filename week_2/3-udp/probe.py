#!/usr/bin/env python3
# Interactive UDP client for the Smart Home Gateway UDP server.
#
# Usage: each line of input is "PORT message", e.g.:
#   > 4218 hello
#   > 4215 some other message
#
# The gateway replies to YOUR IP on the SAME port you sent to (from a random
# source port), so we bind to PORT, send from it, and read the reply on it.
#
# NOTE: a host firewall (ufw) will drop those replies, because they come from
# a random source port and don't match the outgoing "connection". Allow them:
#   sudo ufw allow from 192.168.4.1 to any port 4210:4219 proto udp
import select
import socket
import time

GW = "192.168.4.1"
TIMEOUT = 1.5  # seconds to wait for a reply

socks = {}  # port -> bound socket, reused across probes


def get_sock(port):
    if port not in socks:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("", port))
        socks[port] = s
    return socks[port]


def ask(port, payload):
    sock = get_sock(port)

    # throw away anything already queued (old broadcasts / late replies)
    while select.select([sock], [], [], 0)[0]:
        sock.recvfrom(2048)

    sock.sendto(payload, (GW, port))

    end = time.time() + TIMEOUT
    while (left := end - time.time()) > 0:
        if not select.select([sock], [], [], left)[0]:
            break
        data, addr = sock.recvfrom(2048)
        if b"status_update" in data or b"udp_test" in data:
            continue  # telemetry broadcast, not our reply
        return data
    return None


def main():
    print(f"== target {GW} ==")
    print("Enter lines as: PORT message   e.g.  4218 hello")
    print("(Ctrl+C / Ctrl+D to quit)\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue

        port_str, _, message = line.partition(" ")
        if not port_str.isdigit() or not message:
            print("[!] Expected: PORT message")
            continue
        port = int(port_str)

        try:
            resp = ask(port, message.encode())
        except OSError as e:
            print(f"[!] port {port}: {e}  (another script bound to it? pkill -f probe.py)")
            continue

        if resp is None:
            print(f"  [{port}] {message} -> no reply")
        else:
            print(f"  [{port}] {message} -> {resp.decode(errors='replace')!r}")

    for s in socks.values():
        s.close()


if __name__ == "__main__":
    main()
