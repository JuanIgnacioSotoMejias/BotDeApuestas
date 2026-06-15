# 🤖 Guía de Configuración del Bot de Apuestas

Este proyecto contiene un bot de notificaciones para Telegram diseñado para leer tus jugadas y el estado de tu banca y enviártelos automáticamente al celular. El script está escrito en Python puro y **no requiere instalar librerías externas** (`pip`), garantizando un inicio inmediato.

---

## 🛠️ Pasos de Configuración en Telegram (1 Minuto)

Sigue estos sencillos pasos para crear tu bot y obtener tu ID de chat privado:

### 1. Crear tu Bot en Telegram
1. Abre tu aplicación de Telegram y busca al usuario oficial **`@BotFather`**.
2. Presiona "Iniciar" o envíale el comando:
   ```text
   /newbot
   ```
3. Te pedirá que elijas un nombre para tu bot (ej: *Mi Analista de Apuestas*).
4. Luego te pedirá un nombre de usuario único que termine en `bot` (ej: *mi_analista_reto_bot*).
5. **@BotFather** te responderá con un mensaje felicitándote y te dará un **Token HTTP API** (se ve como `123456789:ABCdefGh...`). **Copia este Token.**

### 2. Obtener tu Chat ID de Telegram
1. En el buscador de Telegram busca a **`@userinfobot`**.
2. Envía cualquier mensaje o presiona "Iniciar".
3. El bot te responderá de inmediato con tu información de usuario. **Copia el número que aparece en la línea `Id:`** (ej: `987654321`).

### 3. Activar el Bot
1. Haz clic en el enlace de tu propio bot que te dio @BotFather (ej: `t.me/mi_analista_reto_bot`).
2. Presiona el botón de **"Iniciar"** en la ventana de conversación. *Este paso es obligatorio para que el bot tenga permiso de enviarte mensajes.*

---

## 📝 Configurar el Proyecto

1. Abre el archivo [.env](file:///c:/Users/sotox/Music/apuestas/.env) en este directorio.
2. Reemplaza los placeholders con tus credenciales:
   ```env
   TELEGRAM_BOT_TOKEN=pega_aqui_tu_token_de_BotFather
   TELEGRAM_CHAT_ID=pega_aqui_tu_id_numerico_de_userinfobot
   ```
3. Guarda el archivo.

---

## 🚀 Cómo Ejecutar el Bot

Abre tu terminal en el directorio del proyecto y ejecuta el script con el comando correspondiente en Python:

### Enviar todo (Picks + Reporte de Banca)
```bash
python send_picks_bot.py --all
```

### Enviar únicamente las jugadas de la jornada
```bash
python send_picks_bot.py --picks
```

### Enviar únicamente el reporte financiero
```bash
python send_picks_bot.py --bank
```
