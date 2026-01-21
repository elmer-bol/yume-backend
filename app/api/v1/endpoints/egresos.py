from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.services.egreso_service import EgresoService
from app.schemas import egreso_schema
from app.core.deps import get_current_user
# IMPORTAMOS LAS LISTAS DE PODER
from app.core.config import ROLES_ADMIN, ROLES_ESCRITURA, ROLES_LECTURA

router = APIRouter(
    prefix="/egresos",
    tags=["Gestión de Gastos y Salidas"]
)

def get_egreso_service(db: Session = Depends(get_db)) -> EgresoService:
    return EgresoService(db)

# 1. Crear Gasto
@router.post("/", response_model=egreso_schema.EgresoResponse, status_code=status.HTTP_201_CREATED)
def registrar_gasto(
    egreso: egreso_schema.EgresoCreate,
    servicio: EgresoService = Depends(get_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Validación de Escritura (Opcional, pero recomendada para consistencia)
    if current_user.rol.nombre not in ROLES_ESCRITURA:
         raise HTTPException(status_code=403, detail="No tiene permisos para registrar gastos.")

    user_id = current_user.id_usuario
    return servicio.create_egreso(egreso, user_id)

# 2. Listar Gastos
@router.get("/", response_model=List[egreso_schema.EgresoResponse])
def listar_gastos(
    skip: int = 0, 
    limit: int = 100,
    servicio: EgresoService = Depends(get_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    # Validación de Lectura
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="No tiene acceso a este módulo.")

    return servicio.get_egresos(skip=skip, limit=limit)

# 3. Anular Gasto (DINÁMICO)
@router.delete("/{id_egreso}", response_model=egreso_schema.EgresoResponse)
def anular_gasto(
    id_egreso: int,
    servicio: EgresoService = Depends(get_egreso_service),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Anula un gasto.
    Seguridad: Validación contra la lista ROLES_ADMIN (SuperAdmin, AdminEdif).
    """
    # AQUI ESTA EL CAMBIO CLAVE
    if current_user.rol.nombre not in ROLES_ADMIN:
        raise HTTPException(
            status_code=403, 
            detail="Permisos insuficientes. Se requiere nivel Administrativo."
        )

    return servicio.anular_egreso(id_egreso)