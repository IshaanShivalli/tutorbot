"""
mDNS Responder for TutorBot PC Server
Advertises tutorbot-server.local on the local network so ESP32 and mobile devices can discover it
"""

from zeroconf import ServiceInfo, Zeroconf
import socket
import time


def get_local_ip():
    """Get the local IP address of this PC"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_mdns_server():
    """Start mDNS responder to advertise tutorbot-server.local and tutorbot-pc.local"""
    local_ip = get_local_ip()
    print(f"Local IP detected: {local_ip}")

    zeroconf = Zeroconf()

    service_info = ServiceInfo(
        "_http._tcp.local.",
        "TutorBot-Server._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=5000,
        properties={"path": "/"},
        server="tutorbot-server.local.",
    )
    zeroconf.register_service(service_info)

    try:
        service_info_pc = ServiceInfo(
            "_http._tcp.local.",
            "TutorBot-PC._http._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=5000,
            properties={"path": "/"},
            server="tutorbot-pc.local.",
        )
        zeroconf.register_service(service_info_pc)
    except Exception as exc:
        print(f"Secondary mDNS info: {exc}")

    print("=" * 60)
    print("✅ TutorBot mDNS Responder Started")
    print("=" * 60)
    print(f"Service Hostname: tutorbot-server.local / tutorbot-pc.local")
    print(f"IP Address:       {local_ip}")
    print(f"Port:             5000")
    print(f"PC Web Access:    http://tutorbot-server.local:5000/")
    print(f"ESP32 Mobile URL: http://tutorbot.local/ (hosted by ESP32)")
    print("")
    print("Press Ctrl+C to stop...")
    print("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⛔ Stopping mDNS Responder...")
        zeroconf.unregister_service(service_info)
        zeroconf.close()
        print("Done!")


if __name__ == "__main__":
    try:
        start_mdns_server()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have zeroconf installed:")
        print("  pip install zeroconf")
