# Mi Asistente 4Geeks — registro de skills

He enseñado a Atlas, mi agente de OpenClaw, a consultar mi cuenta de 4Geeks. Lo construimos mediante conversaciones, una skill cada vez. Cada una resuelve una pregunta concreta y usa únicamente consultas de lectura.

## Cómo empezamos

Mi primera petición fue: «Quiero darte la habilidad de conectarte a mi cuenta de 4Geeks usando mi token de estudiante, sin que tenga que desarrollar código de mi parte. ¿Qué debemos hacer?».

Atlas propuso empezar por comprobar la conexión. Me pidió el token y confirmar la dirección de la API. La credencial se guardó en la configuración privada de OpenClaw, con permisos restringidos. No está en las skills ni en este repositorio.

Después fuimos añadiendo las cuatro capacidades principales y dos necesidades adicionales: consultar mis cohortes y entender el feedback de una tarea.

## 1. Comprobar la conexión

**Lo que pedí:** «Cuando te pregunte si mi conexión de 4Geeks funciona, comprueba que el token siga válido y responde sin revelar credenciales».

**Qué decidimos:** crear `4geeks-conexion`. Hace una sola consulta al usuario actual y devuelve el estado de la conexión, sin mostrar la información personal recibida.

**API:** `GET /v1/admissions/user/me`.

**Prueba real:** el 2 de noviembre de 2026, a las 20:17 (Europe/Madrid), respondió HTTP 200. La sesión era válida y la respuesta permitió comprobar la identidad. El resultado público contiene solo el estado HTTP y dos comprobaciones de sí/no.

## 2. Consultar mis proyectos

**Lo que pedí:** «¿Qué proyectos tengo asignados en spain-aie-pt-5 y en qué estado está cada uno?».

**Qué decidimos:** crear `4geeks-proyectos`. Resuelve la cohorte exacta y consulta solo proyectos. Comprueba la paginación y la pertenencia a la cohorte antes de presentar una lista completa.

**API:** `GET /v1/admissions/user/me` para resolver la cohorte y `GET /v1/assignment/user/me/task` con los filtros `task_type=PROJECT` y `cohort`.

**Prueba inicial:** el 2 de noviembre, a las 20:33, la cohorte principal (ID 1839) devolvió 7 proyectos, todos pendientes. La consulta respondió HTTP 200 y la página quedó completa.

La ruta de cohortes sugerida en el mapa del ejercicio devolvió HTTP 403. Atlas usó las inscripciones propias incluidas en el usuario actual, sin cambiar permisos.

## 3. Saber qué me falta

**Lo que pedí:** «Quiero saber exactamente qué me falta completar en mi cohorte, incluyendo tareas rechazadas que requieren corregir».

**Qué decidimos:** crear `4geeks-pendientes`. Incluye todos los tipos de trabajo y separa lo que falta completar, lo que necesita correcciones y lo que ya espera revisión. Puede consultar solo la cohorte principal o añadir sus módulos vinculados.

**API:** `GET /v1/admissions/user/me` y `GET /v1/assignment/user/me/task`, filtrando los IDs de las cohortes incluidas.

**Prueba real:** el 2 de noviembre, a las 20:41, el curso completo devolvió HTTP 200 y 90 registros. El alcance incluía la cohorte principal y 7 módulos vinculados.

| Estado | Cantidad |
| --- | ---: |
| Por completar | 43 |
| Requieren correcciones | 0 |
| Esperan revisión | 3 |
| Aprobados | 44 |
| Total | 90 |

Los 43 pendientes son 7 proyectos, 23 ejercicios y 13 lecciones. La API no devolvió fechas límite utilizables; el asistente lo indica sin inventarlas.

La consulta de la cohorte principal por separado devolvió 54 registros: 39 pendientes y 15 aprobados. No debe confundirse con el alcance del curso completo.

## 4. Resumir mi progreso

**Lo que pedí:** «¿Qué tan avanzado estoy en mi curso? Quiero un resumen claro con numerador, denominador y fórmula explícita».

