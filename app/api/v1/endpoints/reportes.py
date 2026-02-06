from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import date

from app.db.database import get_db
from app.db import models
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

# 3. DASHBOARD DE REPORTE DE CARTERA TOTAL (ADMINISTRADOR)
@router.get("/cartera-global", response_model=List[reporte_schema.CarteraGlobalResponse])
def ver_cartera_global(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) 
):
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")
    
    service = ReporteService(db)
    return service.obtener_cartera_global()

# 4. NUEVO: ESTADO DE RESULTADOS JERÁRQUICO (CONTABILIDAD)
@router.get("/estado-resultados", response_model=reporte_schema.EstadoResultadosResponse)
def reporte_estado_resultados_endpoint(
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Genera el reporte contable jerárquico (P&L).
    """
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    service = ReporteService(db)
    return service.obtener_estado_resultados(fecha_inicio, fecha_fin)


@router.get("/detalle-cuenta/{id_catalogo}", response_model=List[reporte_schema.DetalleMovimientoResponse])
def obtener_detalle_cuenta_endpoint(
    id_catalogo: int,
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Retorna el listado de movimientos de una cuenta específica en un rango de fechas.
    Usado para el drill-down del Estado de Resultados.
    """
    service = ReporteService(db)
    return service.obtener_detalle_cuenta(id_catalogo, fecha_inicio, fecha_fin)

# 6. NUEVO: ELABORACION REPORTE GENERACION LIBRO DIARIO
@router.get("/caja-movimientos/{id_medio}", response_model=reporte_schema.ReporteCajaResponse)
def obtener_reporte_caja(
    id_medio: int,
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user) # <-- Recomendable mantener seguridad
) -> Any:
    """
    Obtiene el reporte de movimientos de caja (Libro Diario) con saldo acumulado.
    """
    # Verificación de Rol (Opcional, pero recomendado)
    if current_user.rol.nombre not in ROLES_LECTURA:
         raise HTTPException(status_code=403, detail="Acceso denegado.")

    try:
        # 1. Instanciamos la clase (Igual que en los otros endpoints)
        service = ReporteService(db) 
        
        # 2. Llamamos al método usando la instancia 'service'
        reporte = service.generar_kardex_caja(
            id_medio=id_medio,
            fecha_inicio=str(fecha_inicio),
            fecha_fin=str(fecha_fin)
        )
        return reporte
        
    except Exception as e:
        print(f"Error generando reporte: {e}") 
        raise HTTPException(status_code=400, detail=str(e))