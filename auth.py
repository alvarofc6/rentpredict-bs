import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path
from typing import Dict, Optional


BASE_DIR = Path(__file__).resolve().parent
RUTA_BD = BASE_DIR / "usuarios.db"

# Credenciales por defecto
USUARIO_DEFECTO = "admin"
CONTRASENA_DEFECTO = "admin123"
NOMBRE_DEFECTO = "Administrador"


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(RUTA_BD)
    conn.row_factory = sqlite3.Row
    return conn


def _generar_hash(contrasena: str, salt_hex: Optional[str] = None) -> str:
    """Genera un hash seguro usando PBKDF2-HMAC-SHA256 con salt aleatorio."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    clave = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{clave.hex()}"


def _verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    """Compara una contraseña en texto plano contra el hash almacenado."""
    try:
        salt_hex, _ = hash_guardado.split(":")
    except ValueError:
        return False
    hash_calculado = _generar_hash(contrasena, salt_hex)
    return hmac.compare_digest(hash_calculado, hash_guardado)


def inicializar_bd() -> None:
    """Crea las tablas de usuarios y sesiones e inserta la cuenta por defecto si no existe."""
    with _conectar() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                usuario TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sesiones (
                token TEXT PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
            """
        )

        # Crear cuenta por defecto si todavía no existe
        existe = conn.execute(
            "SELECT id FROM usuarios WHERE usuario = ?", (USUARIO_DEFECTO,)
        ).fetchone()
        if not existe:
            conn.execute(
                "INSERT INTO usuarios (nombre, usuario, password_hash) VALUES (?, ?, ?)",
                (NOMBRE_DEFECTO, USUARIO_DEFECTO, _generar_hash(CONTRASENA_DEFECTO)),
            )
        conn.commit()


def registrar_usuario(nombre: str, usuario: str, contrasena: str) -> Dict[str, str]:
    """Registra una nueva cuenta y devuelve sus datos básicos."""
    nombre_limpio = nombre.strip()
    usuario_limpio = usuario.strip().lower()

    if len(nombre_limpio) < 2:
        raise ValueError("El nombre debe tener al menos 2 caracteres.")
    if len(usuario_limpio) < 3 or " " in usuario_limpio:
        raise ValueError("El usuario debe tener al menos 3 caracteres y sin espacios.")
    if len(contrasena) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")

    password_hash = _generar_hash(contrasena)

    try:
        with _conectar() as conn:
            cursor = conn.execute(
                "INSERT INTO usuarios (nombre, usuario, password_hash) VALUES (?, ?, ?)",
                (nombre_limpio, usuario_limpio, password_hash),
            )
            conn.commit()
            usuario_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"El usuario '{usuario_limpio}' ya está registrado. Elige otro.") from exc

    token = _crear_sesion(usuario_id)
    return {
        "token": token,
        "usuario": usuario_limpio,
        "nombre": nombre_limpio,
    }


def iniciar_sesion(usuario: str, contrasena: str) -> Dict[str, str]:
    """Valida las credenciales y genera un token de sesión activo."""
    usuario_limpio = usuario.strip().lower()

    with _conectar() as conn:
        fila = conn.execute(
            "SELECT id, nombre, usuario, password_hash FROM usuarios WHERE usuario = ?",
            (usuario_limpio,),
        ).fetchone()

    if not fila or not _verificar_contrasena(contrasena, fila["password_hash"]):
        raise ValueError("Usuario o contraseña incorrectos.")

    token = _crear_sesion(fila["id"])
    return {
        "token": token,
        "usuario": fila["usuario"],
        "nombre": fila["nombre"],
    }


def _crear_sesion(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO sesiones (token, usuario_id) VALUES (?, ?)",
            (token, usuario_id),
        )
        conn.commit()
    return token


def validar_token(token: str) -> Optional[Dict[str, str]]:
    """Devuelve los datos del usuario si el token es válido, o None si expiró/no existe."""
    with _conectar() as conn:
        fila = conn.execute(
            """
            SELECT u.id, u.nombre, u.usuario
            FROM sesiones s
            INNER JOIN usuarios u ON s.usuario_id = u.id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()

    if not fila:
        return None
    return {"id": fila["id"], "nombre": fila["nombre"], "usuario": fila["usuario"]}


def cerrar_sesion(token: str) -> None:
    """Elimina el token de sesión de la base de datos."""
    with _conectar() as conn:
        conn.execute("DELETE FROM sesiones WHERE token = ?", (token,))
        conn.commit()