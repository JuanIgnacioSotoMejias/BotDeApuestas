import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True) # Telegram ID
    username: Mapped[Optional[str]] = mapped_column(String(100))
    saldo: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10.00"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    es_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_registro: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    tickets: Mapped[List["Ticket"]] = relationship(back_populates="usuario")
    transacciones: Mapped[List["Transaccion"]] = relationship(back_populates="usuario")

class Evento(Base):
    __tablename__ = "eventos"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255))
    fecha_evento: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    estado: Mapped[str] = mapped_column(String(50), default="Pendiente") # Pendiente, Finalizado, Cancelado
    resultado_final: Mapped[Optional[str]] = mapped_column(String(100))
    
    selecciones: Mapped[List["TicketSeleccion"]] = relationship(back_populates="evento")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(50), unique=True) # E.g. 'TKT-20260615-01'
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"))
    tipo_ticket: Mapped[str] = mapped_column(String(20)) # Simple, Combinada
    cuota_total: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    monto_apostado: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    retorno_potencial: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente") # Pendiente, Ganado, Perdido, Anulado
    fecha_registro: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    usuario: Mapped["Usuario"] = relationship(back_populates="tickets")
    selecciones: Mapped[List["TicketSeleccion"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )

class TicketSeleccion(Base):
    __tablename__ = "ticket_selecciones"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    evento_id: Mapped[int] = mapped_column(ForeignKey("eventos.id", ondelete="CASCADE"))
    pronostico: Mapped[str] = mapped_column(String(100))
    cuota: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente") # Pendiente, Ganado, Perdido, Anulado
    
    ticket: Mapped["Ticket"] = relationship(back_populates="selecciones")
    evento: Mapped["Evento"] = relationship(back_populates="selecciones")

class Transaccion(Base):
    __tablename__ = "transacciones"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(50)) # Deposito, Retiro, Apuesta, Premio, Reembolso
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    fecha: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    usuario: Mapped["Usuario"] = relationship(back_populates="transacciones")
