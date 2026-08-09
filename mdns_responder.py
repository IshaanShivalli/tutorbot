"""
mDNS Responder for TutorBot
Advertises tutorbot.all.edu on the local network so mobile devices can access it
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
    """Start mDNS responder to advertise tutorbot.all.edu"""
    local_ip = get_local_ip()
    print(f"Local IP detected: {local_ip}")
    
    # Create service info
    service_info = ServiceInfo(
        "_http._tcp.local.",
        "TutorBot._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=5000,
        properties={"path": "/"},
        server="tutorbot.all.edu.local.",
    )
    
    # Register service
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)
    
    print("=" * 60)
    print("✅ mDNS Responder Started")
    print("=" * 60)
    print(f"Service: tutorbot.all.edu.local")
    print(f"IP Address: {local_ip}")
    print(f"Port: 5000")
    print(f"Access from mobile: http://tutorbot.all.edu.local:5000/")
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
