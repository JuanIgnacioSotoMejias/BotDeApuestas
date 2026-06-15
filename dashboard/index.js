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
    
    // Elementos de la vista Admin/Predicciones
    const panelVisual = document.getElementById("visual-panel");
    const panelParleys = document.getElementById("parleys-panel");
    const panelPredictions = document.getElementById("predictions-panel");
    const panelAdmin = document.getElementById("admin-panel");
    
    const tabVisualBtn = document.getElementById("tab-btn-visual");
    const tabParleysBtn = document.getElementById("tab-btn-parleys");
    const tabPredictionsBtn = document.getElementById("tab-btn-predictions");
    const tabAdminBtn = document.getElementById("tab-btn-admin");
    
    const containerParleysHistory = document.getElementById("parleys-history-container");
    let parleyFilter = "all";
    
    const containerAdminTickets = document.getElementById("admin-active-tickets-list");
    const containerProposedPicks = document.getElementById("proposed-picks-container");
    const cardProposedPicks = document.getElementById("proposed-picks-card");
    const predictionsTbody = document.getElementById("predictions-tbody");
    
    const btnActualizarResultados = document.getElementById("btn-actualizar-resultados");
    const formAjusteBanca = document.getElementById("ajuste-banca-form");
    
    // Formularios e inputs
    const formCrearPicks = document.getElementById("crear-picks-form");
    const inputFecha = document.getElementById("form-fecha");
    const inputDesc = document.getElementById("form-desc");
    const containerSeguro = document.getElementById("seguro-selections-container");
    const containerArriesgado = document.getElementById("arriesgado-selections-container");
    const addSelectionBtns = document.querySelectorAll(".add-selection-btn");

    let dataBanca = null;

    // Conversión de Cuota Decimal a Americana
    const decimalToAmerican = (odd) => {
        if (!odd || odd <= 1.0) return "";
        if (odd >= 2.0) {
            return `+${Math.round((odd - 1.0) * 100)}`;
        } else {
            return `${Math.round(-100 / (odd - 1.0))}`;
        }
    };

    // Configurar fecha por defecto (Hoy)
    const hoy = new Date().toISOString().split('T')[0];
    inputFecha.value = hoy;
    inputDesc.value = `Jornada ${hoy}`;

    // --- TAB SYSTEM LÓGICA ---
    const setupTabs = () => {
        const tabs = [
            { btn: tabVisualBtn, panel: panelVisual },
            { btn: tabParleysBtn, panel: panelParleys },
            { btn: tabPredictionsBtn, panel: panelPredictions },
            { btn: tabAdminBtn, panel: panelAdmin }
        ];

        tabs.forEach(tab => {
            tab.btn.addEventListener("click", () => {
                tabs.forEach(t => {
                    t.btn.classList.remove("active");
                    t.panel.style.display = "none";
                });
                tab.btn.classList.add("active");
                tab.panel.style.display = "grid";
            });
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

        const btnLimpiarPredicciones = document.getElementById("btn-limpiar-predicciones");
        if (btnLimpiarPredicciones) {
            btnLimpiarPredicciones.addEventListener("click", async () => {
                if (!confirm("🧹 ¿Estás seguro de que deseas eliminar permanentemente todas las predicciones de IA de la base de datos? Esta acción no se puede deshacer y afectará tanto local como producción.")) {
                    return;
                }
                
                const originalText = btnLimpiarPredicciones.textContent;
                btnLimpiarPredicciones.textContent = "⏳ Limpiando...";
                btnLimpiarPredicciones.disabled = true;
                
                try {
                    const res = await fetch("/api/predicciones/limpiar", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });
                    
                    if (res.ok) {
                        const data = await res.json();
                        alert("✅ " + data.message);
                        await cargarYRenderizar();
                    } else {
                        const err = await res.text();
                        alert("❌ Error al limpiar predicciones: " + err);
                    }
                } catch (e) {
                    console.error(e);
                    alert("❌ Error de comunicación con el servidor.");
                } finally {
                    btnLimpiarPredicciones.textContent = originalText;
                    btnLimpiarPredicciones.disabled = false;
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
        renderProposedPicks();
        renderActivePicks();
        renderSettledTickets();
        renderAdminTickets();
        renderPredictionsTable();
        renderParleysHistory();
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

    const renderProposedPicks = () => {
        if (!dataBanca) return;
        const propuestas = dataBanca.propuestas_hoy;
        const predicciones = dataBanca.predicciones_ia || [];

        containerProposedPicks.innerHTML = "";

        if (propuestas && propuestas.parleys) {
            let parleysFound = false;

            Object.keys(propuestas.parleys).forEach(key => {
                const parley = propuestas.parleys[key];
                if (!parley || !parley.selecciones || parley.selecciones.length === 0) return;

                // Verificar si alguno de los partidos en el parley ya terminó
                let algunPartidoTerminado = false;
                parley.selecciones.forEach(sel => {
                    const matchingPred = predicciones.find(p => p.partido === sel.partido);
                    if (matchingPred && matchingPred.estado !== "Pendiente") {
                        algunPartidoTerminado = true;
                    }
                });

                if (algunPartidoTerminado) {
                    console.log(`🚫 Omitiendo combinada "${parley.nombre}" porque contiene partidos ya finalizados.`);
                    return; // Saltar renderizado
                }

                parleysFound = true;

                const isSegura = parley.nombre.toLowerCase().includes("segura");
                const badgeClass = isSegura ? "" : "arriesgada";
                const cuotaTotal = parseFloat(parley.cuota_total_estimada);

                let html = `
                    <div class="ticket-card" style="border-left: 3px solid ${isSegura ? 'var(--accent-green)' : 'var(--accent-red)'}; margin-bottom: 15px;">
                        <div class="ticket-header">
                            <h3>🤖 ${parley.nombre}</h3>
                            <span class="badge-status ${badgeClass}">${parley.tipo_riesgo || (isSegura ? 'Bajo Riesgo' : 'Alto Riesgo')}</span>
                        </div>
                        <div class="selections-list">
                `;

                parley.selecciones.forEach(sel => {
                    const cuotaDec = parseFloat(sel.cuota);
                    html += `
                        <div class="sel-item">
                            <span class="sel-match">${sel.partido}</span>
                            <span class="sel-pick">${sel.pronostico} (<b>x${cuotaDec.toFixed(2)} / ${decimalToAmerican(cuotaDec)}</b>)</span>
                        </div>
                    `;
                });

                html += `
                        </div>
                        <div class="ticket-footer" style="flex-direction: column; align-items: stretch; gap: 12px; background: rgba(255,255,255,0.01);">
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-secondary);">
                                <span>Cuota Combinada: <b style="color: var(--accent-blue);">x${cuotaTotal.toFixed(2)} (${decimalToAmerican(cuotaTotal)})</b></span>
                                <span>Prob. Combinada: <b>${parley.probabilidad_estadistica_combinada || 'N/A'}</b></span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-top: 5px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <label style="font-size: 0.8rem; color: var(--text-secondary); white-space: nowrap; margin-bottom: 0;">Inversión ($):</label>
                                    <input type="number" class="stake-input" value="1.00" step="0.50" min="0.10" style="width: 75px; background: rgba(255,255,255,0.03); border: 1px solid var(--card-border); color: #fff; padding: 6px 10px; border-radius: 6px; font-size: 0.85rem; outline: none;">
                                </div>
                                <button class="btn-primary btn-jugar-parley" style="padding: 6px 16px; font-size: 0.85rem; background: linear-gradient(135deg, var(--accent-purple) 0%, #6d28d9 100%); flex: 1;">🎮 Jugar Parley</button>
                            </div>
                        </div>
                    </div>
                `;

                const cardDom = document.createElement("div");
                cardDom.innerHTML = html;

                const btnJugar = cardDom.querySelector(".btn-jugar-parley");
                const inputStake = cardDom.querySelector(".stake-input");

                btnJugar.addEventListener("click", async () => {
                    const stakeVal = parseFloat(inputStake.value);
                    if (isNaN(stakeVal) || stakeVal <= 0) {
                        alert("❌ Por favor ingresa un monto de inversión válido.");
                        return;
                    }

                    if (confirm(`¿Confirmas que deseas jugar $${stakeVal.toFixed(2)} USD en la combinada "${parley.nombre}"?`)) {
                        btnJugar.textContent = "⏳ Procesando...";
                        btnJugar.disabled = true;

                        try {
                            const res = await fetch("/api/jugar_ticket", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    tipo_parley: parley.nombre,
                                    inversion: stakeVal,
                                    cuota: cuotaTotal,
                                    selecciones: parley.selecciones
                                })
                            });

                            if (res.ok) {
                                const resJson = await res.json();
                                alert(`🎉 ${resJson.message}`);
                                await cargarYRenderizar();
                            } else {
                                const errData = await res.json().catch(() => ({}));
                                const errMsg = errData.error || "Error al colocar apuesta.";
                                alert(`❌ ${errMsg}`);
                            }
                        } catch (err) {
                            console.error(err);
                            alert("❌ Error de comunicación con la API del Servidor.");
                        } finally {
                            btnJugar.textContent = "🎮 Jugar Parley";
                            btnJugar.disabled = false;
                        }
                    }
                });

                containerProposedPicks.appendChild(cardDom.firstElementChild);
            });

            if (!parleysFound) {
                containerProposedPicks.innerHTML = `<p class="loading-text">💡 No hay combinadas sugeridas para hoy. Utiliza el botón "Generar con IA" en la Consola Admin.</p>`;
            }
        } else {
            containerProposedPicks.innerHTML = `<p class="loading-text">💡 No hay combinadas sugeridas para hoy. Utiliza el botón "Generar con IA" en la Consola Admin.</p>`;
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
                    <div class="ticket-card" style="margin-bottom: 15px;">
                        <div class="ticket-header">
                            <h3>🎫 Ticket ${tkt.ticket_id}</h3>
                            <span class="badge-status ${badgeClass}">${tkt.tipo_parley}</span>
                        </div>
                        <div class="selections-list">
                `;
                
                tkt.selecciones.forEach(sel => {
                    const cuotaDec = parseFloat(sel.cuota);
                    html += `
                        <div class="sel-item">
                            <span class="sel-match">${sel.partido}</span>
                            <span class="sel-pick">${sel.pronostico} (<b>x${cuotaDec.toFixed(2)} / ${decimalToAmerican(cuotaDec)}</b>)</span>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                        <div class="ticket-footer">
                            <span class="ticket-meta">Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b></span>
                            <span class="ticket-odds">Cuota: <b>x${tkt.cuota.toFixed(2)} (${decimalToAmerican(tkt.cuota)})</b> (Retorno: $${(tkt.retorno_potencial || 0).toFixed(2)})</span>
                        </div>
                    </div>
                `;
                containerPicks.innerHTML += html;
            });
        } else {
            containerPicks.innerHTML = `<p class="loading-text">💡 No tienes combinadas activas para hoy. Juega las propuestas de la IA o regístralas en la Consola Admin.</p>`;
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
                            <p>${tkt.tipo_parley} | Jornada: ${tkt.fecha_jornada} | Cuota: x${tkt.cuota.toFixed(2)} (${decimalToAmerican(tkt.cuota)})</p>
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
                        Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b> | Cuota: <b>x${tkt.cuota.toFixed(2)} (${decimalToAmerican(tkt.cuota)})</b>
                    </p>
                    <div class="settle-actions">
                        <button class="settle-btn btn-win" data-id="${tkt.ticket_id}" data-action="Ganada">Ganado</button>
                        <button class="settle-btn btn-loss" data-id="${tkt.ticket_id}" data-action="Perdida">Perdido</button>
                        <button class="settle-btn btn-void" data-id="${tkt.ticket_id}" data-action="Anulada">Anulado</button>
                    </div>
                `;
                
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

    const renderPredictionsTable = () => {
        if (!dataBanca) return;
        const preds = dataBanca.predicciones_ia || [];
        predictionsTbody.innerHTML = "";

        if (preds.length > 0) {
            preds.forEach(p => {
                const tr = document.createElement("tr");
                tr.style.borderBottom = "1px solid rgba(255, 255, 255, 0.05)";

                const badgeState = p.estado === "Ganado" ? "badge-status" : (p.estado === "Perdido" ? "badge-status arriesgada" : "badge-status");
                const stateStyle = p.estado === "Ganado" ? "" : (p.estado === "Perdido" ? "" : "background: rgba(156,163,175,0.15); color: #9ca3af;");
                
                const fechaFmt = p.fecha ? p.fecha.split("T")[0] : "-";
                const cuotaDec = parseFloat(p.cuota);
                
                tr.innerHTML = `
                    <td style="padding: 12px 10px; font-weight: 500; color: var(--text-secondary);">${fechaFmt}</td>
                    <td style="padding: 12px 10px; font-weight: 600;">${p.partido}</td>
                    <td style="padding: 12px 10px; color: var(--accent-blue); font-weight: 500;">${p.pronostico}</td>
                    <td style="padding: 12px 10px; font-weight: 500;">x${cuotaDec.toFixed(2)} (${decimalToAmerican(cuotaDec)})</td>
                    <td style="padding: 12px 10px; text-align: center;">${p.probabilidad_estadistica}%</td>
                    <td style="padding: 12px 10px; text-align: center;">${p.probabilidad_implicita}%</td>
                    <td style="padding: 12px 10px; color: var(--accent-green); font-weight: 600;">${p.valor}</td>
                    <td style="padding: 12px 10px; color: var(--text-secondary);">${p.tipo_parley}</td>
                    <td style="padding: 12px 10px;"><span class="${badgeState}" style="${stateStyle}">${p.estado}</span></td>
                    <td style="padding: 12px 10px; font-weight: 700; color: var(--accent-purple);">${p.resultado_partido || "-"}</td>
                `;
                predictionsTbody.appendChild(tr);
            });
        } else {
            predictionsTbody.innerHTML = `
                <tr>
                    <td colspan="10" class="loading-text" style="text-align: center; padding: 20px;">No hay predicciones registradas en la base de datos.</td>
                </tr>
            `;
        }
    };

    const setupParleyFilters = () => {
        const filterBtns = document.querySelectorAll(".filter-parley-btn");
        filterBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                filterBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                parleyFilter = btn.getAttribute("data-filter");
                renderParleysHistory();
            });
        });
    };

    const renderParleysHistory = () => {
        if (!dataBanca) return;
        const activas = dataBanca.apuestas_activas || [];
        const archivadas = dataBanca.apuestas_archivadas || [];
        
        let todos = [...activas, ...archivadas];
        todos.sort((a, b) => b.ticket_id.localeCompare(a.ticket_id));
        
        if (parleyFilter !== "all") {
            todos = todos.filter(t => t.estado === parleyFilter);
        }
        
        containerParleysHistory.innerHTML = "";
        
        if (todos.length === 0) {
            containerParleysHistory.innerHTML = `<p class="loading-text">💡 No se encontraron parleys con el estado seleccionado.</p>`;
            return;
        }
        
        todos.forEach(tkt => {
            const isSegura = tkt.tipo_parley.toLowerCase().includes("segura");
            const isGanada = tkt.estado === "Ganada";
            const isPerdida = tkt.estado === "Perdida";
            const isAnulada = tkt.estado === "Anulada";
            
            let statusBadgeHtml = "";
            let leftBorderColor = "var(--text-muted)";
            let profitText = "";
            let profitClass = "";
            
            if (isGanada) {
                statusBadgeHtml = `<span class="badge-status">✅ Ganada</span>`;
                leftBorderColor = "var(--accent-green)";
                const netWin = tkt.retorno_realizado - tkt.inversion;
                profitText = `Resultado: <b>+${netWin.toFixed(2)} USD (Ganancia)</b>`;
                profitClass = "color: var(--accent-green);";
            } else if (isPerdida) {
                statusBadgeHtml = `<span class="badge-status arriesgada">❌ Perdida</span>`;
                leftBorderColor = "var(--accent-red)";
                profitText = `Resultado: <b>-${tkt.inversion.toFixed(2)} USD (Pérdida)</b>`;
                profitClass = "color: var(--accent-red);";
            } else if (isAnulada) {
                statusBadgeHtml = `<span class="badge-status" style="background: rgba(156,163,175,0.2); color: #9ca3af;">🔄 Anulada</span>`;
                leftBorderColor = "var(--text-muted)";
                profitText = `Resultado: <b>$0.00 USD (Reembolsado)</b>`;
                profitClass = "color: var(--text-secondary);";
            } else {
                statusBadgeHtml = `<span class="badge-status" style="background: rgba(14,165,233,0.2); color: var(--accent-blue);">⏳ Pendiente</span>`;
                leftBorderColor = "var(--accent-blue)";
                profitText = `Retorno Potencial: <b>$${tkt.retorno_potencial.toFixed(2)} USD</b>`;
                profitClass = "color: var(--accent-blue);";
            }
            
            let html = `
                <div class="ticket-card" style="border-left: 3px solid ${leftBorderColor}; margin-bottom: 15px;">
                    <div class="ticket-header">
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            <h3 style="font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 700;">🎫 Ticket ${tkt.ticket_id}</h3>
                            <span style="font-size: 0.75rem; color: var(--text-secondary);">${tkt.tipo_parley} | Jornada: ${tkt.fecha_jornada}</span>
                        </div>
                        ${statusBadgeHtml}
                    </div>
                    <div class="selections-list">
            `;
            
            tkt.selecciones.forEach(sel => {
                const cuotaDec = parseFloat(sel.cuota);
                const selEstado = sel.estado_seleccion || "Pendiente";
                
                let selBadge = "";
                if (selEstado === "Ganado") {
                    selBadge = `<span style="color: var(--accent-green); font-weight: bold;">✅ Ganado</span>`;
                } else if (selEstado === "Perdido") {
                    selBadge = `<span style="color: var(--accent-red); font-weight: bold;">❌ Perdido</span>`;
                } else if (selEstado === "Anulado") {
                    selBadge = `<span style="color: #9ca3af; font-weight: bold;">🔄 Anulado</span>`;
                } else {
                    selBadge = `<span style="color: var(--accent-blue); font-weight: bold;">⏳ Pendiente</span>`;
                }
                
                const scoreStr = sel.resultado_partido ? `<span style="background: rgba(139,92,246,0.15); color: var(--accent-purple); padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-left: 8px; font-size: 0.8rem;">${sel.resultado_partido}</span>` : "";
                
                html += `
                    <div class="sel-item" style="border-bottom: 1px solid rgba(255,255,255,0.02); padding-bottom: 8px; margin-bottom: 8px;">
                        <div style="display: flex; flex-direction: column; gap: 2px;">
                            <span class="sel-match" style="font-weight: 600; color: var(--text-primary);">${sel.partido}${scoreStr}</span>
                            <span class="sel-pick" style="font-size: 0.8rem; color: var(--text-secondary);">${sel.pronostico} (<b>x${cuotaDec.toFixed(2)} / ${decimalToAmerican(cuotaDec)}</b>)</span>
                        </div>
                        <div style="align-self: center; font-size: 0.85rem;">
                            ${selBadge}
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                    <div class="ticket-footer" style="background: rgba(255,255,255,0.01); border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 12px; margin-top: 12px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                        <span class="ticket-meta">Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b> | Cuota Combinada: <b>x${tkt.cuota.toFixed(2)} (${decimalToAmerican(tkt.cuota)})</b></span>
                        <span class="ticket-odds" style="${profitClass}">${profitText}</span>
                    </div>
                </div>
            `;
            
            containerParleysHistory.innerHTML += html;
        });
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

    // --- ELEMENTOS INTERACTIVOS: BANCA Y MARCADORES ---
    const setupInteractiveElements = () => {
        if (formAjusteBanca) {
            formAjusteBanca.addEventListener("submit", async (e) => {
                e.preventDefault();
                const tipo = document.getElementById("ajuste-tipo").value;
                const monto = parseFloat(document.getElementById("ajuste-monto").value);
                const desc = document.getElementById("ajuste-desc").value.trim();

                if (isNaN(monto) || monto <= 0) {
                    alert("❌ Por favor ingresa un monto válido mayor a cero.");
                    return;
                }

                const btnSubmit = formAjusteBanca.querySelector("button[type='submit']");
                const originalText = btnSubmit.textContent;
                btnSubmit.textContent = "⏳ Aplicando...";
                btnSubmit.disabled = true;

                try {
                    const res = await fetch("/api/banca/ajustar", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ tipo, monto, descripcion: desc })
                    });

                    if (res.ok) {
                        const resJson = await res.json();
                        alert(`🎉 ${resJson.message}`);
                        formAjusteBanca.reset();
                        await cargarYRenderizar();
                    } else {
                        const err = await res.text();
                        alert(`❌ Error al ajustar banca: ${err}`);
                    }
                } catch (err) {
                    console.error(err);
                    alert("❌ Error de comunicación con la API.");
                } finally {
                    btnSubmit.textContent = originalText;
                    btnSubmit.disabled = false;
                }
            });
        }

        if (btnActualizarResultados) {
            btnActualizarResultados.addEventListener("click", async () => {
                const originalText = btnActualizarResultados.textContent;
                btnActualizarResultados.textContent = "⏳ Sincronizando Marcadores...";
                btnActualizarResultados.disabled = true;

                try {
                    const res = await fetch("/api/actualizar_resultados", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });

                    if (res.ok) {
                        const resJson = await res.json();
                        const r = resJson.resumen;
                        let msg = "Sincronización completada.\n";
                        if (r.apuestas_liquidadas.length > 0) {
                            msg += `🎫 Apuestas liquidadas: ${r.apuestas_liquidadas.join(", ")}\n`;
                        } else {
                            msg += "🎫 Sin apuestas liquidadas.\n";
                        }
                        if (r.predicciones_liquidadas.length > 0) {
                            msg += `🤖 Predicciones liquidadas: ${r.predicciones_liquidadas.length}\n`;
                        } else {
                            msg += "🤖 Sin predicciones liquidadas.\n";
                        }
                        alert(`🔄 ${msg}`);
                        await cargarYRenderizar();
                    } else {
                        const err = await res.text();
                        alert(`❌ Error al actualizar marcadores: ${err}`);
                    }
                } catch (err) {
                    console.error(err);
                    alert("❌ Error de comunicación con la API de actualización.");
                } finally {
                    btnActualizarResultados.textContent = originalText;
                    btnActualizarResultados.disabled = false;
                }
            });
        }
    };

    // --- INICIALIZACIÓN ---
    setupTabs();
    setupParleyFilters();
    setupForm();
    setupInteractiveElements();
    await cargarYRenderizar();
});
