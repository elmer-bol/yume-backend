# Archivo: app/services/egreso_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from fastapi import HTTPException
from typing import List
from decimal import Decimal # <--- IMPORTANTE

from app.db import models
from app.schemas import egreso_schema

class EgresoService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # MÉTODO AUXILIAR: CALCULAR SALDO REAL (LIQUIDEZ)
    # -------------------------------------------------------------------------
    def _calcular_saldo_billetera(self, id_medio: int) -> float:
        """
        Calcula el dinero real disponible usando Tipos Decimales para evitar errores.
        """
        
        # 1. TOTAL ENTRADAS
        # Usamos Decimal(0) como valor por defecto, no 0.0
        total_entradas = self.db.query(func.sum(models.TransaccionIngreso.monto_total)).filter(
            models.TransaccionIngreso.id_medio_ingreso == id_medio,
            models.TransaccionIngreso.estado != 'ANULADO'
        ).scalar() or Decimal(0)

        # 2. TOTAL SALIDAS
        total_salidas = self.db.query(func.sum(models.Egreso.monto)).filter(
            models.Egreso.id_medio_pago == id_medio,
            models.Egreso.estado != 'cancelado' 
        ).scalar() or Decimal(0)

        # Ahora la resta es Decimal - Decimal (Seguro)
        saldo_final = total_entradas - total_salidas
        
        return float(saldo_final)

    # -------------------------------------------------------------------------
    # 1. CREAR GASTO
    # -------------------------------------------------------------------------
    def create_egreso(self, egreso_in: egreso_schema.EgresoCreate, id_usuario: int) -> models.Egreso: 
        try:
            # A. VALIDACIÓN CUENTA DE GASTO (DESTINO)
            cuenta_gasto = self.db.query(models.Categoria).filter(
                models.Categoria.id_catalogo == egreso_in.id_catalogo
            ).first()

            if not cuenta_gasto:
                raise HTTPException(status_code=404, detail="Cuenta contable de gasto no encontrada.")
            
            if cuenta_gasto.tipo != 'EGRESO' and not str(cuenta_gasto.codigo).startswith('5'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"La cuenta '{cuenta_gasto.nombre_cuenta}' NO es de Gasto. Verifique el catálogo."
                )

            # B. VALIDACIÓN DE BILLETERA (ORIGEN)
            billetera = self.db.query(models.MedioIngreso).filter(
                models.MedioIngreso.id_medio_ingreso == egreso_in.id_medio_pago
            ).first()

            if not billetera:
                raise HTTPException(status_code=404, detail="Medio de pago (Billetera) no encontrado.")

            # --- REGLA 1: LÍMITE DE POLÍTICA (Tope por transacción) ---
            if billetera.limite_maximo and billetera.limite_maximo > 0:
                if egreso_in.monto > billetera.limite_maximo:
                    raise HTTPException(
                        status_code=400,
                        detail=f"⚠️ EXCESO DE LÍMITE: La '{billetera.nombre}' solo permite pagos hasta {billetera.limite_maximo} Bs."
                    )
            
            # --- REGLA 2: LÍMITE DE LIQUIDEZ (Saldo Real) ---
            saldo_actual = self._calcular_saldo_billetera(egreso_in.id_medio_pago)
            
            # Convertimos egreso_in.monto a float para comparar con saldo_actual (que ya devolvimos como float)
            monto_float = float(egreso_in.monto)

            if saldo_actual < monto_float:
                raise HTTPException(
                    status_code=400,
                    detail=f"🚫 SALDO INSUFICIENTE en '{billetera.nombre}'. Tienes Bs {saldo_actual:.2f}, pero intentas gastar Bs {monto_float:.2f}."
                )

            # C. CREAR EL ASIENTO
            nuevo_egreso = models.Egreso(
                id_tipo_egreso=egreso_in.id_tipo_egreso,
                id_catalogo=egreso_in.id_catalogo,       # DEBE
                id_medio_pago=egreso_in.id_medio_pago,   # HABER
                
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

            return nuevo_egreso

        except HTTPException as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            print(f"Error interno Egreso: {e}") 
            raise HTTPException(status_code=500, detail=f"Error al registrar gasto: {str(e)}")

    # -------------------------------------------------------------------------
    # 2. LISTAR GASTOS
    # -------------------------------------------------------------------------
    def get_egresos(self, skip: int = 0, limit: int = 100) -> List[models.Egreso]:
        return self.db.query(models.Egreso)\
            .order_by(desc(models.Egreso.fecha))\
            .offset(skip).limit(limit).all()

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