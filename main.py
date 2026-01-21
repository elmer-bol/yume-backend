# Archivo: app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importaciones de Endpoints
from app.api.v1.endpoints import (
    auth,
    medio_ingreso,
    categorias,
    conceptos,
    unidades,
    personas,
    relaciones,
    facturables,
    transacciones_ingreso,
    egresos,
    reportes,
    tipos_egreso,
    depositos,
    caja
)

# 1. Instancia principal
app = FastAPI(
    title="Sistema de Cobros Universal",
    description="API de gestión financiera basada en el modelo universal de cobros y egresos."
)

# 2. CONFIGURACIÓN DE CORS (¡AQUÍ ARRIBA!) 🛡️
# Definimos quién tiene permiso para hablar con el Backend
origins = [
    "http://localhost:3000",      # React (Create React App)
    "http://localhost:5173",      # React (Vite) - TU CASO ACTUAL
    "http://127.0.0.1:5173",      # React (Vite IP local)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permitir GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],  # Permitir Authorization, Content-Type, etc.
)

# 3. INCLUSIÓN DE RUTAS (DESPUÉS DEL MIDDLEWARE) 🛣️
app.include_router(auth.router, prefix="/v1") 
app.include_router(medio_ingreso.router, prefix="/v1")
app.include_router(categorias.router, prefix="/v1")
app.include_router(conceptos.router, prefix="/v1")
app.include_router(unidades.router, prefix="/v1")
app.include_router(personas.router, prefix="/v1")
app.include_router(relaciones.router, prefix="/v1")
app.include_router(facturables.router, prefix="/v1")
app.include_router(transacciones_ingreso.router, prefix="/v1")
app.include_router(egresos.router, prefix="/v1")
app.include_router(reportes.router, prefix="/v1")
app.include_router(tipos_egreso.router, prefix="/v1")
app.include_router(depositos.router, prefix="/v1")
app.include_router(caja.router, prefix="/v1")

@app.get("/")
def read_root():
    return {"message": "Bienvenido al Sistema de Cobros Universal (FastAPI)"}