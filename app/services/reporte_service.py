# Archivo: app/services/reporte_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from fastapi import HTTPException
from datetime import datetime, date
from typing import List  # <--- Agregamos esto para el nuevo método

from app.db import models
from app.schemas import reporte_schema

class ReporteService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. ESTADO DE CUENTA INDIVIDUAL (TU CÓDIGO ORIGINAL - INTACTO)
    # -------------------------------------------------------------------------
    def obtener_estado_cuenta(self, id_persona: int) -> reporte_schema.EstadoCuentaResponse:
        # 1. Verificar Persona
        persona = self.db.query(models.Persona).filter(models.Persona.id_persona == id_persona).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")

        # A. CALCULAR BILLETERAS Y SALDOS A FAVOR
        relaciones = self.db.query(models.RelacionCliente).filter(
            models.RelacionCliente.id_persona == id_persona,
            models.RelacionCliente.estado == 'Activo'
        ).all()

        lista_billeteras = []
        total_saldo_favor = 0.0

        for rel in relaciones:
            nombre_unidad = rel.unidad.identificador_unico if rel.unidad else f"Unidad {rel.id_unidad}"
            saldo = float(rel.saldo_favor)
            
            lista_billeteras.append({
                "unidad": nombre_unidad,
                "tipo_relacion": rel.tipo_relacion,
                "saldo": saldo
            })
            total_saldo_favor += saldo

        # B. CALCULAR DEUDAS (Vencidas y Pendientes)
        items_pendientes = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.id_persona == id_persona,
            models.ItemFacturable.saldo_pendiente > 0.001,
            models.ItemFacturable.estado != 'cancelado'
        ).order_by(asc(models.ItemFacturable.fecha_vencimiento)).all()

        lista_deudas = []
        total_deuda_pendiente = 0.0
        total_deuda_vencida = 0.0
        hoy = date.today()

        for item in items_pendientes:
            saldo_item = float(item.saldo_pendiente)
            es_vencido = item.fecha_vencimiento < hoy

            lista_deudas.append(reporte_schema.ItemDeuda(
                periodo=item.periodo,
                concepto=item.concepto.nombre if item.concepto else "Concepto General",
                monto_base=float(item.monto_base),
                saldo_pendiente=saldo_item,
                fecha_vencimiento=item.fecha_vencimiento,
                estado="VENCIDO" if es_vencido else item.estado.upper()
            ))

            total_deuda_pendiente += saldo_item
            if es_vencido:
                total_deuda_vencida += saldo_item

        # C. HISTORIAL DE PAGOS (Últimos 10)
        ultimos_pagos_db = self.db.query(models.TransaccionIngreso).filter(
            models.TransaccionIngreso.id_usuario_creador == id_persona,
            models.TransaccionIngreso.estado != 'ANULADO'
        ).order_by(desc(models.TransaccionIngreso.fecha)).limit(10).all()
        
        lista_pagos = []
        for pago in ultimos_pagos_db:
            lista_pagos.append(reporte_schema.ItemPago(
                fecha=pago.fecha_creacion,
                monto_total=float(pago.monto_total),
                descripcion=pago.descripcion or "Pago de cuotas",
                num_documento=pago.num_documento,
                medio_pago=pago.medio_ingreso.nombre if pago.medio_ingreso else "Desconocido"
            ))

        # D. DETERMINAR ESTADO GENERAL (SEMÁFORO)
        estado_general = "Al día"
        if total_deuda_vencida > 0:
            estado_general = "Moroso"
        elif total_saldo_favor > 0 and total_deuda_pendiente == 0:
            estado_general = "Solvente (Saldo a Favor)"
        elif total_deuda_pendiente > 0:
             estado_general = "Con Deuda Corriente"

        # E. ARMAR LA RESPUESTA COMPLETA
        resumen_fin = reporte_schema.ResumenFinanciero(
            total_deuda_vencida=total_deuda_vencida,
            total_deuda_pendiente=total_deuda_pendiente,
            saldo_a_favor_disponible=total_saldo_favor,
            estado_general=estado_general
        )

        return reporte_schema.EstadoCuentaResponse(
            fecha_reporte=datetime.now(),
            id_persona=persona.id_persona,
            nombre_persona=f"{persona.nombres} {persona.apellidos}",
            resumen=resumen_fin,
            billeteras=lista_billeteras,
            deudas_pendientes=lista_deudas,
            ultimos_pagos=lista_pagos
        )

    # -------------------------------------------------------------------------
    # 2. REPORTE DE MOROSIDAD (NUEVO MÉTODO AGREGADO) 
    # -------------------------------------------------------------------------
    def obtener_lista_morosos(self) -> List[reporte_schema.MorosoResponse]:
        hoy = date.today()
        
        deudas_vencidas = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.saldo_pendiente > 0.01,
            models.ItemFacturable.fecha_vencimiento < hoy,
            models.ItemFacturable.estado != 'anulado',
            models.ItemFacturable.estado != 'cancelado'
        ).all()

        agrupado = {} 

        for item in deudas_vencidas:
            uid = item.id_unidad
            
            # 1. Obtenemos el valor (el string "2J")
            valor_identificador = item.unidad.identificador_unico if item.unidad else f"ID-{uid}"

            if uid not in agrupado:
                nombre_inquilino = "Desconocido"
                if item.persona:
                    nombre_inquilino = f"{item.persona.nombres} {item.persona.apellidos}"
                
                # 2. Creamos el objeto (AQUÍ ESTABA EL ERROR)
                agrupado[uid] = reporte_schema.MorosoResponse(
                    id_unidad=uid,
                    
                    # ❌ ANTES (Error): iden_unico = valor_identificador
                    # ✅ AHORA (Correcto): El nombre debe ser idéntico al Schema
                    identificador_unico = valor_identificador, 
                    
                    nombre_inquilino=nombre_inquilino,
                    total_deuda=0.0,
                    cantidad_meses=0,
                    detalles=[]
                )
            
            # ... resto del código igual (cálculo de días y acumuladores) ...
            dias_atraso = (hoy - item.fecha_vencimiento).days
            agrupado[uid].total_deuda += float(item.saldo_pendiente)
            agrupado[uid].cantidad_meses += 1
            
            agrupado[uid].detalles.append(reporte_schema.DetalleDeudaMoroso(
                periodo=item.periodo,
                concepto=item.concepto.nombre if item.concepto else "General",
                monto_pendiente=float(item.saldo_pendiente),
                dias_atraso=dias_atraso
            ))
            
        return list(agrupado.values())