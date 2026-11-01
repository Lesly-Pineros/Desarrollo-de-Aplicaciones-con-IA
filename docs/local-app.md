# Ejecutar InvestiQ localmente

1. Instala el proyecto con `uv sync --extra dev` (o `pip install -e '.[dev]'`).
2. Copia `.env.example` a `.env` y configura `INVESTIQ_EMAIL`, una contraseña al primer acceso, `NVIDIA_API_KEY` y un `SEC_USER_AGENT` con contacto real. Twelve Data y Marketaux son opcionales.
3. Ejecuta `uv run streamlit run src/investiq/app.py` (o `streamlit run src/investiq/app.py`). La app crea y usa SQLite en el mismo proceso; no hay API/backend separado.
4. Para poblar histórico y features antes de recomendar, ejecuta `uv run investiq-data all` y luego `uv run investiq-data train`.

La primera autenticación con el correo configurado crea la única cuenta; la contraseña se guarda con Argon2 y el token de sesión solo se conserva en el estado servidor. El log guarda intención, herramientas, fuentes y uso de tokens disponibles, nunca texto de consulta o credenciales. La retención objetivo de `QueryLog` es 90 días; para purgar, eliminar registros anteriores a esa ventana desde la base SQLite con una copia de respaldo previa. Cambia `NVIDIA_API_KEY` en el entorno para rotarla sin modificar código. No compartas `.env`.

Sin NVIDIA, las reglas y respuestas deterministas disponibles siguen funcionando. La validación de respuestas generadas por ChatNVIDIA y los tests SEC en vivo requieren credenciales válidas; las pruebas unitarias usan respuestas simuladas y no cuentan como comprobación en vivo. SEC exige un contacto válido en `SEC_USER_AGENT`.
