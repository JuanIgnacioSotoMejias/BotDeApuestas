// 🏆 LOGICA DEL DASHBOARD INTERACTIVO Y CONSOLA DE ADMINISTRACIÓN

window.growthChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
    // Inicializar elementos de UI
    const elBancaInicial = document.getElementById("banca-inicial");
    const elBancaDisponible = document.getElementById("banca-disponible");
    const elDineroJuego = document.getElementById("dinero-juego");
    const elYield = document.getElementById("yield-stats");
    const elRoi = document.getElementById("roi-stats");
    const containerPicks = document.getElementById("active-picks-container");
    const containerSettled = document.getElementById("settled-tickets-container");
    
    // Elementos de la vista Admin
    const panelVisual = document.getElementById("visual-panel");
    const panelAdmin = document.getElementById("admin-panel");
    const tabVisualBtn = document.getElementById("tab-btn-visual");
    const tabAdminBtn = document.getElementById("tab-btn-admin");
    const containerAdminTickets = document.getElementById("admin-active-tickets-list");
    
    // Formularios e inputs
    const formCrearPicks = document.getElementById("crear-picks-form");
    const inputFecha = document.getElementById("form-fecha");
    const inputDesc = document.getElementById("form-desc");
    const containerSeguro = document.getElementById("seguro-selections-container");
    const containerArriesgado = document.getElementById("arriesgado-selections-container");
    const addSelectionBtns = document.querySelectorAll(".add-selection-btn");

    let dataBanca = null;

    // Configurar fecha por defecto (Hoy)
    const hoy = new Date().toISOString().split('T')[0];
    inputFecha.value = hoy;
    inputDesc.value = `Jornada ${hoy}`;

    // --- TAB SYSTEM LÓGICA ---
    const setupTabs = () => {
        tabVisualBtn.addEventListener("click", () => {
            tabVisualBtn.classList.add("active");
            tabAdminBtn.classList.remove("active");
            panelVisual.style.display = "grid";
            panelAdmin.style.display = "none";
        });

        tabAdminBtn.addEventListener("click", () => {
            tabAdminBtn.classList.add("active");
            tabVisualBtn.classList.remove("active");
            panelVisual.style.display = "none";
            panelAdmin.style.display = "grid";
        });
    };

    // --- DYNAMIC FORM LÓGICA ---
    const createSelectionRowHTML = (type) => {
        const row = document.createElement("div");
        row.className = "selection-row";
        row.innerHTML = `
            <div class="form-group">
                <label>Partido / Evento</label>
                <input type="text" class="sel-partido" placeholder="Ej: España vs Cabo Verde" required>
            </div>
            <div class="form-group">
                <label>Pronóstico</label>
                <input type="text" class="sel-pronostico" placeholder="Ej: Uruguay gana" required>
            </div>
            <div class="form-group">
                <label>Cuota</label>
                <input type="number" class="sel-cuota" step="0.01" min="1.01" placeholder="1.85" required>
            </div>
            <div class="form-group">
                <label>Probabilidad (%)</label>
                <input type="number" class="sel-probabilidad" min="1" max="100" placeholder="70" required>
            </div>
            <button type="button" class="btn-danger-icon remove-row-btn" title="Eliminar Evento">🗑️</button>
        `;

        // Añadir evento para remover
        row.querySelector(".remove-row-btn").addEventListener("click", () => {
            row.remove();
        });

        return row;
    };

    const setupForm = () => {
        const btnGenerarIa = document.getElementById("btn-generar-ia");
        if (btnGenerarIa) {
            btnGenerarIa.addEventListener("click", async () => {
                if (!confirm("🤖 ¿Estás seguro de que deseas activar a los agentes de IA para buscar, analizar y generar automáticamente los parleys oficiales de hoy?")) {
                    return;
                }
                
                const originalText = btnGenerarIa.textContent;
                btnGenerarIa.textContent = "⏳ Generando...";
                btnGenerarIa.disabled = true;
                
                try {
                    const res = await fetch("/api/generar_picks_ia", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });
                    
                    if (res.ok) {
                        const data = await res.json();
                        alert("🎉 " + data.message);
                        await cargarYRenderizar();
                        tabVisualBtn.click();
                    } else {
                        const err = await res.text();
                        alert("❌ Error al generar picks con agentes: " + err);
                    }
                } catch (e) {
                    console.error(e);
                    alert("❌ Error al comunicarse con la API de generación.");
                } finally {
                    btnGenerarIa.textContent = originalText;
                    btnGenerarIa.disabled = false;
                }
            });
        }

        // Agregar selección inicial por defecto
        containerSeguro.appendChild(createSelectionRowHTML("seguro"));
        containerArriesgado.appendChild(createSelectionRowHTML("arriesgado"));

        // Eventos para botones "+ Añadir Selección"
        addSelectionBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                const type = btn.getAttribute("data-type");
                const container = type === "seguro" ? containerSeguro : containerArriesgado;
                container.appendChild(createSelectionRowHTML(type));
            });
        });

        // Evento de envío del formulario
        formCrearPicks.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const submitBtn = formCrearPicks.querySelector(".submit-picks-btn");
            const originalBtnText = submitBtn.textContent;
            submitBtn.textContent = "⏳ Registrando y Enviando...";
            submitBtn.disabled = true;

            try {
                const parleySeguroData = processSelections("seguro");
                const parleyArriesgadoData = processSelections("arriesgado");

                if (!parleySeguroData || !parleyArriesgadoData) {
                    alert("❌ Debes agregar al menos una selección válida en cada combinada.");
                    submitBtn.textContent = originalBtnText;
                    submitBtn.disabled = false;
                    return;
                }

                const payload = {
                    fecha: inputFecha.value,
                    descripcion: inputDesc.value,
                    parley_seguro: parleySeguroData,
                    parley_arriesgado: parleyArriesgadoData
                };

                const res = await fetch("/api/crear_picks", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    const resJson = await res.json();
                    alert("🎉 " + resJson.message);
                    
                    // Limpiar y resetear formulario
                    containerSeguro.innerHTML = "";
                    containerArriesgado.innerHTML = "";
                    containerSeguro.appendChild(createSelectionRowHTML("seguro"));
                    containerArriesgado.appendChild(createSelectionRowHTML("arriesgado"));
                    inputFecha.value = hoy;
                    inputDesc.value = `Jornada ${hoy}`;
                    
                    // Recargar datos e ir al panel visual
                    await cargarYRenderizar();
                    tabVisualBtn.click();
                } else {
                    const err = await res.text();
                    alert("❌ Error al registrar picks: " + err);
                }
            } catch (err) {
                console.error(err);
                alert("❌ Error de comunicación con la API del Servidor.");
            } finally {
                submitBtn.textContent = originalBtnText;
                submitBtn.disabled = false;
            }
        });
    };

    const processSelections = (type) => {
        const container = type === "seguro" ? containerSeguro : containerArriesgado;
        const rows = container.querySelectorAll(".selection-row");
        
        if (rows.length === 0) return null;

        const selecciones = [];
        let cuotaTotal = 1.0;
        let probEstCombinada = 1.0;

        rows.forEach(row => {
            const partido = row.querySelector(".sel-partido").value.trim();
            const pronostico = row.querySelector(".sel-pronostico").value.trim();
            const cuota = parseFloat(row.querySelector(".sel-cuota").value);
            const probabilidadVal = parseFloat(row.querySelector(".sel-probabilidad").value);

            const probImpVal = (1.0 / cuota) * 100;
            const difVal = probabilidadVal - probImpVal;
            const valorStr = difVal > 0 ? `Sí (+${difVal.toFixed(1)}%)` : "Riesgo Ajustado";

            selecciones.push({
                partido: partido,
                pronostico: pronostico,
                cuota: cuota,
                probabilidad_implicita: `${probImpVal.toFixed(1)}%`,
                probabilidad_estadistica: `${probabilidadVal.toFixed(1)}%`,
                fuente_principal: "Web Dashboard (Consenso)",
                valor: valorStr
            });

            cuotaTotal *= cuota;
            probEstCombinada *= (probabilidadVal / 100.0);
        });

        const nombre = type === "seguro" ? "Combinada Segura" : "Combinada de Alto Valor";
        const riesgo = type === "seguro" ? "Bajo" : "Alto";
        const stake = type === "seguro" ? "5/10 (Unidades)" : "1/10 (Unidades)";

        return {
            nombre: nombre,
            tipo_riesgo: riesgo,
            cuota_total_estimada: parseFloat(cuotaTotal.toFixed(2)),
            stake_sugerido: stake,
            probabilidad_implicta_cuota: `${((1.0 / cuotaTotal) * 100).toFixed(2)}%`,
            probabilidad_estadistica_combinada: `${(probEstCombinada * 100).toFixed(2)}%`,
            selecciones: selecciones
        };
    };

    // --- CARGAR Y RENDERIZAR DATOS ---
    const cargarYRenderizar = async () => {
        try {
            // Intentar cargar datos desde la API del servidor local
            const resBanca = await fetch("/api/banca");
            if (!resBanca.ok) throw new Error("HTTP error " + resBanca.status);
            dataBanca = await resBanca.json();
            console.log("📡 Datos en vivo cargados con éxito.");
        } catch (e) {
            console.warn("⚠️ Error al cargar API. Cargando datos demo offline:", e.message);
            // FALLBACK: Datos de demostración premium en caso de abrir directo file:// o desconexión
            dataBanca = {
                "banca": {
                    "banca_inicial": 10.0,
                    "banca_actual": 8.0,
                    "dinero_en_juego": 2.0
                },
                "estadisticas_globales": {
                    "total_apuestas_realizadas": 2,
                    "apuestas_ganadas": 0,
                    "apuestas_perdidas": 0,
                    "apuestas_anuladas": 0,
                    "rendimiento_yield": "0.0%",
                    "roi": "0.0%"
                },
                "apuestas_activas": [
                    {
                        "ticket_id": "DEMO-TKT-01",
                        "fecha_jornada": "2026-06-15",
                        "tipo_parley": "Combinada Segura",
                        "cuota": 2.27,
                        "inversion": 1.0,
                        "retorno_potencial": 2.27,
                        "estado": "Pendiente",
                        "selecciones": [
                            { "partido": "España vs. Cabo Verde", "pronostico": "España a Ganador (1X2)", "cuota": 1.15 },
                            { "partido": "Arabia Saudita vs. Uruguay", "pronostico": "Uruguay a Ganador (1X2)", "cuota": 1.35 },
                            { "partido": "Irán vs. Nueva Zelanda", "pronostico": "Irán o Empate (Doble Oportunidad)", "cuota": 1.20 },
                            { "partido": "Bélgica vs. Egipto", "pronostico": "Más de 1.5 goles", "cuota": 1.22 }
                        ]
                    },
                    {
                        "ticket_id": "DEMO-TKT-02",
                        "fecha_jornada": "2026-06-15",
                        "tipo_parley": "Combinada de Alto Valor",
                        "cuota": 11.64,
                        "inversion": 1.0,
                        "retorno_potencial": 11.64,
                        "estado": "Pendiente",
                        "selecciones": [
                            { "partido": "España vs. Cabo Verde", "pronostico": "España -2.0 Hándicap", "cuota": 1.85 },
                            { "partido": "Arabia Saudita vs. Uruguay", "pronostico": "Uruguay gana y Menos de 3.5 goles", "cuota": 1.95 },
                            { "partido": "Bélgica vs. Egipto", "pronostico": "Ambos Equipos Anotan (Sí)", "cuota": 1.90 },
                            { "partido": "Irán vs. Nueva Zelanda", "pronostico": "Irán a Ganador (1X2)", "cuota": 1.70 }
                        ]
                    }
                ],
                "apuestas_archivadas": []
            };
        }

        renderStats();
        renderActivePicks();
        renderSettledTickets();
        renderAdminTickets();
        renderChart();
    };

    const renderStats = () => {
        if (!dataBanca) return;
        const b = dataBanca.banca;
        const s = dataBanca.estadisticas_globales;
        
        elBancaInicial.textContent = `$${b.banca_inicial.toFixed(2)}`;
        elBancaDisponible.textContent = `$${b.banca_actual.toFixed(2)}`;
        elDineroJuego.textContent = `$${(b.dinero_en_juego || 0.0).toFixed(2)}`;
        elYield.textContent = s.rendimiento_yield;
        elRoi.textContent = s.roi;
        
        // Estilo de ROI positivo/negativo
        if (parseFloat(s.roi) > 0) {
            elRoi.style.color = "#10b981";
        } else if (parseFloat(s.roi) < 0) {
            elRoi.style.color = "#ef4444";
        } else {
            elRoi.style.color = "var(--text-primary)";
        }
    };

    const renderActivePicks = () => {
        if (!dataBanca) return;
        const activas = dataBanca.apuestas_activas || [];

        if (activas.length > 0) {
            containerPicks.innerHTML = "";
            activas.forEach(tkt => {
                const isSegura = tkt.tipo_parley.toLowerCase().includes("segura");
                const badgeClass = isSegura ? "" : "arriesgada";
                
                let html = `
                    <div class="ticket-card">
                        <div class="ticket-header">
                            <h3>🎫 Ticket ${tkt.ticket_id}</h3>
                            <span class="badge-status ${badgeClass}">${tkt.tipo_parley}</span>
                        </div>
                        <div class="selections-list">
                `;
                
                tkt.selecciones.forEach(sel => {
                    html += `
                        <div class="sel-item">
                            <span class="sel-match">${sel.partido}</span>
                            <span class="sel-pick">${sel.pronostico} (${sel.cuota.toFixed(2)})</span>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                        <div class="ticket-footer">
                            <span class="ticket-meta">Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b></span>
                            <span class="ticket-odds">Cuota: <b>x${tkt.cuota.toFixed(2)}</b> (Retorno: $${(tkt.retorno_potencial || 0).toFixed(2)})</span>
                        </div>
                    </div>
                `;
                containerPicks.innerHTML += html;
            });
        } else {
            containerPicks.innerHTML = `<p class="loading-text">💡 No tienes combinadas activas para hoy. Regístralas en la Consola Admin.</p>`;
        }
    };

    const renderSettledTickets = () => {
        if (!dataBanca) return;
        const archivadas = dataBanca.apuestas_archivadas || [];

        if (archivadas.length > 0) {
            containerSettled.innerHTML = "";
            archivadas.forEach(tkt => {
                const gano = tkt.estado === "Ganada";
                const anulo = tkt.estado === "Anulada";
                
                let classVal = "loss";
                let prefijo = "-$";
                let monto = tkt.inversion;
                
                if (gano) {
                    classVal = "win";
                    prefijo = "+$";
                    monto = tkt.retorno_realizado - tkt.inversion;
                } else if (anulo) {
                    classVal = "";
                    prefijo = "$";
                    monto = 0.0;
                }
                
                const txtMonto = `${prefijo}${Math.abs(monto).toFixed(2)}`;
                const ticketEstado = gano ? "✅ Acertado" : (anulo ? "🔄 Reembolsado" : "❌ Fallado");
                
                const html = `
                    <div class="settled-ticket">
                        <div class="settled-info">
                            <h4>Ticket ${tkt.ticket_id}</h4>
                            <p>${tkt.tipo_parley} | Jornada: ${tkt.fecha_jornada}</p>
                        </div>
                        <div class="settled-outcome">
                            <div class="outcome-val ${classVal}">${txtMonto} USD</div>
                            <div class="outcome-status">${ticketEstado}</div>
                        </div>
                    </div>
                `;
                containerSettled.innerHTML += html;
            });
        } else {
            containerSettled.innerHTML = `<p class="loading-text">⏳ Aún no hay apuestas asentadas en el historial.</p>`;
        }
    };

    // --- CARGAR TICKETS ACTIVOS EN EL PANEL ADMIN ---
    const renderAdminTickets = () => {
        if (!dataBanca) return;
        const activas = dataBanca.apuestas_activas || [];
        
        if (activas.length > 0) {
            containerAdminTickets.innerHTML = "";
            activas.forEach(tkt => {
                const card = document.createElement("div");
                card.className = "admin-ticket-card";
                card.innerHTML = `
                    <div class="admin-ticket-header">
                        <h4>🎫 Ticket ${tkt.ticket_id}</h4>
                        <span class="badge-status ${tkt.tipo_parley.toLowerCase().includes("segura") ? "" : "arriesgada"}">${tkt.tipo_parley}</span>
                    </div>
                    <p class="ticket-meta">
                        Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b> | Cuota: <b>x${tkt.cuota.toFixed(2)}</b>
                    </p>
                    <div class="settle-actions">
                        <button class="settle-btn btn-win" data-id="${tkt.ticket_id}" data-action="Ganada">Ganado</button>
                        <button class="settle-btn btn-loss" data-id="${tkt.ticket_id}" data-action="Perdida">Perdido</button>
                        <button class="settle-btn btn-void" data-id="${tkt.ticket_id}" data-action="Anulada">Anulado</button>
                    </div>
                `;
                
                // Eventos de liquidación directa
                card.querySelectorAll(".settle-btn").forEach(btn => {
                    btn.addEventListener("click", async () => {
                        const id = btn.getAttribute("data-id");
                        const estado = btn.getAttribute("data-action");
                        
                        if (confirm(`¿Estás seguro de liquidar el ticket ${id} como "${estado.toUpperCase()}"?`)) {
                            await liquidarTicket(id, estado);
                        }
                    });
                });

                containerAdminTickets.appendChild(card);
            });
        } else {
            containerAdminTickets.innerHTML = `<p class="loading-text">💡 No hay apuestas activas que asentar en este momento.</p>`;
        }
    };

    const liquidarTicket = async (ticketId, estado) => {
        try {
            const res = await fetch("/api/liquidar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ticket_id: ticketId, estado: estado })
            });

            if (res.ok) {
                const resJson = await res.json();
                alert(`🎉 ${resJson.message}`);
                await cargarYRenderizar();
            } else {
                const err = await res.text();
                alert("❌ Error al liquidar ticket: " + err);
            }
        } catch (err) {
            console.error(err);
            alert("❌ Error al comunicarse con el servidor.");
        }
    };

    // --- RENDERIZAR GRÁFICO DE CRECIMIENTO ---
    const renderChart = () => {
        const canvas = document.getElementById('growthChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        // Destruir instancia previa si existe para evitar problemas de redibujado
        if (window.growthChartInstance) {
            window.growthChartInstance.destroy();
        }

        // Construir línea de tiempo de la banca
        const labels = ["Inicio"];
        const chartData = [10.0];
        
        if (dataBanca && dataBanca.apuestas_archivadas) {
            let bancaAcumulada = 10.0;
            // Ordenar del más antiguo al más nuevo
            const archivadasOrdenadas = [...dataBanca.apuestas_archivadas].sort((a,b) => a.ticket_id.localeCompare(b.ticket_id));
            
            archivadasOrdenadas.forEach((tkt, idx) => {
                labels.push(`TKT ${idx + 1}`);
                if (tkt.estado === "Ganada") {
                    bancaAcumulada += (tkt.retorno_realizado - tkt.inversion);
                } else if (tkt.estado === "Perdida") {
                    bancaAcumulada -= tkt.inversion;
                }
                chartData.push(parseFloat(bancaAcumulada.toFixed(2)));
            });
        }

        const targetLine = Array(labels.length).fill(100.0);

        window.growthChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Mi Banca ($)',
                        data: chartData,
                        borderColor: '#0ea5e9',
                        backgroundColor: 'rgba(14, 165, 233, 0.15)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#0ea5e9'
                    },
                    {
                        label: 'Objetivo Final ($100)',
                        data: targetLine,
                        borderColor: 'rgba(239, 68, 68, 0.4)',
                        borderDash: [5, 5],
                        borderWidth: 1.5,
                        fill: false,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#9ca3af',
                            font: { family: 'Inter' }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.04)' },
                        ticks: { color: '#9ca3af', font: { family: 'Inter' } }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.04)' },
                        ticks: { color: '#9ca3af', font: { family: 'Inter' } }
                    }
                }
            }
        });
    };

    // --- INICIALIZACIÓN ---
    setupTabs();
    setupForm();
    await cargarYRenderizar();
});
