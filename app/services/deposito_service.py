from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
from typing import List

from app.db import models
from app.schemas import deposito_schema

class DepositoService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. VER CAJA PENDIENTE
    # -------------------------------------------------------------------------
    def obtener_efectivo_pendiente(self) -> List[deposito_schema.TransaccionPendiente]:
        """
        Busca transacciones en EFECTIVO que no tienen depósito.
        """
        # 1. Identificar el medio de pago "Efectivo"
        medio_efectivo = self.db.query(models.MedioIngreso).filter(
            models.MedioIngreso.nombre.ilike("Efectivo") 
        ).first()
        
        if not medio_efectivo:
            return [] 

        # 2. Buscar transacciones "sueltas"
        pendientes_db = self.db.query(models.TransaccionIngreso).filter(
            models.TransaccionIngreso.id_medio_ingreso == medio_efectivo.id_medio_ingreso,
            models.TransaccionIngreso.id_deposito == None, 
            models.TransaccionIngreso.estado != 'ANULADO'
        ).order_by(models.TransaccionIngreso.fecha.asc()).all()
        
        # 3. Formatear para el frontend
        resultado = []
        for trx in pendientes_db:
            pagador = "Desconocido"
            if trx.detalles:
                item = trx.detalles[0].item_facturable
                if item and item.persona:
                    pagador = f"{item.persona.nombres} {item.persona.apellidos}"
            
            resultado.append(deposito_schema.TransaccionPendiente(
                id_transaccion=trx.id_transaccion,
                fecha=trx.fecha,
                monto_total=float(trx.monto_total),
                descripcion=trx.descripcion,
                nombre_pagador=pagador
            ))
            
        return resultado

    # -------------------------------------------------------------------------
    # 2. REGISTRAR DEPÓSITO (BLINDADO)
    # -------------------------------------------------------------------------
    # MODIFICADO: Agregamos id_usuario como argumento
    def crear_deposito_cierre(self, datos: deposito_schema.DepositoCreate, id_usuario: int) -> models.Deposito:
        try:
            # A. Validar Transacciones
            transacciones = self.db.query(models.TransaccionIngreso).filter(
                models.TransaccionIngreso.id_transaccion.in_(datos.transacciones_ids)
            ).all()

            if len(transacciones) != len(datos.transacciones_ids):
                raise HTTPException(status_code=400, detail="Alguna transacción seleccionada no existe.")

            suma_total_sistema = 0.0

            for trx in transacciones:
                if trx.id_deposito is not None:
                    raise HTTPException(status_code=400, detail=f"Recibo #{trx.id_transaccion} ya fue depositado antes.")
                
                if trx.estado == 'ANULADO':
                    raise HTTPException(status_code=400, detail=f"Recibo #{trx.id_transaccion} está anulado.")
                
                suma_total_sistema += float(trx.monto_total)

            # B. Cuadre de Caja (Tolerancia 0.10)
            diff = abs(float(datos.monto) - suma_total_sistema)
            if diff > 0.10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error de Cuadre: Seleccionaste recibos por {suma_total_sistema}, pero el voucher es por {datos.monto}."
                )

            # C. Crear Depósito
            nuevo_deposito = models.Deposito(
                monto=datos.monto,
                fecha=datos.fecha,
                num_referencia=datos.num_referencia,
                
                # SEGURIDAD: Usamos el ID del Token
                id_administrador=id_usuario,
                
                banco=datos.banco,
                cuenta_destino=datos.cuenta_destino,
                estado='confirmado'
            )
            self.db.add(nuevo_deposito)
            self.db.flush() 

            # D. Vincular (Sellado)
            for trx in transacciones:
                trx.id_deposito = nuevo_deposito.id_deposito
                self.db.add(trx)

            self.db.commit()
            self.db.refresh(nuevo_deposito)
            return nuevo_deposito

        except HTTPException as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error al depositar: {str(e)}")

    # -------------------------------------------------------------------------
    # 3. HISTORIAL
    # -------------------------------------------------------------------------
    def get_depositos(self, skip: int = 0, limit: int = 100):
        return self.db.query(models.Deposito).order_by(desc(models.Deposito.fecha)).offset(skip).limit(limit).all()