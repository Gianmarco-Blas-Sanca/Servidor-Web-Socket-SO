import socket
import sys

# Puerto por defecto del servidor
PORT = 5000

def clean_input(prompt):
    """Obtiene una entrada limpia y controlada de la terminal."""
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSaliendo del navegador...")
        return "exit"

def parse_response(response_data):
    """Descompone la respuesta del servidor en estado y contenido."""
    lines = response_data.split('\n', 1)
    status = lines[0]
    content = lines[1] if len(lines) > 1 else ""
    return status, content

def main():
    print("=========================================================")
    print("        NAVEGADOR WEB DE TEXTO DE SISTEMAS OPERATIVOS     ")
    print("=========================================================")
    
    # Solicitar dirección IP del servidor
    server_ip = clean_input("Ingrese la IP del Servidor (Presione Enter para ::1): ")
    if not server_ip:
        server_ip = '::1'
        
    print(f"\n[SISTEMA] Conectando a [{server_ip}]:{PORT}...")
    
    # Crear socket de cliente (IPv6)
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, PORT))
        print("[SISTEMA] Conexión establecida con éxito.")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar al servidor: {str(e)}")
        sys.exit(1)
        
    # Estado del navegador local
    current_page = "index.txt"
    
    try:
        # Cargar la página index.txt inicialmente
        request = f"GET {current_page}"
        client_socket.sendall(request.encode('utf-8'))
        
        response = client_socket.recv(4096).decode('utf-8')
        status, content = parse_response(response)
        
        if status.startswith("200"):
            print("\n" + content)
        else:
            print(f"\n[ERROR DEL SERVIDOR] {status}")
            print(content)
            
        # Bucle de navegación interactivo
        while True:
            print("\n---------------------------------------------------------")
            user_input = clean_input("Navegar (nombre archivo, 'home' para inicio, 'exit' para salir) > ")
            
            # Normalizar entrada
            command = user_input.lower()
            
            if command in ['exit', 'end']:
                print("\n[SISTEMA] Cerrando la conexión con el servidor...")
                client_socket.sendall("CLOSE".encode('utf-8'))
                break
                
            elif command == 'home':
                target_page = "index.txt"
                
            elif user_input:
                # Si el usuario no ingresó la extensión .txt, la añadimos para su comodidad
                target_page = user_input
                if not target_page.lower().endswith('.txt'):
                    target_page += '.txt'
            else:
                continue
                
            # Enviar solicitud GET al servidor
            request = f"GET {target_page}"
            client_socket.sendall(request.encode('utf-8'))
            
            # Recibir la respuesta (soporta hasta 4KB de contenido de página)
            response = client_socket.recv(4096).decode('utf-8')
            status, content = parse_response(response)
            
            if status.startswith("200"):
                # Si la página se cargó con éxito, actualizamos la página actual
                current_page = target_page
                print(f"\n[PÁGINA ACTUAL: {current_page}]")
                print(content)
            else:
                # Si hubo un error, mostramos el error sin cambiar de página
                print(f"\n[ERROR - {status}]")
                print(content)
                print(f"[Navegación] Permaneces en la pagina: {current_page}")
                
    except ConnectionError:
        print("\n[ERROR CRITICO] Se perdió la conexion con el servidor.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error inesperado: {str(e)}")
    finally:
        client_socket.close()
        print("[SISTEMA] Sesion de navegacion terminada. ¡Hasta luego!")

if __name__ == '__main__':
    main()