**Qué decidimos:** crear `4geeks-progreso`. Agrega los estados de las tareas y distingue el trabajo completado por mí del aprobado en revisión.

**API:** las mismas consultas de usuario y tareas, aplicadas únicamente al curso elegido. No consulta ni modifica entregas.

**Prueba real:** el 2 de noviembre, a las 20:51, se recuperaron los 90 registros del curso con HTTP 200 y alcance verificado. Incluyen 15 proyectos, 60 ejercicios y 15 lecciones.

| Medida | Cálculo | Resultado |
| --- | --- | ---: |
| Completado por mí | 100 × 47 / 90 | 52,2 % |
| Aprobado en revisión | 100 × 44 / 90 | 48,9 % |

El primer cálculo usa `task_status=DONE`; el segundo, `revision_status=APPROVED`. Ambos usan como denominador todos los registros del alcance. Son porcentajes calculados desde las tareas, no una métrica oficial de 4Geeks.

También se probó el modo de cohorte principal: 15 de 54 completados y aprobados, un 27,8 %. Las sumas por tipo coinciden con los totales.

## 5. Consultar mis cohortes

**Lo que pedí:** «Necesito saber en qué cohortes estoy inscrito y cuál es el estado de cada inscripción. No supongas que la primera es la activa».

**Qué decidimos:** crear `4geeks-cohortes`. Lista mis inscripciones y mantiene separados `educational_status` (estado de mi inscripción) y `stage` (etapa de la cohorte).

**API:** intenta `GET /v1/admissions/academy/cohort/me`. En mi cuenta devuelve HTTP 403, así que utiliza las inscripciones propias de `GET /v1/admissions/user/me`, que devuelve HTTP 200. No se amplían permisos.

**Prueba real:** el 2 de noviembre, a las 20:59, recuperó 32 inscripciones y confirmó que hay varias activas.

| Estado de inscripción | Cantidad |
| --- | ---: |
| `ACTIVE` | 26 |
| `GRADUATED` | 5 |
| `NOT_COMPLETING` | 1 |

Por ejemplo, `spain-aie-pt-5` tiene inscripción `ACTIVE` y etapa `STARTED`. `spain-ai-engineering-introduction` tiene inscripción `NOT_COMPLETING` y etapa `PREWORK`. La skill conserva los valores originales sin confundir ambos campos.

## 6. Consultar detalle y feedback

**Lo que pedí:** «Mi segunda necesidad adicional es entender el detalle y feedback de una tarea para saber cómo mejorarla. Si el feedback está vacío, dilo».

**Qué decidimos:** crear `4geeks-feedback`. Primero comprueba que el ID aparece en mis tareas de la cohorte indicada. Después consulta su detalle y muestra los estados y el feedback que realmente devuelve la API.

**API:** `GET /v1/assignment/user/me/task`, filtrando la cohorte, y `GET /v1/assignment/user/me/task/{task_id}`. La ruta personal de detalle filtra por el usuario autenticado; es la alternativa comprobada a la ruta genérica del mapa del ejercicio.

**Prueba real:** el 2 de noviembre, a las 21:08, consultamos mi tarea `1004503`, de la cohorte `1839`. Ambas llamadas devolvieron HTTP 200 y coincidieron el ID y la cohorte.

El título recibido fue «Milestone 1 — Your Company's Public Website». Sus estados eran `task_status=PENDING` y `revision_status=PENDING`. La respuesta no incluía campos de feedback ni nota. Atlas informó de esa ausencia sin inventar comentarios del revisor.

Esta limitación pertenece a los datos que expone la ruta consultada: la prueba demuestra acceso al detalle, no la existencia de comentarios ni calificaciones que la API no devuelve.

## Comprobación final

El 2 de noviembre, a las 21:12 (Europe/Madrid), se volvieron a ejecutar las seis consultas. Pasaron la validación de estructura, la comprobación de sintaxis y las pruebas con la cuenta real. OpenClaw reconoció las seis skills como disponibles. El resumen verificable está en [verificacion.json](verificacion.json).

