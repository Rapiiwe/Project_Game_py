import socket
import pickle
import threading

from .constants import HOST, PORT

# Shared state (module-level, mutated by both game loop and network threads)
is_host = False
online_mode = False
online_connected = False
network_status = ""

conn = None
client_socket = None

network_data: dict = {
    "x": 0, "y": 0,
    "health": 100, "max_health": 100,
    "ship_index": 0,
    "bullets": [],
    "game_state": {}
}

enemy_network_data: dict = {
    "x": 0, "y": 0,
    "health": 100, "max_health": 100,
    "ship_index": 0,
    "bullets": [],
    "game_state": {}
}


def reset_network():
    """Call before starting a new game session."""
    global is_host, online_mode, online_connected, network_status
    global conn, client_socket
    is_host = False
    online_mode = False
    online_connected = False
    network_status = ""
    conn = None
    client_socket = None
    network_data.update({"x": 0, "y": 0, "health": 100, "max_health": 100,
                        "ship_index": 0, "bullets": [], "game_state": {}})
    enemy_network_data.update({"x": 0, "y": 0, "health": 100, "max_health": 100,
                                "ship_index": 0, "bullets": [], "game_state": {}})


def host_server():
    global conn, online_mode, online_connected, network_status

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.settimeout(0.25)

        network_status = "Menunggu player 2 join..."
        print("Menunggu player masuk...")

        while online_mode:
            try:
                conn, addr = server.accept()
                break
            except socket.timeout:
                continue
        else:
            network_status = ""
            server.close()
            return

        online_connected = True
        network_status = f"Player 2 connected: {addr[0]}"
    except Exception:
        online_connected = False
        network_status = "Gagal membuat host server"
        return

    print("Player connected:", addr)

    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            received = pickle.loads(data)
            enemy_network_data.update({
                "x":          received.get("x",          enemy_network_data["x"]),
                "y":          received.get("y",          enemy_network_data["y"]),
                "health":     received.get("health",     enemy_network_data["health"]),
                "max_health": received.get("max_health", enemy_network_data["max_health"]),
                "ship_index": received.get("ship_index", enemy_network_data["ship_index"]),
                "bullets":    received.get("bullets",    []),
                "game_state": received.get("game_state", enemy_network_data["game_state"]),
            })
            conn.send(pickle.dumps(network_data))
        except Exception:
            break

    online_connected = False
    network_status = "Koneksi player 2 terputus"
    server.close()


def connect_to_server(ip):
    global client_socket, online_connected, network_status

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(6)
    network_status = "Menghubungkan ke host..."
    try:
        client_socket.connect((ip, PORT))
    except Exception:
        network_status = "Gagal terhubung ke host"
        return

    client_socket.settimeout(None)
    online_connected = True
    network_status = "Terhubung ke host"

    while True:
        try:
            client_socket.send(pickle.dumps(network_data))
            data = client_socket.recv(4096)
            if not data:
                break
            received = pickle.loads(data)
            enemy_network_data.update({
                "x":          received.get("x",          enemy_network_data["x"]),
                "y":          received.get("y",          enemy_network_data["y"]),
                "health":     received.get("health",     enemy_network_data["health"]),
                "max_health": received.get("max_health", enemy_network_data["max_health"]),
                "ship_index": received.get("ship_index", enemy_network_data["ship_index"]),
                "bullets":    received.get("bullets",    []),
                "game_state": received.get("game_state", enemy_network_data["game_state"]),
            })
        except Exception:
            break

    online_connected = False
    network_status = "Koneksi host terputus"


def start_host_thread():
    threading.Thread(target=host_server, daemon=True).start()


def start_join_thread(ip):
    threading.Thread(target=connect_to_server, args=(ip,), daemon=True).start()
