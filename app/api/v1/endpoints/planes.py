from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db import models
from app.schemas.plan_schema import PlanPagoCreate, PlanPagoResponse
from app.services import plan_service

# --- SEGURIDAD E IMPORTACIONES DEL NÚCLEO ---
from app.core.deps import get_current_user
from app.core.config import ROLES_ESCRITURA, ROLES_ADMIN

router = APIRouter(
    prefix="/planes",
    tags=["Gestión de Planes de Pago"]
)

# ----------------------------------------------------
# 1. CREACIÓN DE PLAN (POST /planes/crear)
# ----------------------------------------------------
@router.post("/crear", response_model=PlanPagoResponse, status_code=status.HTTP_201_CREATED)
def crear_nuevo_plan_endpoint(
    datos_plan: PlanPagoCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    """
    Crea un nuevo plan de pagos (Refinanciamiento).
    
    Reglas de Negocio:
    1. Requiere estar logueado.
    2. Requiere rol de ESCRITURA (Cajero o Admin).
    3. Registra el ID del usuario creador para auditoría.
    """
    
    # 1. SEGURIDAD (RBAC)
    # Validamos si el rol del usuario tiene permiso de escritura
    if current_user.rol.nombre not in ROLES_ESCRITURA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tiene permisos para autorizar planes de pago."
        )

    # 2. LÓGICA DE NEGOCIO
    # Invocamos al servicio pasando el ID real del usuario (extraído del Token JWT)
    try:
        nuevo_plan = plan_service.crear_plan_de_pagos(
            db=db, 
            datos=datos_plan, 
            user_id_creador=current_user.id_usuario
        )
        return nuevo_plan

    except HTTPException as he:
        # Si el servicio lanza una excepción HTTP (ej: items no encontrados), la dejamos pasar
        raise he
    except Exception as e:
        # Capturamos cualquier otro error inesperado
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error interno al procesar el plan: {str(e)}"
        )