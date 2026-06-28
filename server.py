import os
import socket
import threading

# ── Configuración ──────────────────────────────────────────────────────────────
PORT     = 5000
BIND_IP  = "::"   # "::" escucha en TODAS las interfaces IPv4 e IPv6 (dual-stack)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "base"))

# ── Detección de IPs locales ───────────────────────────────────────────────────

def get_local_ips():
    """Detecta las IPs externas activas mediante conexiones UDP ficticias."""
    ips = []
    for family, test_addr in [(socket.AF_INET, "8.8.8.8"), (socket.AF_INET6, "2001:4860:4860::8888")]:
        s = socket.socket(family, socket.SOCK_DGRAM)
        try:
            s.connect((test_addr, 1))
            ip = s.getsockname()[0]
            if ip not in ips:
                ips.append(ip)
        except Exception:
            pass
        finally:
            s.close()
    return ips

# ── Resolución segura de rutas ─────────────────────────────────────────────────

def resolve_path_safely(base_dir, relative_path):
    """
    Resuelve una ruta relativa de forma segura e insensible a mayúsculas/minúsculas.
    Retorna (ruta_absoluta, "ok") o (None, "not_found" | "directory_traversal").
    """
    parts = relative_path.replace("\\", "/").strip("/").split("/")
    current = base_dir

    for part in parts:
        if not part or part == ".":
            continue
        if part == "..":
            return None, "directory_traversal"
        try:
            match = next((i for i in os.listdir(current) if i.lower() == part.lower()), None)
        except OSError:
            return None, "not_found"
        if match is None:
            return None, "not_found"
        current = os.path.join(current, match)

    abs_path = os.path.abspath(current)
    if not abs_path.startswith(base_dir):
        return None, "directory_traversal"
    return abs_path, "ok"

# ── Manejo de clientes ─────────────────────────────────────────────────────────

def handle_client(client_socket, client_address):
    """Atiende todas las peticiones de un cliente en su propio hilo."""
    ip, port = client_address[0], client_address[1]
    print(f"\n[+] Conectado: {ip}:{port}")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            request = data.decode("utf-8").strip()
            print(f"[>] {ip} solicita: '{request}'")

            if request.startswith("GET "):
                filename = request[4:].strip()
                res_path, status_code = resolve_path_safely(BASE_DIR, filename)

                if status_code == "directory_traversal":
                    response = "403 FORBIDDEN\nAcceso denegado. Intento de navegacion no autorizado."
                    print(f"[!] Directory Traversal bloqueado de {ip}: '{filename}'")
                elif status_code == "not_found":
                    response = f"404 NOT FOUND\nEl archivo '{filename}' no fue encontrado."
                    print(f"[404] '{filename}' no existe.")
                elif os.path.isfile(res_path):
                    try:
                        with open(res_path, "r", encoding="utf-8") as f:
                            response = "200 OK\n" + f.read()
                        print(f"[<] Enviado: '{filename}' -> {ip}:{port}")
                    except Exception as e:
                        response = f"500 SERVER ERROR\nError al leer '{filename}': {e}"
                        print(f"[500] Error leyendo '{filename}': {e}")
                else:
                    response = f"404 NOT FOUND\n'{filename}' es un directorio, no un archivo."
                    print(f"[404] '{filename}' es un directorio.")

            elif request == "CLOSE":
                print(f"[-] {ip}:{port} cerró la sesión correctamente.")
                break

            else:
                response = "400 BAD REQUEST\nFormato desconocido. Use: GET <archivo>"
                print(f"[400] Petición inválida de {ip}: '{request}'")

            client_socket.sendall(response.encode("utf-8"))

    except ConnectionResetError:
        print(f"[!] {ip}:{port} se desconectó abruptamente.")
    except Exception as e:
        print(f"[!] Error con {ip}:{port}: {e}")
    finally:
        client_socket.close()
        print(f"[-] Conexión cerrada: {ip}:{port}")

# ── Punto de entrada ───────────────────────────────────────────────────────────

def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    # Socket IPv6 con dual-stack habilitado (también acepta conexiones IPv4)
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

    try:
        server_socket.bind((BIND_IP, PORT))
        server_socket.listen(5)

        print("=========================================================")
        print("         SERVIDOR WEB DE TEXTO - SISTEMAS OPERATIVOS      ")
        print("=========================================================")
        print("IPs para conexiones externas (comparte una con el cliente):")
        local_ips = get_local_ips()
        if local_ips:
            for ip in local_ips:
                print(f"  -> {ip}")
        else:
            print("  -> (No se detectaron IPs externas activas)")
        print(f"\nLoopback (misma maquina):  ::1  /  localhost")
        print(f"Puerto de escucha:         {PORT}")
        print(f"Directorio de paginas:     {BASE_DIR}")
        print("\nEsperando clientes... (Ctrl+C para detener)")
        print("---------------------------------------------------------")

        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    except KeyboardInterrupt:
        print("\n[APAGADO] Servidor detenido por el usuario.")
    except Exception as e:
        print(f"\n[ERROR CRITICO] No se pudo iniciar el servidor: {e}")
    finally:
        server_socket.close()
        print("[SISTEMA] Servidor cerrado correctamente.")

if __name__ == "__main__":
    main()
