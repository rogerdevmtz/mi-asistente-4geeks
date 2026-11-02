---
name: 4geeks-feedback
description: Consulta el detalle y feedback real de una tarea propia de 4Geeks para ayudar a mejorarla. Úsala ante preguntas sobre comentarios, revisión o estado de una tarea concreta; solo GET, nunca entrega ni modifica.
---

# Consultar detalle y feedback de una tarea propia

1. Desde la raíz del workspace, ejecuta `python3 skills/4geeks-feedback/scripts/get_task_feedback.py <task_id> <cohort_id>`. Usa solo un ID obtenido de la lista autenticada de tareas del estudiante; confirma cohorte esperada antes de consultar detalle. No inventes ni reutilices IDs de otros estudiantes.
2. El helper comprueba pertenencia del `task_id` al `cohort_id` en `GET /v1/assignment/user/me/task` y recupera el detalle por `GET /v1/assignment/user/me/task/<task_id>`. Ambos son rutas de estudiante; la segunda está mapeada oficialmente a `TaskMeView`, que filtra el ID por `request.user`. El mapa oficial de `assignments/urls.py` no declara `/v1/assignment/academy/task/<id>` como endpoint; no llames endpoints de academia/docente ni pidas permisos.
3. Si cualquier GET falla, el ID no aparece en la cohorte, la respuesta no coincide, o no puede verificarse identidad/alcance, detente y reporta el error/status sin afirmar éxito. No pruebes otras rutas no documentadas.
4. Presenta título, tipo, `task_status`, `revision_status`, `reviewed_at` y el comentario recibido. En las tareas revisadas de esta cuenta, la API guarda el comentario en `description`: el helper lo incluye con ese nombre solo si hay fecha de revisión y estado `APPROVED` o `REJECTED`. No interpretes la descripción de una tarea sin revisar como feedback. Conserva siempre el campo de origen. Si no hay texto disponible, indícalo. No inventes nota ni atribuyas sugerencias propias al revisor. `complete=true` confirma el acceso al detalle; solo `feedback_text_present=true` demuestra que se recuperó texto.
5. Usa solo GET. No leas ni imprimas el token, cabeceras, payload entero, datos personales, URLs privadas de entrega ni contenido ajeno. No modifiques, entregues ni publiques la tarea, y no cambies configuración, servicios o permisos.
