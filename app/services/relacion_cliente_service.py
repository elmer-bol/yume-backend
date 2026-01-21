# Archivo: app/services/relacion_cliente_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date

from app.db import models
from app.schemas import relacion_cliente_schema as schemas

class NotFoundError(Exception):
    pass

class RelacionClienteService:
    def __init__(self, db: Session):
        self.db = db

    def get_relacion_by_id(self, relacion_id: int) -> models.RelacionCliente:
        relacion = self.db.query(models.RelacionCliente).filter(
            models.RelacionCliente.id_relacion == relacion_id
        ).first()
        if not relacion:
            raise NotFoundError(f"La relación con ID {relacion_id} no existe.")
        return relacion

    def get_all_relaciones(self, filtros: schemas.RelacionClienteFilter, skip: int = 0, limit: int = 100) -> List[models.RelacionCliente]:
        query = self.db.query(models.RelacionCliente)

        if filtros.id_persona:
            query = query.filter(models.RelacionCliente.id_persona == filtros.id_persona)
        if filtros.id_unidad:
            query = query.filter(models.RelacionCliente.id_unidad == filtros.id_unidad)
        if filtros.estado:
            query = query.filter(models.RelacionCliente.estado == filtros.estado)
        if filtros.tipo_relacion:
            query = query.filter(models.RelacionCliente.tipo_relacion == filtros.tipo_relacion)

        query = query.order_by(desc(models.RelacionCliente.fecha_inicio))
        return query.offset(skip).limit(limit).all()

    def create_relacion(self, relacion_in: schemas.RelacionClienteCreate) -> models.RelacionCliente:
        # 1. Validaciones existentes...
        persona = self.db.query(models.Persona).filter(models.Persona.id_persona == relacion_in.id_persona).first()
        if not persona:
            raise NotFoundError(f"La Persona ID {relacion_in.id_persona} no existe.")

        unidad = self.db.query(models.UnidadServicio).filter(models.UnidadServicio.id_unidad == relacion_in.id_unidad).first()
        if not unidad:
            raise NotFoundError(f"La Unidad ID {relacion_in.id_unidad} no existe.")

        # --- 🔥 NUEVA VALIDACIÓN: ¿La unidad ya está ocupada? ---
        if unidad.estado == "Ocupado":
             # Opcional: Puedes lanzar error o permitirlo si es un 'roommate'
             # Por ahora, lancemos error para mantener el orden.
             raise Exception(f"La unidad {unidad.identificador_unico} ya se encuentra ocupada.")

        # 2. Crear la relación (Igual que antes)
        nueva_relacion = models.RelacionCliente(
            id_persona=relacion_in.id_persona,
            id_unidad=relacion_in.id_unidad,
            fecha_inicio=relacion_in.fecha_inicio,
            fecha_fin=relacion_in.fecha_fin,
            estado=relacion_in.estado,
            tipo_relacion=relacion_in.tipo_relacion,
            monto_mensual=relacion_in.monto_mensual,
            saldo_favor=0.0
        )

        self.db.add(nueva_relacion)
        
        # --- 🔥 LA MAGIA AUTOMÁTICA: Actualizar Estado de Unidad ---
        # Si el contrato está activo, marcamos la unidad como Ocupada
        if relacion_in.estado == 'Activo':
            unidad.estado = "Ocupado"
            self.db.add(unidad) # Agregamos la unidad a la transacción
        # -----------------------------------------------------------

        self.db.commit()
        self.db.refresh(nueva_relacion)
        return nueva_relacion

    def update_relacion(self, relacion_id: int, relacion_update: schemas.RelacionClienteUpdate) -> models.RelacionCliente:
        # 1. Obtenemos el contrato actual de la BD
        db_relacion = self.get_relacion_by_id(relacion_id)
        
        # --- 🤖 AUTOMATIZACIÓN DE ESTADOS (NUEVO) ---
        # Verificamos si en la actualización viene un cambio de 'estado'
        if relacion_update.estado is not None:
            nuevo_estado = relacion_update.estado
            estado_anterior = db_relacion.estado
            
            # Buscamos la unidad asociada para actualizarla
            unidad = self.db.query(models.UnidadServicio).filter(models.UnidadServicio.id_unidad == db_relacion.id_unidad).first()
            
            if unidad:
                # CASO 1: REACTIVACIÓN (Estaba Inactivo/Legal -> Pasa a Activo)
                if nuevo_estado == "Activo" and estado_anterior != "Activo":
                    # Validamos si no está ocupada por otro (Opcional, pero recomendado)
                    if unidad.estado == "Ocupado":
                        # Aquí podrías lanzar error, pero como es una corrección manual, 
                        # asumimos que el admin sabe lo que hace y solo actualizamos.
                        pass 
                    unidad.estado = "Ocupado"
                    self.db.add(unidad)
                
                # CASO 2: DESACTIVACIÓN (Estaba Activo -> Pasa a Inactivo/Legal)
                elif nuevo_estado != "Activo" and estado_anterior == "Activo":
                    unidad.estado = "Vacío"
                    self.db.add(unidad)
        # ---------------------------------------------

        # 2. Actualización estándar de campos
        update_data = relacion_update.model_dump(exclude_unset=True)

                # --- 🚚 DETECCIÓN DE MUDANZA (Cambio de Unidad) ---
        if relacion_update.id_unidad and relacion_update.id_unidad != db_relacion.id_unidad:
            # 1. Liberar la unidad anterior
            unidad_anterior = self.db.query(models.UnidadServicio).get(db_relacion.id_unidad)
            if unidad_anterior:
                unidad_anterior.estado = "Vacío"
                self.db.add(unidad_anterior)
            
            # 2. Ocupar la nueva unidad
            unidad_nueva = self.db.query(models.UnidadServicio).get(relacion_update.id_unidad)
            if unidad_nueva:
                unidad_nueva.estado = "Ocupado"
                self.db.add(unidad_nueva)

        for field, value in update_data.items():
            setattr(db_relacion, field, value)

        self.db.commit()
        self.db.refresh(db_relacion)
        return db_relacion

    def delete_relacion(self, relacion_id: int) -> models.RelacionCliente:
        db_relacion = self.get_relacion_by_id(relacion_id)
        
        # 1. Desactivamos el contrato
        db_relacion.estado = "Inactivo"
        db_relacion.fecha_fin = date.today()
        
        # --- Liberar la Unidad ---
        # Buscamos la unidad asociada y la ponemos Vacía
        unidad = self.db.query(models.UnidadServicio).filter(models.UnidadServicio.id_unidad == db_relacion.id_unidad).first()
        if unidad:
            unidad.estado = "Vacío"
            self.db.add(unidad)
        # ----------------------------------------------

        self.db.commit()
        self.db.refresh(db_relacion)
        return db_relacion