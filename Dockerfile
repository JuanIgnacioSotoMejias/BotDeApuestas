# Usar imagen base ligera de Python
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto del servidor HTTP
EXPOSE 8000

# Comando por defecto para correr el supervisor de procesos
CMD ["python", "launcher.py"]
