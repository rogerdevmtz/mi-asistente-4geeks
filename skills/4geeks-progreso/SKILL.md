---
name: 4geeks-progreso
description: Resume el progreso de un estudiante 4Geeks agregando estados de tareas de una cohorte; distingue completado por el estudiante de aprobado por revisión y explica numeradores, denominadores y alcance, sin atribuir carácter oficial al porcentaje.
---

# Resumen de progreso 4Geeks

1. Cuando Roger pregunte cuánto ha avanzado en un curso/cohorte, ejecuta desde la raíz del workspace `python3 skills/4geeks-progreso/scripts/summarize_progress.py <slug> [macro|course]`. Si pide solo la macrocohorte, usa `macro`; si pide el curso o solo da el slug, usa `course`, que añade únicamente módulos cuyo `source_macro_cohort` apunta a esa macro.
2. El helper reutiliza de forma privada el lector `load_token()` de `4geeks-conexion`. Resuelve slug exacto con `GET /v1/admissions/user/me`, consulta tareas personales con `GET /v1/assignment/user/me/task` y el filtro `cohort` con IDs separados por coma, sin excluir tipos. No abras ni imprimas secretos ni respuesta cruda.
3. Exige `complete=true`, todos los HTTP correctos, paginación completa y cohort ID coincidente en cada registro antes de anunciar un porcentaje como completo. Ante 401/403, error o paginación/filtro no demostrable, comunica el bloqueo y no inventes totales exhaustivos.
4. Explica alcance, tamaño de cohorte y tipos incluidos. Unidad = registro individual de asignación dentro del alcance; no deduplicar títulos, pues pueden existir tareas del mismo título en más de una cohorte/módulo. Desglosa por tipo y por valores de ambos estados.
5. Reporta separadamente:
   - **Completado por mí:** numerador `task_status=DONE`, denominador todos los registros asignados en el alcance; `100 × DONE / total`.
   - **Aprobado por revisión:** numerador `revision_status=APPROVED`, mismo denominador; `100 × APPROVED / total`.
   Preserva fracciones y redondea el porcentaje a 1 decimal. Si total=0, indica N/D. Aclara que son cálculos descriptivos desde las tareas de la API, no un porcentaje oficial de 4Geeks.
6. Distingue `PENDING`, `DONE`, `APPROVED`, `REJECTED` y `IGNORED` en sus campos reales; no infieras aprobación desde `task_status` ni finalización desde revisión. Conserva estados desconocidos.
7. Antes de responder, verifica que la suma de denominadores y numeradores por tipo coincide con totales globales. No publiques ni cambies tareas, configuración, servicios o permisos; el helper hace solo GET.
