# Archivo: app/services/transaccion_ingreso_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime, date

from app.db import models
from app.db.models import (
    TransaccionIngreso, 
    RelacionCliente, 
    ItemFacturable,
    MedioIngreso
)

from app.schemas.transaccion_ingreso_schema import (
    TransaccionIngresoCreate, 
    ResultadoSimulacionIngreso,
    DetalleSimulacion
)

class TransaccionIngresoService:
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------------
    def _get_transaccion_or_404(self, transaccion_id: int) -> models.TransaccionIngreso:
        db_transaccion = self.db.query(models.TransaccionIngreso).filter(
            models.TransaccionIngreso.id_transaccion == transaccion_id
        ).first()
        
        if not db_transaccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Transacción {transaccion_id} no encontrada."
            )
        return db_transaccion

    def _get_item_facturable(self, item_id: int) -> Optional[models.ItemFacturable]:
        return self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.id_item == item_id
        ).first()

    # ----------------------------------------------------------------------
    # 1. SIMULADOR (Sin Cambios Lógicos)
    # ----------------------------------------------------------------------
    def simular_ingreso(self, id_persona: int, id_unidad: int, monto_total: float, monto_cuota_futura_manual: float = 0) -> ResultadoSimulacionIngreso:
        relacion_cliente = self.db.query(RelacionCliente).filter(
            RelacionCliente.id_persona == id_persona,
            RelacionCliente.id_unidad == id_unidad,
            RelacionCliente.estado == 'Activo'
        ).first()

        if not relacion_cliente:
             raise HTTPException(status_code=404, detail="No existe contrato activo para simular.")

        costo_mensual_proyeccion = float(relacion_cliente.monto_mensual) if relacion_cliente.monto_mensual else 0.0
        if costo_mensual_proyeccion <= 0:
            costo_mensual_proyeccion = monto_cuota_futura_manual

        detalles_simulados = []
        dinero_disponible = monto_total
        dinero_gastado = 0.0

        # FASE 1: DEUDAS VIEJAS
        deudas = self.db.query(ItemFacturable).filter(
            ItemFacturable.id_persona == id_persona,
            ItemFacturable.id_unidad == id_unidad,
            ItemFacturable.saldo_pendiente > 0.001,
            ItemFacturable.estado != 'cancelado',
            ItemFacturable.estado != 'anulado'
        ).order_by(asc(ItemFacturable.fecha_vencimiento)).all()
        
        ultimo_anio_conocido = None
        ultimo_mes_conocido = None
        
        for deuda in deudas:
            ultimo_anio_conocido = deuda.año
            ultimo_mes_conocido = deuda.mes
            
            if dinero_disponible <= 0.001: break
            
            saldo_actual = float(deuda.saldo_pendiente)
            monto_a_aplicar = min(saldo_actual, dinero_disponible)
            nuevo_saldo = saldo_actual - monto_a_aplicar
            
            detalles_simulados.append(DetalleSimulacion(
                id_item_facturable=deuda.id_item,
                periodo=f"{deuda.periodo} (Existente)",
                monto_aplicado=round(monto_a_aplicar, 2),
                saldo_restante_deuda=round(nuevo_saldo, 2)
            ))
            
            dinero_disponible -= monto_a_aplicar
            dinero_gastado += monto_a_aplicar

        # FASE 2: PROYECCIÓN
        if dinero_disponible > 0.001:
            if ultimo_anio_conocido and ultimo_mes_conocido:
                anio_cursor = ultimo_anio_conocido
                mes_cursor = ultimo_mes_conocido
            else:
                hoy = datetime.now()
                anio_cursor = hoy.year
                mes_cursor = hoy.month
            
            while dinero_disponible > 0.001:
                if costo_mensual_proyeccion <= 0: break

                mes_cursor += 1
                if mes_cursor > 12:
                    mes_cursor = 1
                    anio_cursor += 1
                
                periodo_str = f"{anio_cursor}-{mes_cursor:02d}"
                monto_a_aplicar_futuro = min(dinero_disponible, costo_mensual_proyeccion)
                saldo_restante_simulado = costo_mensual_proyeccion - monto_a_aplicar_futuro

                detalles_simulados.append(DetalleSimulacion(
                    id_item_facturable=0, 
                    periodo=f"{periodo_str} (Futuro Nuevo)",
                    monto_aplicado=round(monto_a_aplicar_futuro, 2),
                    saldo_restante_deuda=round(saldo_restante_simulado, 2)
                ))

                dinero_disponible -= monto_a_aplicar_futuro
                dinero_gastado += monto_a_aplicar_futuro

        remanente_real = monto_total - dinero_gastado

        return ResultadoSimulacionIngreso(
            monto_total_ingresado=monto_total,
            monto_usado_en_deudas=round(dinero_gastado, 2),
            monto_remanente_billetera=round(remanente_real, 2),
            detalles_sugeridos=detalles_simulados
        )
    
    # ----------------------------------------------------------------------
    # 2. CREACIÓN (SEGURIDAD APLICADA)
    # ----------------------------------------------------------------------
    def create_transaccion(self, transaccion: TransaccionIngresoCreate, id_usuario: int) -> models.TransaccionIngreso:
        try:
            # 1. VALIDAR CONTRATO
            relacion = self.db.query(RelacionCliente).filter(
                RelacionCliente.id_relacion == transaccion.id_relacion
            ).first()

            if not relacion:
                raise HTTPException(status_code=404, detail="Contrato no encontrado.")

            # OBTENER CUENTA CONTABLE
            medio_obj = self.db.query(MedioIngreso).filter(
                MedioIngreso.id_medio_ingreso == transaccion.id_medio_ingreso
            ).first()

            if not medio_obj:
                raise HTTPException(status_code=404, detail="El medio de pago seleccionado no existe.")
            
            id_catalogo_destino = medio_obj.id_catalogo 

            # 2. PROCESAR DETALLES
            detalles_a_procesar = transaccion.detalles 

            if not detalles_a_procesar:
                # Automático
                deudas_pendientes = self.db.query(ItemFacturable).filter(
                    ItemFacturable.id_persona == relacion.id_persona,
                    ItemFacturable.id_unidad == relacion.id_unidad,
                    ItemFacturable.saldo_pendiente > 0.001,
                    ItemFacturable.estado != 'anulado'
                ).order_by(asc(ItemFacturable.fecha_vencimiento)).all()

                detalles_generados = []
                dinero_disponible_auto = float(transaccion.monto_total)

                class DetalleDummy:
                    def __init__(self, id_item, monto):
                        self.id_item = id_item
                        self.monto_aplicado = monto
                    
                for deuda in deudas_pendientes:
                    if dinero_disponible_auto <= 0.001: break
                    
                    saldo_actual = float(deuda.saldo_pendiente)
                    monto_a_pagar = min(dinero_disponible_auto, saldo_actual)
                    
                    detalles_generados.append(DetalleDummy(deuda.id_item, monto_a_pagar))
                    dinero_disponible_auto -= monto_a_pagar
                
                detalles_a_procesar = detalles_generados
            
            # 3. CREAR CABECERA
            new_ingreso = models.TransaccionIngreso(
                id_relacion=transaccion.id_relacion,
                
                # SEGURIDAD: Aquí usamos el ID del Token, no del Schema
                id_usuario_creador=id_usuario, 
                
                id_catalogo=id_catalogo_destino, 
                id_medio_ingreso=transaccion.id_medio_ingreso,
                id_deposito=transaccion.id_deposito,
                monto_total=transaccion.monto_total,
                fecha=transaccion.fecha,
                num_documento=transaccion.num_documento,
                descripcion=transaccion.descripcion,
                fecha_creacion=datetime.now(),
                estado="APLICADO",
                monto_billetera_usado=0.0
            )
            self.db.add(new_ingreso)
            self.db.flush() 

            monto_disponible_real = float(transaccion.monto_total)
            ultimo_item_procesado = None

            # 4. APLICAR DETALLES
            for detalle_in in detalles_a_procesar:
                item_facturable = self._get_item_facturable(detalle_in.id_item)
                if not item_facturable: raise HTTPException(status_code=404, detail=f"Deuda {detalle_in.id_item} no encontrada.")
                
                if item_facturable.id_persona != relacion.id_persona:
                       raise HTTPException(status_code=400, detail="Error seguridad: Deuda ajena al contrato.")

                saldo_pendiente = float(item_facturable.saldo_pendiente)
                monto_a_pagar = min(float(detalle_in.monto_aplicado), saldo_pendiente)
                
                item_facturable.saldo_pendiente = saldo_pendiente - monto_a_pagar
                item_facturable.estado = "pagado" if item_facturable.saldo_pendiente <= 0.001 else "pagado_parcial"
                
                nuevo_detalle = models.TransaccionIngresoDetalle(
                    id_transaccion=new_ingreso.id_transaccion,
                    id_item=item_facturable.id_item,
                    monto_aplicado=monto_a_pagar,
                    saldo_anterior=saldo_pendiente,
                    saldo_posterior=item_facturable.saldo_pendiente,
                    estado="APLICADO"
                )
                self.db.add(nuevo_detalle)
                
                monto_disponible_real -= monto_a_pagar
                ultimo_item_procesado = item_facturable

            # 5. GENERACIÓN DE FUTURO
            while monto_disponible_real > 0.001:
                
                if ultimo_item_procesado:
                    año = ultimo_item_procesado.año
                    mes = ultimo_item_procesado.mes
                    id_concepto = ultimo_item_procesado.id_concepto
                else:
                    hoy = datetime.now()
                    año = hoy.year
                    mes = hoy.month
                    id_concepto = 2 

                next_mes = mes + 1
                next_anio = año
                if next_mes > 12:
                    next_mes = 1
                    next_anio += 1
                
                next_periodo = f"{next_anio}-{next_mes:02d}"

                siguiente_item = self.db.query(ItemFacturable).filter(
                    ItemFacturable.id_unidad == relacion.id_unidad,
                    ItemFacturable.periodo == next_periodo,
                    ItemFacturable.id_concepto == id_concepto
                ).first()

                if not siguiente_item:
                    monto_base = float(relacion.monto_mensual) if relacion.monto_mensual else 0.0
                    if monto_base <= 0: break 

                    try:
                        fecha_venc = date(next_anio, next_mes, 5)
                    except ValueError:
                        fecha_venc = date(next_anio, next_mes, 28)

                    siguiente_item = models.ItemFacturable(
                        id_unidad=relacion.id_unidad,
                        id_concepto=id_concepto,
                        id_persona=relacion.id_persona,
                        monto_base=monto_base,
                        periodo=next_periodo,
                        fecha_vencimiento=fecha_venc,
                        estado="pendiente",
                        saldo_pendiente=monto_base,
                        año=next_anio,
                        mes=next_mes
                    )
                    self.db.add(siguiente_item)
                    self.db.flush() 
                
                saldo_futuro = float(siguiente_item.saldo_pendiente)
                monto_adelanto = min(monto_disponible_real, saldo_futuro)
                
                siguiente_item.saldo_pendiente = saldo_futuro - monto_adelanto
                siguiente_item.estado = "pagado" if siguiente_item.saldo_pendiente <= 0.001 else "pagado_parcial"

                detalle_adelanto = models.TransaccionIngresoDetalle(
                    id_transaccion=new_ingreso.id_transaccion,
                    id_item=siguiente_item.id_item,
                    monto_aplicado=monto_adelanto,
                    saldo_anterior=saldo_futuro,
                    saldo_posterior=siguiente_item.saldo_pendiente,
                    estado="APLICADO"
                )
                self.db.add(detalle_adelanto)
                
                monto_disponible_real -= monto_adelanto
                ultimo_item_procesado = siguiente_item

            self.db.commit()
            self.db.refresh(new_ingreso)
            return new_ingreso

        except Exception as e:
            self.db.rollback()
            raise e
            
    # ----------------------------------------------------------------------
    # 3. ANULACIÓN
    # ----------------------------------------------------------------------
    def anular_transaccion(self, transaccion_id: int, id_usuario_anulacion: int) -> models.TransaccionIngreso:
        
        db_transaccion = self._get_transaccion_or_404(transaccion_id)
        if db_transaccion.estado == 'ANULADO': raise HTTPException(status_code=400, detail="Transacción ya estaba anulada.")

        try:
            relacion = db_transaccion.relacion_cliente
            if not relacion:
                 raise HTTPException(status_code=404, detail="El contrato asociado a esta transacción no existe.")

            suma_detalles = sum(d.monto_aplicado for d in db_transaccion.detalles)
            monto_excedente_guardado = float(db_transaccion.monto_total) - float(suma_detalles)
            
            if monto_excedente_guardado > 0.001:
                relacion.saldo_favor = float(relacion.saldo_favor) - monto_excedente_guardado

            monto_usado_de_billetera = float(db_transaccion.monto_billetera_usado) if db_transaccion.monto_billetera_usado else 0.0
            if monto_usado_de_billetera > 0.001:
                relacion.saldo_favor = float(relacion.saldo_favor) + monto_usado_de_billetera

            for detalle in db_transaccion.detalles:
                if detalle.estado != 'APLICADO': continue
                
                item = self._get_item_facturable(detalle.id_item)
                if item:
                    item.saldo_pendiente = float(item.saldo_pendiente) + float(detalle.monto_aplicado)
                    if item.saldo_pendiente >= float(item.monto_base) - 0.01:
                        item.estado = "pendiente"
                    else:
                        item.estado = "pagado_parcial"
                
                detalle.estado = "REVERSADO"

            db_transaccion.estado = 'ANULADO'
            db_transaccion.fecha_anulacion = datetime.now()
            # Podríamos guardar 'id_usuario_anulacion' si tuviéramos un campo en BD,
            # pero por ahora queda en el Log de Auditoría (AuditLog).
            
            self.db.commit()
            return db_transaccion

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error al anular: {str(e)}")

    # ----------------------------------------------------------------------
    # 4. LECTURA Y OTROS
    # ----------------------------------------------------------------------
    def get_transaccion_by_id(self, transaccion_id: int) -> Optional[models.TransaccionIngreso]:
        return self.db.query(models.TransaccionIngreso).filter(models.TransaccionIngreso.id_transaccion == transaccion_id).first()
    
    def get_transacciones(self, skip: int = 0, limit: int = 100) -> List[models.TransaccionIngreso]:
        return self.db.query(models.TransaccionIngreso).order_by(desc(models.TransaccionIngreso.fecha)).offset(skip).limit(limit).all()

    def get_transacciones_by_persona(self, persona_id: int, skip: int = 0, limit: int = 100) -> List[models.TransaccionIngreso]:
        return self.db.query(models.TransaccionIngreso)\
            .join(RelacionCliente)\
            .filter(RelacionCliente.id_persona == persona_id)\
            .order_by(desc(models.TransaccionIngreso.fecha))\
            .offset(skip).limit(limit).all()

    def delete_transaccion(self, transaccion_id: int):
        db_transaccion = self._get_transaccion_or_404(transaccion_id)
        if db_transaccion.detalles:
            raise HTTPException(status_code=409, detail="No se puede borrar transacciones con detalles. Use Anular.")
        self.db.delete(db_transaccion)
        self.db.commit()