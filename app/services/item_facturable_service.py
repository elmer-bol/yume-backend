from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, and_, asc
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from calendar import monthrange

from app.db import models
from app.db.models import RelacionCliente, UnidadServicio
from app.schemas import item_facturable_schema as schemas

class ItemFacturableService:
    def __init__(self, db: Session):
        self.db = db
        self.FINAL_STATUSES = ['pagado', 'cancelado', 'anulado']

    # ----------------------------------------------------------------------
    # 1. CONSULTAS (LECTURA)
    # ----------------------------------------------------------------------
    def get_item_by_id(self, item_id: int) -> Optional[models.ItemFacturable]:
        return self.db.query(models.ItemFacturable).filter(models.ItemFacturable.id_item == item_id).first()
    
    def get_items_by_unidad(self, unidad_id: int) -> List[models.ItemFacturable]:
        """
        Modificado: Ahora solo devuelve lo que es COBRABLE (Pendiente y con Saldo).
        Oculta automáticamente lo Pagado, Anulado y CONGELADO.
        """
        return self.db.query(models.ItemFacturable)\
            .options(joinedload(models.ItemFacturable.concepto))\
            .filter(
                models.ItemFacturable.id_unidad == unidad_id,
                models.ItemFacturable.estado.notin_(['pagado', 'anulado', 'cancelado', 'congelado']),
                models.ItemFacturable.saldo_pendiente > 0.01  # <--- El filtro real es el saldo
            )\
            .order_by(asc(models.ItemFacturable.fecha_vencimiento))\
            .all()
    
    def get_all_items(self, skip: int = 0, limit: int = 100) -> List[models.ItemFacturable]:
        return self.db.query(models.ItemFacturable).order_by(desc(models.ItemFacturable.fecha_creacion)).offset(skip).limit(limit).all()

    def get_filtered_items(self, filters: schemas.ItemFacturableFilter, skip: int = 0, limit: int = 100):
        query = self.db.query(models.ItemFacturable)
        
        if filters.id_persona: query = query.filter(models.ItemFacturable.id_persona == filters.id_persona)
        if filters.id_unidad: query = query.filter(models.ItemFacturable.id_unidad == filters.id_unidad)
        if filters.estado: query = query.filter(models.ItemFacturable.estado == filters.estado)
        if filters.periodo: query = query.filter(models.ItemFacturable.periodo == filters.periodo)
        
        if filters.fecha_vencimiento_min: query = query.filter(models.ItemFacturable.fecha_vencimiento >= filters.fecha_vencimiento_min)
        if filters.fecha_vencimiento_max: query = query.filter(models.ItemFacturable.fecha_vencimiento <= filters.fecha_vencimiento_max)

        return query.order_by(desc(models.ItemFacturable.fecha_creacion)).offset(skip).limit(limit).all()

    # ----------------------------------------------------------------------
    # 2. CREACIÓN MANUAL (CON AUDITORÍA)
    # ----------------------------------------------------------------------
    def _validate_periodo_format(self, periodo: str):
        if len(periodo) != 7 or periodo[4] != '-':
            raise HTTPException(status_code=400, detail="Formato inválido. Use 'YYYY-MM'.")

    def create_item(self, item_data: schemas.ItemFacturableCreate, id_usuario: int) -> models.ItemFacturable:
        self._validate_periodo_format(item_data.periodo)

        # 1. Regla R2: No Duplicidad
        existe = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.id_unidad == item_data.id_unidad,
            models.ItemFacturable.id_concepto == item_data.id_concepto,
            models.ItemFacturable.periodo == item_data.periodo,
            models.ItemFacturable.estado != 'anulado'
        ).first()

        if existe:
            raise HTTPException(status_code=409, detail=f"Ya existe cobro para {item_data.periodo}.")

        # 2. Autocompletar Monto
        monto_final = item_data.monto_base
        
        if not monto_final:
            relacion = self.db.query(RelacionCliente).filter(
                RelacionCliente.id_persona == item_data.id_persona,
                RelacionCliente.id_unidad == item_data.id_unidad,
                RelacionCliente.estado == 'Activo'
            ).first()
            
            if relacion:
                monto_final = relacion.monto_mensual
            else:
                raise HTTPException(status_code=400, detail="Debe especificar el monto_base o tener un contrato activo.")

        año = int(item_data.periodo[:4])
        mes = int(item_data.periodo[5:7])

        nuevo_item = models.ItemFacturable(
            id_unidad=item_data.id_unidad,
            id_persona=item_data.id_persona,
            id_concepto=item_data.id_concepto,
            
            # AUDITORÍA
            id_usuario_creador=id_usuario,
            
            periodo=item_data.periodo,
            año=año,
            mes=mes,
            monto_base=monto_final,
            saldo_pendiente=monto_final,
            fecha_vencimiento=item_data.fecha_vencimiento,
            fecha_creacion=datetime.now(),
            estado='pendiente'
        )

        self.db.add(nuevo_item)
        self.db.commit()
        self.db.refresh(nuevo_item)
        return nuevo_item

    # 3. ACTUALIZACIÓN (CON AUDITORÍA)
    def update_item(self, item_id: int, item_in: schemas.ItemFacturableUpdate, id_usuario: int) -> models.ItemFacturable:
        db_item = self.get_item_by_id(item_id)
        if not db_item: raise HTTPException(status_code=404, detail="Item no encontrado.")

        if db_item.estado in self.FINAL_STATUSES:
            raise HTTPException(status_code=403, detail=f"No se puede editar un item '{db_item.estado}'.")

        update_data = item_in.model_dump(exclude_unset=True)

        if item_in.monto_base is not None and item_in.monto_base != db_item.monto_base:
            if db_item.saldo_pendiente < db_item.monto_base:
                raise HTTPException(status_code=403, detail="No se puede cambiar el monto: ya tiene pagos aplicados.")
            
            update_data['saldo_pendiente'] = item_in.monto_base 

        # Aplicar cambios
        for field, value in update_data.items():
            setattr(db_item, field, value)

        # AUDITORÍA
        db_item.id_usuario_modificacion = id_usuario
        db_item.fecha_modificacion = datetime.now()

        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    # ----------------------------------------------------------------------
    # 4. GESTIÓN DE DEUDA
    # ----------------------------------------------------------------------
    def cancel_item(self, item_id: int, id_usuario: int) -> models.ItemFacturable:
        db_item = self.get_item_by_id(item_id)
        if not db_item: raise HTTPException(status_code=404)
        if db_item.estado == 'pagado': raise HTTPException(status_code=400, detail="Imposible cancelar: Ya fue pagado.")
        
        db_item.saldo_pendiente = 0.0
        db_item.estado = 'anulado'
        
        # Auditoría
        db_item.id_usuario_modificacion = id_usuario
        db_item.fecha_modificacion = datetime.now()
        
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def apply_payment(self, item_id: int, monto_pago: float, id_usuario: int) -> models.ItemFacturable:
        # Nota: Normalmente los pagos van por TransaccionIngresoService. 
        # Este método es para ajustes manuales directos.
        db_item = self.get_item_by_id(item_id)
        if not db_item: raise HTTPException(status_code=404)
        
        if db_item.estado in self.FINAL_STATUSES and db_item.saldo_pendiente <= 0:
             raise HTTPException(status_code=400, detail="La deuda ya está saldada.")

        if monto_pago <= 0: raise HTTPException(status_code=400, detail="El pago debe ser positivo.")

        saldo_actual = float(db_item.saldo_pendiente)
        pago_aplicado = min(monto_pago, saldo_actual)
        nuevo_saldo = saldo_actual - pago_aplicado
        
        db_item.saldo_pendiente = nuevo_saldo
        
        if nuevo_saldo <= 0.01:
            db_item.estado = 'pagado'
        elif nuevo_saldo < float(db_item.monto_base):
            db_item.estado = 'pagado_parcial'
        
        # Auditoría
        db_item.id_usuario_modificacion = id_usuario
        db_item.fecha_modificacion = datetime.now()
        
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def check_for_overdue(self) -> List[models.ItemFacturable]:
        # Tarea automática, no requiere usuario
        hoy = date.today()
        vencidos = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.estado == 'pendiente',
            models.ItemFacturable.fecha_vencimiento < hoy
        ).all()
        
        for item in vencidos:
            item.estado = 'vencido'
        
        self.db.commit()
        return vencidos

    # ----------------------------------------------------------------------
    # 5. GENERACIÓN INTELIGENTE (CON REACTIVACIÓN DE ANULADOS)
    # ----------------------------------------------------------------------
    def generar_cuota_con_cruce(self, datos: schemas.GenerarCuotaRequest, id_usuario: int = None) -> Dict[str, Any]:
        # A. AUTO-COMPLETADO (Igual que antes)
        id_persona_final = datos.id_persona
        monto_final = datos.monto_base
        relacion = None

        if not id_persona_final or not monto_final:
            relacion = self.db.query(RelacionCliente).filter(
                RelacionCliente.id_unidad == datos.id_unidad,
                RelacionCliente.estado == "Activo"
            ).first()

            if not relacion:
                raise HTTPException(status_code=404, detail="No se encontró contrato activo.")
            
            if not id_persona_final: id_persona_final = relacion.id_persona
            if not monto_final: monto_final = relacion.monto_mensual

        # B. BÚSQUEDA DE EXISTENTES (INCLUYENDO ANULADOS)
        # Quitamos el filtro "!= anulado" para ver TODO lo que hay
        item_existente = self.db.query(models.ItemFacturable).filter(
            models.ItemFacturable.periodo == datos.periodo,
            models.ItemFacturable.id_unidad == datos.id_unidad,
            models.ItemFacturable.id_concepto == datos.id_concepto
        ).first()

        nuevo_item = None # Variable para trabajar

        # C. LÓGICA DE DECISIÓN (REACTIVAR vs CREAR)
        if item_existente:
            if item_existente.estado == 'anulado':
                # --- CASO 1: RECICLAJE (La magia ocurre aquí) ---
                print(f"♻️ Reactivando cuota anulada ID {item_existente.id_item}...")
                
                # Actualizamos los datos clave
                item_existente.estado = 'pendiente'
                item_existente.monto_base = monto_final
                item_existente.saldo_pendiente = monto_final
                item_existente.fecha_vencimiento = datos.fecha_vencimiento
                item_existente.id_persona = id_persona_final # Por si cambió el dueño
                
                # Auditoría de modificación
                item_existente.id_usuario_modificacion = id_usuario
                item_existente.fecha_modificacion = datetime.now()
                
                nuevo_item = item_existente # Usamos este objeto para el resto del flujo
            else:
                # --- CASO 2: DUPLICADO REAL ---
                raise HTTPException(status_code=409, detail=f"Ya existe cuota activa para {datos.periodo}")
        else:
            # --- CASO 3: CREACIÓN NUEVA (Lo normal) ---
            año_calc = int(datos.periodo[:4])
            mes_calc = int(datos.periodo[5:7])
            
            nuevo_item = models.ItemFacturable(
                id_unidad=datos.id_unidad,
                id_persona=id_persona_final,
                id_concepto=datos.id_concepto,
                id_usuario_creador=id_usuario,
                monto_base=monto_final,
                saldo_pendiente=monto_final,
                periodo=datos.periodo,
                año=año_calc,
                mes=mes_calc,
                fecha_vencimiento=datos.fecha_vencimiento,
                fecha_creacion=datetime.now(),
                estado="pendiente"
            )
            self.db.add(nuevo_item)

        # Guardamos cambios preliminares (sea update o insert)
        self.db.flush() 

        # D. CRUCE DE BILLETERA (Lógica igual, pero usa 'nuevo_item' que puede ser el reciclado)
        if not relacion:
            # Buscamos la relación si no la teníamos (para ver saldo a favor)
            relacion = self.db.query(RelacionCliente).filter(
                RelacionCliente.id_persona == id_persona_final,
                RelacionCliente.id_unidad == datos.id_unidad,
                RelacionCliente.estado == "Activo"
            ).first()

        monto_descontado = 0.0
        mensaje_resp = "Cuota generada exitosamente."

        # Solo aplicamos saldo si la cuota está pendiente (por seguridad)
        if nuevo_item.estado == 'pendiente' and relacion and relacion.saldo_favor > 0:
            saldo_disponible = float(relacion.saldo_favor)
            deuda_inicial = float(nuevo_item.monto_base)
            
            monto_a_usar = min(saldo_disponible, deuda_inicial)
            
            if monto_a_usar > 0:
                relacion.saldo_favor = saldo_disponible - monto_a_usar
                nuevo_item.saldo_pendiente = deuda_inicial - monto_a_usar
                
                if nuevo_item.saldo_pendiente <= 0.001:
                    nuevo_item.estado = "pagado"
                else:
                    nuevo_item.estado = "pagado_parcial"
                
                monto_descontado = monto_a_usar
                mensaje_resp = f"Se descontaron {monto_descontado} automáticamente del saldo a favor."

        self.db.commit()
        self.db.refresh(nuevo_item)
        
        return {
            "mensaje": mensaje_resp,
            "item": nuevo_item,
            "saldo_usado": monto_descontado,
            "saldo_remanente": float(relacion.saldo_favor) if relacion else 0.0
        }
    
    # ----------------------------------------------------------------------
    # 6. UTILIDADES Y GENERACIÓN MASIVA (CON AUDITORÍA)
    # ----------------------------------------------------------------------
    def _calcular_siguiente_periodo(self, periodo_inicio: str, meses_a_sumar: int):
        año_inicial = int(periodo_inicio[:4])
        mes_inicial = int(periodo_inicio[5:7])
        total_meses = mes_inicial - 1 + meses_a_sumar
        nuevo_año = año_inicial + (total_meses // 12)
        nuevo_mes = (total_meses % 12) + 1
        return f"{nuevo_año}-{nuevo_mes:02d}", nuevo_año, nuevo_mes

    def generar_cuotas_masivas(self, datos: schemas.GenerarMasivoRequest, id_usuario: int = None):
        resultados = []
        
        # ... (Logica de periodo inicio igual que antes) ...
        ultimo_periodo_db = self.db.query(func.max(models.ItemFacturable.periodo)).filter(
            models.ItemFacturable.id_unidad == datos.id_unidad,
            models.ItemFacturable.id_concepto == datos.id_concepto,
            models.ItemFacturable.estado != 'anulado'
        ).scalar()
        
        periodo_calculado = ""
        if ultimo_periodo_db:
            periodo_calculado, _, _ = self._calcular_siguiente_periodo(ultimo_periodo_db, 1)
        else:
            if not datos.periodo_inicio:
                raise HTTPException(status_code=400, detail="Debe especificar el periodo_inicio.")
            periodo_calculado = datos.periodo_inicio

        periodo_actual_bucle = periodo_calculado
        for i in range(datos.cantidad_meses):
            if i > 0:
                periodo_para_item, año, mes = self._calcular_siguiente_periodo(periodo_actual_bucle, i)
            else:
                periodo_para_item = periodo_actual_bucle
                año = int(periodo_para_item[:4])
                mes = int(periodo_para_item[5:7])

            _, ultimo_dia_del_mes = monthrange(año, mes)
            fecha_venc = date(año, mes, ultimo_dia_del_mes)
            
            req = schemas.GenerarCuotaRequest(
                id_unidad=datos.id_unidad,
                id_concepto=datos.id_concepto,
                periodo=periodo_para_item,
                fecha_vencimiento=fecha_venc, 
                id_persona=datos.id_persona, 
                monto_base=datos.monto_base  
            )
            
            try:
                # PASAMOS EL USUARIO AQUÍ
                res = self.generar_cuota_con_cruce(req, id_usuario)
                resultados.append({
                    "periodo": periodo_para_item,
                    "estado": res["item"].estado,
                    "info": "OK"
                })
            except HTTPException as e:
                resultados.append({"periodo": periodo_para_item, "estado": "SKIP", "info": e.detail})
            except Exception as e:
                resultados.append({"periodo": periodo_para_item, "estado": "ERROR", "info": str(e)})

        return {
            "mensaje": f"Proceso masivo finalizado desde {periodo_calculado}",
            "detalles": resultados
        }

    def generar_cuotas_globales(self, datos: schemas.GenerarGlobalRequest, id_usuario: int = None):
        # 1. INICIO DE LA CONSULTA (Uniendo Contratos con Unidades)
        # Usamos .join(UnidadServicio) para poder ver de qué tipo es la unidad del contrato
        query = self.db.query(RelacionCliente).join(UnidadServicio).filter(
            RelacionCliente.estado == 'Activo',
            RelacionCliente.tipo_relacion != 'Interno'
        )

        # 2. APLICAR FILTRO DINÁMICO
        # Si el usuario eligió algo específico (que no sea "Todos" ni vacío)
        if datos.tipo_unidad and datos.tipo_unidad != "Todos":
            query = query.filter(UnidadServicio.tipo_unidad == datos.tipo_unidad)

        # 3. EJECUTAR CONSULTA
        contratos_activos = query.all()

        if not contratos_activos:
            filtro_texto = datos.tipo_unidad if datos.tipo_unidad else "General"
            return {"mensaje": f"No hay contratos activos para: {filtro_texto}", "procesados": 0}

        # 4. PREPARAR FECHAS
        año = int(datos.periodo[:4])
        mes = int(datos.periodo[5:7])
        _, ultimo_dia = monthrange(año, mes)
        fecha_venc = date(año, mes, ultimo_dia)

        resultados = []
        contador_exito = 0

        # 5. GENERAR UNO POR UNO
        for contrato in contratos_activos:

             # --- LÓGICA DE DECISIÓN DE MONTO ---
            if datos.monto_override and datos.monto_override > 0:
                # Caso A: Cuota Extraordinaria (Monto Fijo para todos, ej: 220 Bs)
                monto_final = datos.monto_override
            else:
                # Caso B: Expensa Normal (Monto según contrato individual)
                monto_final = contrato.monto_mensual   

            req = schemas.GenerarCuotaRequest(
                id_unidad=contrato.id_unidad,
                id_persona=contrato.id_persona,
                monto_base=monto_final,
                id_concepto=datos.id_concepto,
                periodo=datos.periodo,
                fecha_vencimiento=fecha_venc
            )

            try:
                # Reutilizamos la lógica que ya tenías (que revisa billeteras, etc.)
                res = self.generar_cuota_con_cruce(req, id_usuario)
                
                resultados.append({
                    "unidad": contrato.id_unidad,
                    "estado": "OK", 
                    "detalle": f"Generado ({res['item'].estado})"
                })
                contador_exito += 1
                
            except Exception as e:
                # Si falla uno, no detenemos a los demás
                resultados.append({"unidad": contrato.id_unidad, "estado": "ERROR", "detalle": str(e)})

        return {
            "mensaje": f"Proceso finalizado. {contador_exito} cuotas generadas (Filtro: {datos.tipo_unidad or 'Todos'}).",
            "detalles": resultados
        }
    # Agrega este método dentro de la clase ItemFacturableService

    def generar_retroactivo_contrato(self, datos: schemas.GenerarPorContratoRequest, id_usuario: int):
        """
        Genera deudas históricas o futuras para un contrato específico.
        Ideal para migraciones (Cargar Ene, Feb, Mar de golpe).
        """
        resultados = []
        
        # 1. Obtener datos del contrato (para saber el monto oficial)
        contrato = self.db.query(RelacionCliente).filter(
            RelacionCliente.id_unidad == datos.id_unidad,
            RelacionCliente.id_persona == datos.id_persona,
            RelacionCliente.estado == 'Activo'
        ).first()

        if not contrato:
            raise HTTPException(status_code=404, detail="No se encontró un contrato activo entre esta persona y unidad.")

        # Si no mandaron monto específico, usamos el del contrato
        monto_a_usar = datos.monto_override if datos.monto_override else contrato.monto_mensual

        # 2. Bucle de Generación
        periodo_actual = datos.periodo_inicio

        for i in range(datos.cantidad_meses):
            # Calcular el periodo para esta iteración (Ej: 2025-01, luego 2025-02...)
            if i > 0:
                periodo_para_item, año, mes = self._calcular_siguiente_periodo(datos.periodo_inicio, i)
            else:
                periodo_para_item = datos.periodo_inicio
                año = int(periodo_para_item[:4])
                mes = int(periodo_para_item[5:7])

            # Calcular vencimiento (Fin de mes)
            _, ultimo_dia = monthrange(año, mes)
            fecha_venc = date(año, mes, ultimo_dia)

            # Preparar la solicitud individual
            req = schemas.GenerarCuotaRequest(
                id_unidad=datos.id_unidad,
                id_persona=datos.id_persona,
                id_concepto=datos.id_concepto,
                periodo=periodo_para_item,
                fecha_vencimiento=fecha_venc,
                monto_base=monto_a_usar
            )

            try:
                # Reutilizamos la lógica blindada (que revisa duplicados y billetera)
                res = self.generar_cuota_con_cruce(req, id_usuario)
                
                resultados.append({
                    "periodo": periodo_para_item,
                    "estado": "GENERADO",
                    "detalle": f"Deuda creada. Estado: {res['item'].estado}"
                })
            except HTTPException as e:
                # Si ya existe (409), no es error, es que ya estaba cargado
                if e.status_code == 409:
                    resultados.append({"periodo": periodo_para_item, "estado": "EXISTENTE", "detalle": "Ya existía"})
                else:
                    resultados.append({"periodo": periodo_para_item, "estado": "ERROR", "detalle": e.detail})
            except Exception as e:
                resultados.append({"periodo": periodo_para_item, "estado": "ERROR", "detalle": str(e)})

        return {
            "mensaje": f"Proceso finalizado. {len(resultados)} periodos procesados.",
            "detalles": resultados
        }
    
    # ----------------------------------------------------------------------
    # 7. ANULACIÓN MASIVA (ROLLBACK) - SOPORTE TIPOS DINÁMICOS
    # ----------------------------------------------------------------------
    def anular_cuotas_masivas(self, datos: schemas.AnulacionMasivaRequest, id_usuario: int):
        
        # 1. INICIAR CONSULTA CON JOIN
        # Unimos ItemFacturable con UnidadServicio para poder ver el 'tipo_unidad'
        query = self.db.query(models.ItemFacturable).join(models.UnidadServicio).filter(
            models.ItemFacturable.periodo == datos.periodo,
            models.ItemFacturable.id_concepto == datos.id_concepto,
            
            # SEGURIDAD CRÍTICA:
            # Solo anulamos si está pendiente Y si el saldo es igual al total.
            # (Significa que nadie ha pagado ni un centavo todavía).
            models.ItemFacturable.estado == 'pendiente',
            models.ItemFacturable.saldo_pendiente == models.ItemFacturable.monto_base
        )

        # 2. LÓGICA DE FILTRADO DINÁMICO
        # Definimos qué valores significan "No filtrar"
        VALORES_IGNORAR = ["Todos (Sin Filtro)", "Todos", "", None]

        # Si el usuario mandó un tipo específico (ej: "Helipuerto"), filtramos.
        if datos.tipo_unidad not in VALORES_IGNORAR:
            # Aquí la BD se encarga. Si mañana creas "Nave Espacial", funcionará igual.
                query = self.db.query(models.ItemFacturable).join(
                models.UnidadServicio, 
                models.ItemFacturable.id_unidad == models.UnidadServicio.id_unidad
            ).filter(
                models.ItemFacturable.periodo == datos.periodo,
                models.ItemFacturable.id_concepto == datos.id_concepto,
                models.ItemFacturable.estado == 'pendiente',
                models.ItemFacturable.saldo_pendiente == models.ItemFacturable.monto_base
            )

        # 3. OBTENER ITEMS
        items_a_anular = query.all()
        cantidad = len(items_a_anular)

        if cantidad == 0:
            return {
                "mensaje": f"No se encontró nada para anular en {datos.periodo} (Filtro: {datos.tipo_unidad or 'Todos'}).", 
                "anulados": 0
            }

        # 4. EJECUTAR ANULACIÓN (Iteramos para auditar uno por uno)
        for item in items_a_anular:
            item.estado = 'anulado'
            item.saldo_pendiente = 0.00
            
            # Auditoría Interna
            item.id_usuario_modificacion = id_usuario
            item.fecha_modificacion = datetime.now()
            
            # OPCIONAL: Si tienes tabla AuditLog, descomenta esto:
            # self._registrar_auditoria(item.id_item, "ANULACION_MASIVA", datos.motivo, id_usuario)

        self.db.commit()

        return {
            "mensaje": f"Operación exitosa. Se anularon {cantidad} cuotas de tipo '{datos.tipo_unidad or 'Todos'}'.",
            "anulados": cantidad,
            "motivo": datos.motivo
        }