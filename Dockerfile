# Usar imagen base ligera de Python
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Hacer ejecutable el script de inicio
RUN chmod +x start.sh

# Exponer el puerto del servidor HTTP
EXPOSE 8000

# Comando por defecto para correr el servidor web y el bot en paralelo
CMD ["sh", "start.sh"]
