#!/usr/bin/env python3
"""
🛠️ CLASE BASE ABSTRACTA PARA COMANDOS (SOLID)
Define el contrato obligatorio que todos los comandos del bot de Telegram
deben implementar.
"""

from abc import ABC, abstractmethod

class BaseCommand(ABC):
    @abstractmethod
    def ejecutar(self, bot, message, args):
        """
        Ejecuta la lógica del comando.
        - bot: Instancia del TeleBot.
        - message: Objeto mensaje de pyTelegramBotAPI.
        - args: Lista de argumentos pasados con el comando.
        """
        pass
