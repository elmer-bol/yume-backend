from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List 

from app.db.database import get_db
from app.db import models  # Necesario para el usuario
from app.schemas import reporte_schema
from app.services.reporte_service import ReporteService

# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes y Estados de Cuenta"]
)

# 1. ESTADO DE CUENTA INDIVIDUAL (CLIENTE)
@router.get("/estado-cuenta/{id_persona}", response_model=reporte_schema.EstadoCuentaResponse)
def obtener_estado_cuenta_endpoint(
    id_persona: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Obtiene la fotografía financiera completa de una persona.
    Requiere: Rol de Lectura (Cajero, Admin).
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    service = ReporteService(db)
    return service.obtener_estado_cuenta(id_persona)

# 2. DASHBOARD DE MOROSIDAD (ADMINISTRADOR)
@router.get("/morosidad", response_model=List[reporte_schema.MorosoResponse])
def obtener_dashboard_morosos_endpoint(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Devuelve la 'Lista Negra': Todos los inquilinos con deudas VENCIDAS.
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    service = ReporteService(db)
    return service.obtener_lista_morosos()