La revisión de privacidad comparó el token privado con los 22 archivos originales del paquete y no encontró coincidencias. El resultado está en [privacidad.json](privacidad.json); el archivo privado de credenciales no forma parte de la entrega.

También se revisó la clasificación de proyectos: una entrega con `DONE` no implica aprobación. La prueba real identificó los 7 proyectos pendientes de la cohorte principal y 2 aprobados de `personal-assistants-with-openclaw`. Pasaron además cinco casos de clasificación que cubren pendientes, revisión, aprobación, rechazo y estados sin clasificar.

Los porcentajes cuentan registros de asignación. Si el mismo título aparece en la cohorte principal y en un módulo, cada asignación cuenta por separado. El alcance queda explícito para que el resultado se pueda reproducir.

### Revisión de los criterios

| Requisito | Evidencia |
| --- | --- |
| OpenClaw activo y accesible | Conversaciones reales con Atlas y reconocimiento de las seis skills. |
| Cuatro skills principales | Apartados 1 a 4 y sus pruebas con la API. |
| Dos skills adicionales | Cohortes y detalle/feedback, con la necesidad que las originó. |
| Una responsabilidad por skill | Cada carpeta contiene una función concreta y sus instrucciones. |
| Construcción conversacional | Peticiones originales enlazadas debajo y decisiones en cada apartado. |
| Token privado | Configuración fuera del repositorio, permisos `600`; no se incluye su valor. |
| Registro con prompt, función, API y prueba | Este archivo y las peticiones completas. |
| Información precisa | Estados literales, fórmulas reproducibles, alcance y límites expresos. |
| Entrega en GitHub | `SKILL_LOG.md` en la raíz del repositorio junto a las skills y la verificación. |

Las pruebas se hicieron con consultas de lectura. No se cambiaron tareas, entregas ni permisos de 4Geeks. La prueba de feedback no se presenta como evidencia de comentarios disponibles, y los porcentajes calculados no se atribuyen a la plataforma.

### Incidencia del entorno

Una prueba adicional que pidió usar las seis skills en una sola conversación se interrumpió: la VPS se quedó sin memoria y el sistema detuvo OpenClaw. No se cuenta como una prueba conversacional superada. El servicio existente se recuperó y completó su preparación interna.

Las seis pruebas reales anteriores y su verificación conjunta siguen siendo válidas. Esta incidencia muestra un límite del entorno: conviene hacer consultas concretas y evitar agrupar demasiadas operaciones en la VPS actual.

Después de la recuperación se probó una pregunta concreta de progreso desde la conversación. Atlas seleccionó `4geeks-progreso`, ejecutó una consulta nueva y respondió con 47/90 completadas y 44/90 aprobadas. La [petición y respuesta final](conversaciones/comprobacion-final.md) documentan esa prueba superada.

### Peticiones originales y archivos

| Conversación | Skill |
| --- | --- |
| [Descubrimiento](conversaciones/descubrimiento.md) | Plan inicial con Atlas. |
| [Petición 1](conversaciones/skill-1.md) | [Conexión](skills/4geeks-conexion/SKILL.md) |
| [Petición 2](conversaciones/skill-2.md) | [Proyectos](skills/4geeks-proyectos/SKILL.md) |
| [Petición 3](conversaciones/skill-3.md) | [Pendientes](skills/4geeks-pendientes/SKILL.md) |
| [Petición 4](conversaciones/skill-4.md) | [Progreso](skills/4geeks-progreso/SKILL.md) |
| [Petición 5](conversaciones/skill-5.md) | [Cohortes](skills/4geeks-cohortes/SKILL.md) |
| [Petición 6](conversaciones/skill-6.md) | [Detalle y feedback](skills/4geeks-feedback/SKILL.md) |

Las fechas y horas de este registro usan Europe/Madrid. Los resultados son una instantánea de las pruebas; las próximas consultas pueden cambiar a medida que avance el curso.
