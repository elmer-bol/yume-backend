from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models # Necesario para el usuario
from app.services.caja_service import CajaService
from app.schemas import caja_schema

# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA

router = APIRouter(
    prefix="/caja",
    tags=["Reportes y Control de Caja"]
)

@router.get("/balance", response_model=caja_schema.BalanceCaja)
def ver_balance_actual(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Arqueo rápido: ¿Cuánto dinero físico debe haber en el cajón?
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    servicio = CajaService(db)
    return servicio.calcular_balance()

@router.get("/libro-diario", response_model=caja_schema.ReporteLibroCaja)
def ver_libro_diario(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Reporte detallado cronológico de todos los movimientos de efectivo.
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    servicio = CajaService(db)
    return servicio.generar_libro_caja()