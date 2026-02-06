# Archivo: app/services/caja_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime
from typing import List

from app.db import models
from app.schemas import caja_schema

class CajaService:
    def __init__(self, db: Session):
        self.db = db

    def _get_id_efectivo(self) -> int:
        """Helper para buscar el ID del medio de pago Efectivo."""
        # Ajusta el string si tu BD usa otro nombre
        medio = self.db.query(models.MedioIngreso).filter(
            models.MedioIngreso.nombre.ilike("%Efectivo%") 
        ).first()
        return medio.id_medio_ingreso if medio else 0

    # -------------------------------------------------------------------------
    # 1. CÁLCULO DE SALDO (VALIDADOR)
    # -------------------------------------------------------------------------
    def calcular_balance(self) -> caja_schema.BalanceCaja:
        id_efectivo = self._get_id_efectivo()

        # A. SUMA INGRESOS
        total_ingresos = self.db.query(func.sum(models.TransaccionIngreso.monto_total)).filter(
            models.TransaccionIngreso.id_medio_ingreso == id_efectivo,
            models.TransaccionIngreso.estado == 'APLICADO'
        ).scalar() or 0.0

        # B. SUMA GASTOS
        total_gastos = self.db.query(func.sum(models.Egreso.monto)).filter(
            models.Egreso.id_medio_pago == id_efectivo, # <--- Corregido para filtrar solo efectivo
            models.Egreso.estado != 'cancelado'
        ).scalar() or 0.0

        # C. SUMA DEPÓSITOS
        total_depositos = self.db.query(func.sum(models.Deposito.monto)).filter(
            models.Deposito.estado == 'confirmado'
        ).scalar() or 0.0

        # D. SALDO FINAL
        saldo = float(total_ingresos) - float(total_gastos) - float(total_depositos)

        return caja_schema.BalanceCaja(
            total_ingresos_efectivo=total_ingresos,
            total_gastos_realizados=total_gastos,
            total_depositos_bancarios=total_depositos,
            saldo_actual_en_caja=saldo,
            fecha_corte=datetime.now()
        )

    def validar_fondos_suficientes(self, monto_a_gastar: float):
        balance = self.calcular_balance()
        if balance.saldo_actual_en_caja < (monto_a_gastar - 0.01):
            raise HTTPException(
                status_code=400,
                detail=f"FONDOS INSUFICIENTES EN CAJA. Tienes {balance.saldo_actual_en_caja:.2f}, intentas usar {monto_a_gastar:.2f}."
            )
        return True

    # -------------------------------------------------------------------------
    # 2. GENERACIÓN DE REPORTE (LIBRO DIARIO) - ¡AQUÍ ESTABA EL ERROR!
    # -------------------------------------------------------------------------
    def generar_libro_caja(self) -> caja_schema.ReporteLibroCaja:
        movimientos = []
        id_efectivo = self._get_id_efectivo()

        # A. OBTENER INGRESOS
        ingresos_db = self.db.query(models.TransaccionIngreso).filter(
            models.TransaccionIngreso.id_medio_ingreso == id_efectivo,
            models.TransaccionIngreso.estado == 'APLICADO'
        ).all()

        for i in ingresos_db:
            # CORREGIDO: Accedemos a usuario_creador -> persona -> nombres
            responsable = "Sistema"
            if i.usuario_creador and i.usuario_creador.persona:
                p = i.usuario_creador.persona
                responsable = f"{p.nombres} {p.apellidos}"

            movimientos.append(caja_schema.MovimientoCaja(
                fecha=i.fecha_creacion,
                tipo="INGRESO",
                descripcion=f"Recibo #{i.id_transaccion} - {i.descripcion or 'Sin descripción'}",
                monto_entrada=float(i.monto_total),
                monto_salida=0.0,
                referencia_id=i.id_transaccion,
                usuario_responsable=responsable
            ))

        # B. OBTENER GASTOS
        egresos_db = self.db.query(models.Egreso).filter(
            models.Egreso.id_medio_pago == id_efectivo, # Filtramos solo gastos de efectivo
            models.Egreso.estado != 'cancelado'
        ).all()

        for e in egresos_db:
            # CORREGIDO: Cambiamos 'e.administrador' por 'e.usuario_creador'
            responsable = "Admin"
            if e.usuario_creador and e.usuario_creador.persona:
                p = e.usuario_creador.persona
                responsable = f"{p.nombres} {p.apellidos}"

            cat_nombre = e.catalogo.nombre_cuenta if e.catalogo else "General"
            
            movimientos.append(caja_schema.MovimientoCaja(
                fecha=e.fecha_creacion,
                tipo="GASTO",
                descripcion=f"Gasto #{e.id_egreso} ({cat_nombre}) - {e.beneficiario}",
                monto_entrada=0.0,
                monto_salida=float(e.monto),
                referencia_id=e.id_egreso,
                usuario_responsable=responsable
            ))

        # C. OBTENER DEPÓSITOS
        depositos_db = self.db.query(models.Deposito).filter(
            models.Deposito.estado == 'confirmado'
        ).all()

        for d in depositos_db:
            # CORREGIDO: Cambiamos 'd.administrador' por 'd.usuario_creador'
            responsable = "Tesoreria"
            if d.usuario_creador and d.usuario_creador.persona:
                p = d.usuario_creador.persona
                responsable = f"{p.nombres} {p.apellidos}"

            movimientos.append(caja_schema.MovimientoCaja(
                fecha=d.fecha_creacion,
                tipo="DEPOSITO",
                descripcion=f"Traslado a Banco #{d.num_referencia} ({d.banco})",
                monto_entrada=0.0,
                monto_salida=float(d.monto),
                referencia_id=d.id_deposito,
                usuario_responsable=responsable
            ))

        # D. ORDENAR Y RETORNAR
        movimientos.sort(key=lambda x: x.fecha, reverse=True)
        balance_actual = self.calcular_balance()

        return caja_schema.ReporteLibroCaja(
            saldo_actual=balance_actual.saldo_actual_en_caja,
            movimientos=movimientos
        )
    
    # -------------------------------------------------------------------------
    # 3. TRANSFERENCIA DE FONDOS
    # -------------------------------------------------------------------------
    def realizar_transferencia(self, datos: caja_schema.TransferenciaCreate, id_usuario: int):
        if datos.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
        if datos.id_medio_origen == datos.id_medio_destino:
            raise HTTPException(status_code=400, detail="El origen y destino no pueden ser iguales")

        cuenta_ingreso = self.db.query(models.Categoria).filter(models.Categoria.codigo == '4.9.9.99').first()
        cuenta_egreso  = self.db.query(models.Categoria).filter(models.Categoria.codigo == '5.9.9.99').first()

        if not cuenta_ingreso or not cuenta_egreso:
            raise HTTPException(status_code=500, detail="Faltan cuentas puente 4.9.9.99 y 5.9.9.99")

        tipo_egreso_gen = self.db.query(models.TipoEgreso).first()
        relacion_interna = self.db.query(models.RelacionCliente).filter(models.RelacionCliente.id_relacion == 113).first()
        if not relacion_interna:
             relacion_interna = self.db.query(models.RelacionCliente).first()

        try:
            nuevo_egreso = models.Egreso(
                id_tipo_egreso=tipo_egreso_gen.id_tipo_egreso if tipo_egreso_gen else 1,
                id_catalogo=cuenta_egreso.id_catalogo,
                id_medio_pago=datos.id_medio_origen,
                id_usuario_creador=id_usuario,
                monto=datos.monto,
                fecha=datos.fecha,
                beneficiario="TRANSFERENCIA INTERNA",
                descripcion=f"Salida hacia {datos.id_medio_destino}: {datos.descripcion}",
                estado='registrado'
            )
            self.db.add(nuevo_egreso)

            nuevo_ingreso = models.TransaccionIngreso(
                id_relacion=relacion_interna.id_relacion,
                id_usuario_creador=id_usuario,
                id_medio_ingreso=datos.id_medio_destino,
                id_catalogo=cuenta_ingreso.id_catalogo,
                monto_total=datos.monto,
                fecha=datos.fecha,
                num_documento="TRANSF-INT",
                descripcion=f"Entrada desde {datos.id_medio_origen}: {datos.descripcion}",
                estado='APLICADO'
            )
            self.db.add(nuevo_ingreso)

            self.db.commit()
            return {"mensaje": "Transferencia realizada con éxito", "monto": datos.monto}

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")