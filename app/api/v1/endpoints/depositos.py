from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.services.deposito_service import DepositoService
from app.schemas import deposito_schema
# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA, ROLES_ESCRITURA

router = APIRouter(
    prefix="/depositos",
    tags=["Gestión de Efectivo y Depósitos (Blindaje)"]
)

def get_deposito_service(db: Session = Depends(get_db)) -> DepositoService:
    return DepositoService(db)

# --------------------------------------------------------------------
# 1. GET: VER EFECTIVO PENDIENTE
# --------------------------------------------------------------------
@router.get("/pendientes", response_model=List[deposito_schema.TransaccionPendiente])
def ver_efectivo_pendiente(
    servicio: DepositoService = Depends(get_deposito_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Ver recibos en efectivo pendientes.
    Requiere: Estar logueado (Cualquier rol autorizado).
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.obtener_efectivo_pendiente()

# --------------------------------------------------------------------
# 2. POST: CERRAR CAJA (DEPÓSITO)
# --------------------------------------------------------------------
@router.post("/", response_model=deposito_schema.DepositoResponse, status_code=status.HTTP_201_CREATED)
def crear_deposito(
    deposito: deposito_schema.DepositoCreate,
    servicio: DepositoService = Depends(get_deposito_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Registra el depósito bancario.
    Requiere: Rol Operativo (Cajero, Admin).
    """
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para cerrar caja.")

    # Extraemos el ID del usuario del token
    user_id = current_user.id_usuario
    return servicio.crear_deposito_cierre(deposito, user_id)

# --------------------------------------------------------------------
# 3. GET: HISTORIAL
# --------------------------------------------------------------------
@router.get("/", response_model=List[deposito_schema.DepositoResponse])
def listar_historial_depositos(
    skip: int = 0, 
    limit: int = 100,
    servicio: DepositoService = Depends(get_deposito_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """Historial de cierres."""
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
         
    return servicio.get_depositos(skip=skip, limit=limit)