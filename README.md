# Mi Asistente 4Geeks

Este proyecto enseña a Atlas, mi agente de OpenClaw, a consultar mi progreso en 4Geeks desde una conversación.

La entrega principal es [SKILL_LOG.md](SKILL_LOG.md). Recoge qué pedí, cómo respondió el agente, qué skill construimos y qué ocurrió al probarla con la API real.

## Qué debe poder hacer

| Skill | Pregunta que resuelve |
| --- | --- |
| Conexión | ¿Mi sesión de 4Geeks funciona? |
| Proyectos | ¿Qué proyectos tengo asignados y en qué estado están? |
| Pendientes | ¿Qué me falta completar o corregir? |
| Progreso | ¿Cuánto he avanzado y cómo se calcula? |
| Cohortes | ¿En qué cohortes estoy inscrito? |
| Detalle y feedback | ¿Qué revisión tiene una tarea y qué debo mejorar? |

Las dos últimas responden a necesidades adicionales: ubicar cada módulo del curso y entender la revisión de una tarea.

## Cómo se protege la credencial

El token se guarda en la configuración privada de OpenClaw, fuera del repositorio. Las skills lo cargan al ejecutar las consultas y no lo muestran en sus respuestas.

Todas las consultas del proyecto son de lectura. No cambian tareas ni envían entregas. Las pruebas y sus límites se detallan en el registro.

## Referencias

- [Enunciado del proyecto](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/openclaw-integration/README.es.md)
- [Mapa de llamadas API](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/openclaw-integration/STUDENT_API_CALLS_REFERENCE.es.md)
