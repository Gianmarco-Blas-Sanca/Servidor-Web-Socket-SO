import os
import socket
import threading

# Puerto de escucha del servidor
PORT = 5000
# IP de escucha del servidor (Modificar aquí para forzar a una interfaz de red específica)
# Por defecto "::" escucha en todas las interfaces de red IPv4 e IPv6 activas (Dual-Stack)
BIND_IP = "::"

# Directorio base que contiene las páginas (archivos .txt)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'base'))

def get_local_ips():
    """Obtiene una lista de todas las direcciones IP (IPv4 e IPv6) activas en la máquina."""
    ips = []
    try:
        hostname = socket.gethostname()
        addr_infos = socket.getaddrinfo(hostname, None)
        for res in addr_infos:
            ip = res[4][0]
            # Excluir localhost y duplicados
            if ip not in ['127.0.0.1', '::1', '0.0.0.0'] and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
        
    # Intentar conexión ficticia como fallback para detectar la interfaz de salida activa
    for family, test_ip in [(socket.AF_INET, '8.8.8.8'), (socket.AF_INET6, '2001:4860:4860::8888')]:
        s = socket.socket(family, socket.SOCK_DGRAM)
        try:
            s.connect((test_ip, 1))
            ip = s.getsockname()[0]
            if ip not in ips and ip not in ['127.0.0.1', '::1', '0.0.0.0']:
                ips.append(ip)
        except Exception:
            pass
        finally:
            s.close()
            
    return ips

def resolve_path_safely(base_dir, relative_path):
    """
    Normaliza y resuelve una ruta relativa de forma segura y tolerante a mayúsculas/minúsculas.
    Evita directory traversal al validar que no suba del directorio base.
    """
    # Reemplazar barras invertidas (estilo Windows) por barras normales
    normalized_rel = relative_path.replace('\\', '/').strip('/')
    parts = normalized_rel.split('/')
    
    current_path = base_dir
    for part in parts:
        if not part or part == '.':
            continue
        if part == '..':
            return None, "directory_traversal"
            
        try:
            items = os.listdir(current_path)
        except OSError:
            return None, "not_found"
            
        # Buscar el archivo de forma insensible a mayúsculas/minúsculas
        match = None
        for item in items:
            if item.lower() == part.lower():
                match = item
                break
                
        if match is None:
            return None, "not_found"
            
        current_path = os.path.join(current_path, match)
        
    abs_path = os.path.abspath(current_path)
    if not abs_path.startswith(base_dir):
        return None, "directory_traversal"
        
    return abs_path, "ok"

