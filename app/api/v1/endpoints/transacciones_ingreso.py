# Archivo: app/api/v1/endpoints/transacciones_ingreso.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.schemas import transaccion_ingreso_schema as schemas
from app.services.transaccion_ingreso_service import TransaccionIngresoService
from app.core.deps import get_current_user
# IMPORTAR LISTAS DE ROLES
from app.core.config import ROLES_LECTURA, ROLES_ESCRITURA, ROLES_ADMIN

def get_transaccion_ingreso_service(db: Session = Depends(get_db)) -> TransaccionIngresoService:
    return TransaccionIngresoService(db)
    
router = APIRouter(
    prefix="/transacciones-ingreso",
    tags=["Transacciones de Ingreso (Pagos Recibidos)"]
)

# ----------------------------------------------------
# 1. CREAR (POST) - Solo Escritura
# ----------------------------------------------------
@router.post("/", response_model=schemas.TransaccionIngreso, status_code=status.HTTP_201_CREATED)
def create_transaccion_endpoint(
    transaccion: schemas.TransaccionIngresoCreate, 
    servicio: TransaccionIngresoService = Depends(get_transaccion_ingreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Registrar un nuevo cobro.
    Seguridad: Requiere ROLES_ESCRITURA.
    """
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para registrar cobros.")

    # Extraemos el ID real del token y lo pasamos al servicio
    user_id = current_user.id_usuario
    return servicio.create_transaccion(transaccion, user_id)

# ----------------------------------------------------
# 2. LISTAR (GET) - Solo Lectura
# ----------------------------------------------------
@router.get("/", response_model=List[schemas.TransaccionIngreso])
def read_transacciones_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    servicio: TransaccionIngresoService = Depends(get_transaccion_ingreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="No tiene acceso a este módulo.")

    return servicio.get_transacciones(skip=skip, limit=limit)

# ----------------------------------------------------
# 3. SIMULAR (GET) - Lectura
# ----------------------------------------------------
@router.get("/simular", response_model=schemas.ResultadoSimulacionIngreso)
def simular_distribucion_endpoint(
    id_persona: int = Query(...),
    id_unidad: int = Query(...),
    monto: float = Query(...),
    monto_cuota_mensual: float = Query(0.0),
    servicio: TransaccionIngresoService = Depends(get_transaccion_ingreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Calculadora de deuda. Solo lectura."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="No tiene acceso a simulaciones.")

    return servicio.simular_ingreso(id_persona, id_unidad, monto, monto_cuota_mensual)

# ----------------------------------------------------
# 4. LEER POR ID (GET) - Lectura
# ----------------------------------------------------
@router.get("/{transaccion_id}", response_model=schemas.TransaccionIngreso)
def read_transaccion_by_id_endpoint(
    transaccion_id: int, 
    servicio: TransaccionIngresoService = Depends(get_transaccion_ingreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="No tiene acceso.")

    db_transaccion = servicio.get_transaccion_by_id(transaccion_id=transaccion_id)
    if db_transaccion is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return db_transaccion

# ----------------------------------------------------
# 5. ANULAR (PATCH) - Solo Admins
# ----------------------------------------------------
@router.patch("/anular/{transaccion_id}", response_model=schemas.TransaccionIngreso)
def anular_transaccion_ingreso_endpoint(
    transaccion_id: int,
    servicio: TransaccionIngresoService = Depends(get_transaccion_ingreso_service),
    current_user: models.Usuario = Depends(get_current_user) 
):
    """
    Anulación de cobro.
    Seguridad: Requiere ROLES_ADMIN.
    """
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Se requiere nivel administrativo para anular.")

    return servicio.anular_transaccion(transaccion_id, current_user.id_usuario) 

# ----------------------------------------------------
# 6. BORRAR (DELETE) - Solo Admins
# ----------------------------------------------------
@router.delete("/{transaccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaccion_ingreso_endpoint(
    transaccion_id: int,
    servicio: TransaccionIngresoService = Depends(get_transaccion_ingreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    if current_user.rol.nombre not in ROLES_ADMIN:
         raise HTTPException(status_code=403, detail="Se requiere nivel administrativo para borrar.")

    servicio.delete_transaccion(transaccion_id)