# Archivo: app/services/egreso_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
from typing import List

from app.db import models
from app.schemas import egreso_schema
from app.services.caja_service import CajaService

class EgresoService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. CREAR GASTO (SEGURIDAD APLICADA)
    # -------------------------------------------------------------------------
    def create_egreso(self, egreso_in: egreso_schema.EgresoCreate, id_usuario: int) -> egreso_schema.EgresoResponse: 
        try:
            # A. VALIDACIÓN CONTABLE
            catalogo = self.db.query(models.Categoria).filter(
                models.Categoria.id_catalogo == egreso_in.id_catalogo
            ).first()

            if not catalogo:
                raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")
            
            if catalogo.tipo != 'Egreso':
                raise HTTPException(
                    status_code=400, 
                    detail=f"La cuenta '{catalogo.nombre_cuenta}' es de INGRESO. No puedes registrar gastos aquí."
                )

            # B. VALIDACIÓN DE FONDOS
            servicio_caja = CajaService(self.db)
            servicio_caja.validar_fondos_suficientes(egreso_in.monto)

            # C. CREAR REGISTRO
            nuevo_egreso = models.Egreso(
                id_tipo_egreso=egreso_in.id_tipo_egreso,
                id_catalogo=egreso_in.id_catalogo,
                
                # SEGURIDAD: Usamos el ID del Token y la columna correcta de models.py
                id_usuario_creador=id_usuario, 
                
                monto=egreso_in.monto,
                fecha=egreso_in.fecha,
                beneficiario=egreso_in.beneficiario,
                num_comprobante=egreso_in.num_comprobante,
                descripcion=egreso_in.descripcion,
                estado='registrado'
            )

            self.db.add(nuevo_egreso)
            self.db.commit()
            self.db.refresh(nuevo_egreso)

            # D. RESPUESTA MANUAL (Para incluir nombres)
            return egreso_schema.EgresoResponse(
                id_egreso=nuevo_egreso.id_egreso,
                monto=float(nuevo_egreso.monto),
                fecha=nuevo_egreso.fecha,
                beneficiario=nuevo_egreso.beneficiario,
                num_comprobante=nuevo_egreso.num_comprobante,
                descripcion=nuevo_egreso.descripcion,
                estado=nuevo_egreso.estado,
                fecha_creacion=nuevo_egreso.fecha_creacion,
                
                nombre_cuenta=nuevo_egreso.catalogo.nombre_cuenta if nuevo_egreso.catalogo else "Desconocido",
                tipo_egreso=nuevo_egreso.tipo_egreso.nombre if nuevo_egreso.tipo_egreso else "Desconocido"
            )

        except HTTPException as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            print(f"Error interno: {e}") 
            raise HTTPException(status_code=500, detail=f"Error al registrar gasto: {str(e)}")

    # -------------------------------------------------------------------------
    # 2. LISTAR GASTOS
    # -------------------------------------------------------------------------
    def get_egresos(self, skip: int = 0, limit: int = 100):
        egresos = self.db.query(models.Egreso).order_by(desc(models.Egreso.fecha)).offset(skip).limit(limit).all()
        
        resultados = []
        for e in egresos:
            resp = egreso_schema.EgresoResponse.model_validate(e)
            if e.catalogo:
                resp.nombre_cuenta = e.catalogo.nombre_cuenta
            if e.tipo_egreso:
                resp.tipo_egreso = e.tipo_egreso.nombre
            resultados.append(resp)
            
        return resultados

    # -------------------------------------------------------------------------
    # 3. ANULAR GASTO
    # -------------------------------------------------------------------------
    def anular_egreso(self, id_egreso: int):
        egreso = self.db.query(models.Egreso).filter(models.Egreso.id_egreso == id_egreso).first()
        if not egreso:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")
            
        if egreso.estado == 'cancelado':
            raise HTTPException(status_code=400, detail="El gasto ya está anulado")
            
        egreso.estado = 'cancelado'
        self.db.commit()
        self.db.refresh(egreso)
        return egreso