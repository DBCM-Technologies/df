from df.server import Server
import psutil

from threading import Thread

def print_info():
    print("Seving at:")
    for iface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family.name == 'AF_INET':
                ip = snic.address
                print(f"    http://{ip}:5381")

def main():
    with Server(('', 5381)) as server:
        print_info()
        server_thread = Thread(target=server.serve_forever)
        server_thread.start()
        try:
            while True:
                input()
        except:
            server.shutdown()
            server_thread.join()
            raise

if __name__ == "__main__":
    main()

