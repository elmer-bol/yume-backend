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
        # Ajusta el string dentro del ilike si tu BD dice "Efectivo/Caja"
        medio = self.db.query(models.MedioIngreso).filter(
            models.MedioIngreso.nombre.ilike("%Efectivo%") 
        ).first()
        return medio.id_medio_ingreso if medio else 0

    # -------------------------------------------------------------------------
    # 1. CÁLCULO DE SALDO (VALIDADOR)
    # -------------------------------------------------------------------------
    def calcular_balance(self) -> caja_schema.BalanceCaja:
        """
        Calcula: (Entradas Efectivo) - (Gastos) - (Depósitos Confirmados)
        """
        id_efectivo = self._get_id_efectivo()

        # A. SUMA INGRESOS (Solo efectivo y confirmados)
        total_ingresos = self.db.query(func.sum(models.TransaccionIngreso.monto_total)).filter(
            models.TransaccionIngreso.id_medio_ingreso == id_efectivo,
            models.TransaccionIngreso.estado == 'APLICADO'
        ).scalar() or 0.0

        # B. SUMA GASTOS (Solo activos)
        total_gastos = self.db.query(func.sum(models.Egreso.monto)).filter(
            models.Egreso.estado != 'cancelado'
        ).scalar() or 0.0

        # C. SUMA DEPÓSITOS (Dinero enviado al banco)
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
        """
        Método crítico para bloquear gastos sin fondos.
        """
        balance = self.calcular_balance()
        if balance.saldo_actual_en_caja < (monto_a_gastar - 0.01): # Pequeña tolerancia decimal
            raise HTTPException(
                status_code=400,
                detail=f"FONDOS INSUFICIENTES EN CAJA. Tienes {balance.saldo_actual_en_caja:.2f}, intentas usar {monto_a_gastar:.2f}."
            )
        return True

    # -------------------------------------------------------------------------
    # 2. GENERACIÓN DE REPORTE (LIBRO DIARIO)
    # -------------------------------------------------------------------------
    def generar_libro_caja(self) -> caja_schema.ReporteLibroCaja:
        """
        Mezcla las 3 tablas en una sola lista cronológica.
        """
        movimientos = []
        id_efectivo = self._get_id_efectivo()

        # A. OBTENER INGRESOS
        ingresos_db = self.db.query(models.TransaccionIngreso).filter(
            models.TransaccionIngreso.id_medio_ingreso == id_efectivo,
            models.TransaccionIngreso.estado == 'APLICADO'
        ).all()

        for i in ingresos_db:
            # Tratamos de obtener nombre del usuario creador
            responsable = i.usuario_creador.nombres if i.usuario_creador else f"User {i.id_usuario_creador}"
            movimientos.append(caja_schema.MovimientoCaja(
                fecha=i.fecha_creacion, # Usamos fecha exacta con hora
                tipo="INGRESO",
                descripcion=f"Recibo #{i.id_transaccion} - {i.descripcion or 'Sin descripción'}",
                monto_entrada=float(i.monto_total),
                monto_salida=0.0,
                referencia_id=i.id_transaccion,
                usuario_responsable=responsable
            ))

        # B. OBTENER GASTOS
        egresos_db = self.db.query(models.Egreso).filter(
            models.Egreso.estado != 'cancelado'
        ).all()

        for e in egresos_db:
            responsable = e.administrador.nombres if e.administrador else f"Admin {e.id_administrador}"
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
            responsable = d.administrador.nombres if d.administrador else f"Admin {d.id_administrador}"
            movimientos.append(caja_schema.MovimientoCaja(
                fecha=d.fecha_creacion,
                tipo="DEPOSITO",
                descripcion=f"Traslado a Banco #{d.num_referencia} ({d.banco})",
                monto_entrada=0.0,
                monto_salida=float(d.monto),
                referencia_id=d.id_deposito,
                usuario_responsable=responsable
            ))

        # D. ORDENAR CRONOLÓGICAMENTE
        # La magia de Python: ordenamos la lista mixta por fecha
        movimientos.sort(key=lambda x: x.fecha, reverse=True) # Del más reciente al más antiguo

        # E. OBTENER SALDO ACTUAL
        balance_actual = self.calcular_balance()

        return caja_schema.ReporteLibroCaja(
            saldo_actual=balance_actual.saldo_actual_en_caja,
            movimientos=movimientos
        )