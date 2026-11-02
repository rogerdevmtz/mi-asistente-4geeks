---
name: 4geeks-conexion
description: Comprueba si la conexión autenticada de Roger a 4Geeks sigue funcionando. Úsala cuando pregunte si funciona, está activa o sigue autenticada; solo hace una consulta de lectura al usuario actual.
---

# Comprueba la conexión de 4Geeks

1. Ejecuta `python3 skills/4geeks-conexion/scripts/check_connection.py` desde la raíz del workspace activo. El helper lee la credencial dentro del proceso y devuelve únicamente estado HTTP y comprobaciones booleanas. No uses `cat`, `echo`, `env`, trazas de depuración ni comandos que expongan el secreto.
2. Interpreta su JSON reducido:
   - `http_status: 200`, `session_valid: true` e `identity_verified: true`: confirma que la conexión funciona en esta comprobación.
   - HTTP `401` o `403`: indica claramente que 4Geeks no aceptó la autenticación; no digas que funciona.
   - Cualquier otro código, error de red, credencial ausente o identidad no verificable: informa que no se pudo verificar e indica el estado disponible. No infieras éxito.
3. Responde en español, breve y sin exponer credenciales ni datos personales. Nunca muestres token, cabeceras, email, nombre, identificador, cuerpo de respuesta ni salida de depuración.

El helper consulta solo `GET https://breathecode.herokuapp.com/v1/admissions/user/me`, no reintenta y no guarda la respuesta. No realiza cambios ni llama a otros endpoints.