def handle_client(client_socket, client_address):
    """Maneja la comunicación con un cliente conectado."""
    print(f"\n[CONEXIÓN] Cliente conectado desde {client_address[0]}:{client_address[1]}")
    
    try:
        while True:
            # Recibir la petición del cliente
            request = client_socket.recv(1024).decode('utf-8').strip()
            
            # Si no hay datos, el cliente se desconectó
            if not request:
                break
                
            print(f"[PETICIÓN] Cliente {client_address[0]}:{client_address[1]} solicitó: '{request}'")
            
            # Procesar el comando (se espera 'GET <ruta>')
            if request.startswith("GET "):
                filename = request[4:].strip()
                
                # Resolver la ruta de forma segura e insensible a mayúsculas/minúsculas
                res_path, status_code = resolve_path_safely(BASE_DIR, filename)
                
                if status_code == "directory_traversal":
                    response = "403 FORBIDDEN\nAcceso denegado. Intento de navegacion no autorizado."
                    print(f"[ADVERTENCIA] Intento de Directory Traversal de {client_address[0]}:{client_address[1]} con la ruta: '{filename}'")
                elif status_code == "not_found":
                    response = f"404 NOT FOUND\nEl archivo '{filename}' no fue encontrado en el servidor."
                    print(f"[NO ENCONTRADO] El archivo '{filename}' no existe.")
                else:
                    if os.path.isfile(res_path):
                        # Archivo encontrado, leer y enviar contenido
                        try:
                            with open(res_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            response = f"200 OK\n{content}"
                            print(f"[EXITO] Enviado archivo '{filename}' a {client_address[0]}:{client_address[1]}")
                        except Exception as e:
                            response = f"500 SERVER ERROR\nError al leer el archivo en el servidor: {str(e)}"
                            print(f"[ERROR] Error de lectura para '{filename}': {str(e)}")
                    else:
                        response = f"404 NOT FOUND\n'{filename}' no es un archivo valido."
                        print(f"[NO ENCONTRADO] '{filename}' es un directorio.")
            elif request == "CLOSE":
                # Petición de cierre ordenada
                print(f"[DESCONEXIÓN] Petición de cierre recibida de {client_address[0]}:{client_address[1]}")
                break
            else:
                response = "400 BAD REQUEST\nFormato de solicitud desconocido. Use 'GET <archivo>'."
                print(f"[BAD REQUEST] Petición inválida de {client_address[0]}:{client_address[1]}: '{request}'")
            
            # Enviar la respuesta al cliente
            client_socket.sendall(response.encode('utf-8'))
            
    except ConnectionResetError:
        print(f"\n[CONEXIÓN PERDIDA] El cliente {client_address[0]}:{client_address[1]} cerró abruptamente la conexión.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error con el cliente {client_address[0]}:{client_address[1]}: {str(e)}")
    finally:
        client_socket.close()
        print(f"[CONEXIÓN] Canal de comunicación cerrado para {client_address[0]}:{client_address[1]}")

def main():
    # Asegurarse de que el directorio base exista
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        print(f"[SISTEMA] Se ha creado el directorio base en: {BASE_DIR}")
        
    local_ips = get_local_ips()
    
    # Resolver BIND_IP para determinar la familia de socket adecuada (IPv4 o IPv6)
    try:
        addr_infos = socket.getaddrinfo(BIND_IP, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        af, socktype, proto, canonname, sa = addr_infos[0]
    except Exception as e:
        print(f"\n[ERROR CRITICO] No se pudo resolver BIND_IP '{BIND_IP}': {str(e)}")
        return
        
    # Crear socket de servidor TCP
    server_socket = socket.socket(af, socktype, proto)
    # Permitir reutilizar el puerto inmediatamente después de apagar el servidor
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Si es IPv6 y estamos escuchando en comodín (::), desactivamos IPV6_V6ONLY para dual-stack (IPv4/IPv6)
    if af == socket.AF_INET6 and (BIND_IP == "::" or sa[0] == "::"):
        try:
            server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except Exception:
            pass
            
    try:
        server_socket.bind(sa)
        server_socket.listen(5)
        print("=========================================================")
        print("         SERVIDOR WEB DE TEXTO INICIADO CON EXITO         ")
        print("=========================================================")
        print("Direcciones IP del servidor para conexiones externas:")
        if local_ips:
            for ip in local_ips:
                print(f"  -> {ip}")
        else:
            print("  -> (No se detectaron IPs externas activas)")
        print(f"Dirección IP local (Loopback):         " + ("localhost" if af == socket.AF_INET else "::1"))
        print(f"Puerto de escucha:                     {PORT}")
        print(f"Dirección de escucha configurada:      {BIND_IP}")
        print(f"Directorio de paginas:                 {BASE_DIR}")
        print("Esperando conexiones de clientes...\n")
        print("---------------------------------------------------------")
        
        while True:
            client_socket, client_address = server_socket.accept()
            # Iniciar un nuevo hilo por cada cliente conectado
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address),
                daemon=True
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\n[APAGADO] Servidor interrumpido por el usuario. Apagando...")
    except Exception as e:
        print(f"\n[ERROR CRITICO] No se pudo levantar el servidor: {str(e)}")
    finally:
        server_socket.close()
        print("[SISTEMA] Servidor apagado correctamente.")

if __name__ == '__main__':
    main()
