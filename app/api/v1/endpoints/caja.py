from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models # Necesario para el usuario
from app.services.caja_service import CajaService
from app.schemas import caja_schema

# SEGURIDAD
from app.core.deps import get_current_user
from app.core.config import ROLES_LECTURA
from app.schemas import caja_schema

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

@router.post("/transferencia", status_code=201)
def crear_transferencia_fondos(
    datos: caja_schema.TransferenciaCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Mueve dinero de una billetera a otra (Ej: Banco -> Caja Chica).
    Genera un Egreso y un Ingreso que se anulan contablemente pero mueven el saldo.
    """
    # Validamos permisos (Solo admins o tesoreros deberían poder mover plata)
    if current_user.rol.nombre not in ROLES_LECTURA:
        raise HTTPException(status_code=403, detail="No tienes permisos para transferir fondos.")

    servicio = CajaService(db)
    return servicio.realizar_transferencia(datos, current_user.id_usuario)