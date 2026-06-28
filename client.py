import socket
import sys

# ── Configuración ──────────────────────────────────────────────────────────────
port = 5000
# Dejar vacío "" para que el programa pida el host al iniciar.
# O poner directamente la IPv6 del servidor: "2800:200:ede0:d5f:..."
host = ""

# ── Utilidades ─────────────────────────────────────────────────────────────────

def parse_response(data):
    """Separa el estado del contenido en la respuesta del servidor."""
    lines = data.split("\n", 1)
    status  = lines[0]
    content = lines[1] if len(lines) > 1 else ""
    return status, content

# ── Punto de entrada ───────────────────────────────────────────────────────────

def main():
    print("=========================================================")
    print("        NAVEGADOR WEB DE TEXTO - SISTEMAS OPERATIVOS     ")
    print("=========================================================")

    # Pedir el host si no está configurado
    server_host = host.strip("[] ")
    if not server_host:
        server_host = input("Ingrese el host/IP del servidor (Enter = ::1): ").strip("[] ")
        if not server_host:
            server_host = "::1"

    print(f"\n[SISTEMA] Conectando a [{server_host}]:{port}...")

    # Intentar la conexión (dual-stack: IPv6 primero, luego IPv4 si falla)
    client_socket = None
    try:
        addr_infos = socket.getaddrinfo(server_host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except Exception as e:
        print(f"[ERROR] No se pudo resolver '{server_host}': {e}")
        sys.exit(1)

    for af, socktype, proto, _, sa in addr_infos:
        try:
            client_socket = socket.socket(af, socktype, proto)
            client_socket.connect(sa)
            break
        except Exception:
            if client_socket:
                client_socket.close()
            client_socket = None

    if not client_socket:
        print(f"[ERROR] No se pudo conectar a [{server_host}]:{port}.")
        print("        Verifique que el servidor esté activo y el host sea correcto.")
        sys.exit(1)

    print("[SISTEMA] Conexion establecida con exito.\n")

    current_page = "index.txt"

    try:
        # Cargar la página de inicio automáticamente
        client_socket.sendall(f"GET {current_page}".encode("utf-8"))
        status, content = parse_response(client_socket.recv(4096).decode("utf-8"))
        if status.startswith("200"):
            print(content)
        else:
            print(f"[{status}]\n{content}")

        # Bucle de navegación
        while True:
            print("---------------------------------------------------------")
            cmd = input("Pagina (o 'home', 'exit') > ").strip()

            if not cmd:
                continue

            if cmd.lower() in ("exit", "end"):
                print("[SISTEMA] Cerrando conexion...")
                client_socket.sendall("CLOSE".encode("utf-8"))
                break

            if cmd.lower() == "home":
                target = "index.txt"
            else:
                target = cmd if cmd.lower().endswith(".txt") else cmd + ".txt"

            client_socket.sendall(f"GET {target}".encode("utf-8"))
            status, content = parse_response(client_socket.recv(4096).decode("utf-8"))

            if status.startswith("200"):
                current_page = target
                print(f"\n[Pagina actual: {current_page}]")
                print(content)
            else:
                print(f"\n[{status}]\n{content}")
                print(f"[Permaneces en: {current_page}]")

    except ConnectionError:
        print("\n[ERROR] Se perdio la conexion con el servidor.")
    except (KeyboardInterrupt, EOFError):
        print("\n[SISTEMA] Sesion interrumpida.")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        if client_socket:
            client_socket.close()
        print("[SISTEMA] Sesion terminada. ¡Hasta luego!")

if __name__ == "__main__":
    main()
