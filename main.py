import io
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import (
    CONTRASENA_DEFECTO,
    USUARIO_DEFECTO,
    cerrar_sesion,
    inicializar_bd,
    iniciar_sesion,
    registrar_usuario,
    validar_token,
)
from modelo_lineal import ModeloAlquilerLineal


BASE_DIR = Path(__file__).resolve().parent
RUTA_CSV_DEFECTO = BASE_DIR / "alquileres.csv"

modelo = ModeloAlquilerLineal()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Inicializa la base de datos de usuarios y carga alquileres.csv al arrancar."""
    inicializar_bd()
    print(f"[OK] Base de datos lista. Credencial por defecto -> usuario: '{USUARIO_DEFECTO}' | clave: '{CONTRASENA_DEFECTO}'")

    if RUTA_CSV_DEFECTO.exists():
        try:
            df = pd.read_csv(RUTA_CSV_DEFECTO)
            modelo.entrenar_desde_dataframe(df, nombre_archivo=RUTA_CSV_DEFECTO.name)
            print(f"[OK] Modelo entrenado al inicio con '{RUTA_CSV_DEFECTO.name}' ({len(df)} registros).")
        except Exception as exc:
            print(f"[ADVERTENCIA] No se pudo cargar '{RUTA_CSV_DEFECTO.name}': {exc}")
    else:
        print("[AVISO] No se encontró 'alquileres.csv'. Ejecuta 'python generar_datos.py' o sube un CSV en la web.")
    yield


app = FastAPI(
    title="Sistema de Predicción de Alquileres (Bs)",
    description="Regresión Lineal Múltiple mediante Ecuación Normal con FastAPI, NumPy y autenticación.",
    version="1.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ==================== ESQUEMAS PYDANTIC ====================

class SolicitudLogin(BaseModel):
    usuario: str = Field(..., min_length=1)
    contrasena: str = Field(..., min_length=1)


class SolicitudRegistro(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=80)
    usuario: str = Field(..., min_length=3, max_length=40)
    contrasena: str = Field(..., min_length=4, max_length=100)


class DatosInmueble(BaseModel):
    superficie_m2: float = Field(..., gt=0, le=2000, description="Superficie habitable en m²")
    habitaciones: int = Field(..., ge=1, le=20, description="Número de habitaciones")
    antiguedad_anios: float = Field(..., ge=0, le=150, description="Antigüedad del inmueble en años")
    distancia_centro_km: float = Field(..., ge=0, le=100, description="Distancia al centro o avenida en km")


# ==================== DEPENDENCIA DE AUTENTICACIÓN ====================

def obtener_usuario_actual(authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Debes iniciar sesión para acceder al sistema.")
    token = authorization.removeprefix("Bearer ").strip()
    usuario = validar_token(token)
    if not usuario:
        raise HTTPException(status_code=401, detail="Tu sesión ha expirado o no es válida.")
    return {**usuario, "token": token}


# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.post("/api/auth/login")
async def login(datos: SolicitudLogin):
    try:
        return iniciar_sesion(datos.usuario, datos.contrasena)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.post("/api/auth/registro")
async def registro(datos: SolicitudRegistro):
    try:
        return registrar_usuario(datos.nombre, datos.usuario, datos.contrasena)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auth/me")
async def perfil_actual(usuario_actual: Dict[str, str] = Depends(obtener_usuario_actual)):
    return {
        "nombre": usuario_actual["nombre"],
        "usuario": usuario_actual["usuario"],
    }


@app.post("/api/auth/logout")
async def logout(usuario_actual: Dict[str, str] = Depends(obtener_usuario_actual)):
    cerrar_sesion(usuario_actual["token"])
    return {"mensaje": "Sesión cerrada correctamente."}


# ==================== RUTAS DEL SISTEMA ====================

@app.get("/", include_in_schema=False)
async def servir_inicio():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/analisis")
async def obtener_analisis(_usuario: Dict[str, str] = Depends(obtener_usuario_actual)):
    if not modelo.entrenado:
        raise HTTPException(
            status_code=400,
            detail="No hay ningún conjunto de datos cargado. Ejecuta generar_datos.py o sube un archivo CSV.",
        )
    return modelo.obtener_analisis_completo()


@app.post("/api/cargar-csv")
async def cargar_csv(
    file: UploadFile = File(...),
    _usuario: Dict[str, str] = Depends(obtener_usuario_actual),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Por favor sube un archivo con extensión .csv válida.")

    try:
        contenido = await file.read()
        df = pd.read_csv(io.BytesIO(contenido))
        modelo.entrenar_desde_dataframe(df, nombre_archivo=file.filename)
        return modelo.obtener_analisis_completo()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo procesar el archivo CSV: {exc}") from exc


@app.post("/api/predecir")
async def predecir_alquiler(
    datos: DatosInmueble,
    _usuario: Dict[str, str] = Depends(obtener_usuario_actual),
):
    if not modelo.entrenado:
        raise HTTPException(
            status_code=400,
            detail="El modelo no está entrenado. Carga primero un archivo CSV válido.",
        )
    try:
        return modelo.predecir(
            superficie_m2=datos.superficie_m2,
            habitaciones=datos.habitaciones,
            antiguedad_anios=datos.antiguedad_anios,
            distancia_centro_km=datos.distancia_centro_km,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al calcular la predicción: {exc}") from exc