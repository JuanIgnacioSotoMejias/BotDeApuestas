// 🏆 LÓGICA DEL DASHBOARD INTERACTIVO Y CONSOLA DE ADMINISTRACIÓN (PREMIUM)

window.growthChartInstance = null;
window.projectedLabels = null;
window.projectedSeries = null;

document.addEventListener("DOMContentLoaded", async () => {
    // Inicializar elementos de UI
    const elBancaInicial = document.getElementById("banca-inicial");
    const elBancaDisponible = document.getElementById("banca-disponible");
    const elDineroJuego = document.getElementById("dinero-juego");
    const elYield = document.getElementById("yield-stats");
    const elRoi = document.getElementById("roi-stats");
    const containerPicks = document.getElementById("active-picks-container");
    const containerSettled = document.getElementById("settled-tickets-container");
    
    // Elementos de la vista Admin/Predicciones/Quiniela
    const panelVisual = document.getElementById("visual-panel");
    const panelParleys = document.getElementById("parleys-panel");
    const panelPredictions = document.getElementById("predictions-panel");
    const panelQuiniela = document.getElementById("quiniela-panel");
    const panelAdmin = document.getElementById("admin-panel");
    
    const tabVisualBtn = document.getElementById("tab-btn-visual");
    const tabParleysBtn = document.getElementById("tab-btn-parleys");
    const tabPredictionsBtn = document.getElementById("tab-btn-predictions");
    const tabQuinielaBtn = document.getElementById("tab-btn-quiniela");
    const tabAdminBtn = document.getElementById("tab-btn-admin");

    // Elementos de Quiniela IA
    const containerQuinielaMatches = document.getElementById("quiniela-matches-list");
    const btnCalcularQuiniela = document.getElementById("btn-calcular-quiniela");
    const containerQuinielaCombinations = document.getElementById("quiniela-combinations-container");
    const quinielaIndividualTbody = document.getElementById("quiniela-individual-tbody");
    const btnRecargarPartidosQuiniela = document.getElementById("btn-recargar-partidos-quiniela");
    const btnSelectAllQuiniela = document.getElementById("btn-select-all-quiniela");
    const btnDeselectAllQuiniela = document.getElementById("btn-deselect-all-quiniela");
    const inputManualLocal = document.getElementById("manual-local");
    const inputManualVisitante = document.getElementById("manual-visitante");
    const btnAddManualMatch = document.getElementById("btn-add-manual-match");
    
    const containerParleysHistory = document.getElementById("parleys-history-container");
    let parleyFilter = "all";
    
    // Variables de paginación
    let parleysCurrentPage = 1;
    const parleysPageSize = 5;
    let predictionsCurrentPage = 1;
    const predictionsPageSize = 10;
    
    // Controles de paginación
    const parleysPaginationDiv = document.getElementById("parleys-pagination");
    const parleysPrevBtn = document.getElementById("parleys-prev-btn");
    const parleysNextBtn = document.getElementById("parleys-next-btn");
    const parleysPageInfo = document.getElementById("parleys-page-info");
    
    const predictionsPaginationDiv = document.getElementById("predictions-pagination");
    const predictionsPrevBtn = document.getElementById("predictions-prev-btn");
    const predictionsNextBtn = document.getElementById("predictions-next-btn");
    const predictionsPageInfo = document.getElementById("predictions-page-info");
    
    const containerAdminTickets = document.getElementById("admin-active-tickets-list");
    const containerProposedPicks = document.getElementById("proposed-picks-container");
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

    // --- SYSTEMA DE TOAST NOTIFICATIONS ---
    const showToast = (message, type = "info") => {
        const container = document.getElementById("toast-container");
        if (!container) return;
        
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let icon = "💡";
        if (type === "success") icon = "✅";
        if (type === "error") icon = "❌";
        
        toast.innerHTML = `
            <div style="font-size: 1.2rem; display: flex; align-items: center;">${icon}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" aria-label="Cerrar">&times;</button>
        `;
        
        container.appendChild(toast);
        setTimeout(() => toast.classList.add("show"), 50);
        
        const closeToast = () => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 400);
        };
        
        toast.querySelector(".toast-close").addEventListener("click", closeToast);
        setTimeout(closeToast, 4000);
    };

    // --- SYSTEMA DE MODALES PERSONALIZADOS ---
    const showModal = (title, message, onConfirm, onCancel = null) => {
        const modal = document.getElementById("custom-modal");
        const elTitle = document.getElementById("modal-title");
        const elMessage = document.getElementById("modal-message");
        const btnConfirm = document.getElementById("modal-btn-confirm");
        const btnCancel = document.getElementById("modal-btn-cancel");
        const btnClose = document.getElementById("modal-close-btn");
        
        if (!modal) return;
        
        elTitle.textContent = title;
        elMessage.textContent = message;
        
        modal.style.display = "flex";
        setTimeout(() => modal.classList.add("show"), 50);
        
        const cleanup = () => {
            modal.classList.remove("show");
            setTimeout(() => {
                modal.style.display = "none";
            }, 300);
        };
        
        const handleConfirm = () => {
            cleanup();
            if (onConfirm) onConfirm();
        };
        
        const handleCancel = () => {
            cleanup();
            if (onCancel) onCancel();
        };
        
        // Clonar para limpiar listeners anteriores
        const newConfirm = btnConfirm.cloneNode(true);
        const newCancel = btnCancel.cloneNode(true);
        const newClose = btnClose.cloneNode(true);
        
        btnConfirm.parentNode.replaceChild(newConfirm, btnConfirm);
        btnCancel.parentNode.replaceChild(newCancel, btnCancel);
        btnClose.parentNode.replaceChild(newClose, btnClose);
        
        newConfirm.addEventListener("click", handleConfirm);
        newCancel.addEventListener("click", handleCancel);
        newClose.addEventListener("click", handleCancel);
    };

    const askConfirmation = (title, message) => {
        return new Promise((resolve) => {
            showModal(title, message, () => resolve(true), () => resolve(false));
        });
    };

    // --- SELECTOR DE FORMATO DE CUOTAS ---
    let currentOddsFormat = "decimal";

    const formatOdds = (odd) => {
        if (!odd || odd <= 1.0) return "";
        const val = parseFloat(odd);
        if (currentOddsFormat === "decimal") {
            return `x${val.toFixed(2)}`;
        } else {
            // Cuota Americana
            if (val >= 2.0) {
                return `+${Math.round((val - 1.0) * 100)}`;
            } else {
                return `${Math.round(-100 / (val - 1.0))}`;
            }
        }
    };

    const setupOddsToggle = () => {
        const btnDec = document.getElementById("toggle-odds-dec");
        const btnAme = document.getElementById("toggle-odds-ame");
        
        if (!btnDec || !btnAme) return;
        
        btnDec.addEventListener("click", () => {
            if (currentOddsFormat === "decimal") return;
            currentOddsFormat = "decimal";
            btnDec.classList.add("active");
            btnAme.classList.remove("active");
            cargarYRenderizar();
            showToast("Cuotas cambiadas a formato Decimal.", "info");
        });
        
        btnAme.addEventListener("click", () => {
            if (currentOddsFormat === "american") return;
            currentOddsFormat = "american";
            btnAme.classList.add("active");
            btnDec.classList.remove("active");
            cargarYRenderizar();
            showToast("Cuotas cambiadas a formato Americano.", "info");
        });
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
            { btn: tabQuinielaBtn, panel: panelQuiniela },
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
                
                // Acciones específicas de pestañas
                if (tab.btn === tabAdminBtn) {
                    cargarYRenderizarLogsIA();
                } else if (tab.btn === tabQuinielaBtn) {
                    cargarPartidosQuiniela();
                }
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

        row.querySelector(".remove-row-btn").addEventListener("click", () => {
            row.remove();
        });

        return row;
    };

    const setupForm = () => {
        const btnGenerarIa = document.getElementById("btn-generar-ia");
        if (btnGenerarIa) {
            btnGenerarIa.addEventListener("click", async () => {
                const confirmed = await askConfirmation("🤖 Generar con IA", "¿Deseas activar a los agentes de IA para buscar, analizar y generar automáticamente los parleys oficiales de hoy?");
                if (!confirmed) return;
                
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
                        showToast(data.message, "success");
                        await cargarYRenderizar();
                        tabVisualBtn.click();
                    } else {
                        const err = await res.text();
                        showToast("Error al generar picks con agentes: " + err, "error");
                    }
                } catch (e) {
                    console.error(e);
                    showToast("Error al comunicarse con la API de generación.", "error");
                } finally {
                    btnGenerarIa.textContent = originalText;
                    btnGenerarIa.disabled = false;
                }
            });
        }

        const btnLimpiarPredicciones = document.getElementById("btn-limpiar-predicciones");
        if (btnLimpiarPredicciones) {
            btnLimpiarPredicciones.addEventListener("click", async () => {
                const confirmed = await askConfirmation("🧹 Limpiar Predicciones", "¿Estás seguro de que deseas eliminar permanentemente todas las predicciones de IA de la base de datos? Esta acción no se puede deshacer.");
                if (!confirmed) return;
                
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
                        showToast(data.message, "success");
                        await cargarYRenderizar();
                    } else {
                        const err = await res.text();
                        showToast("Error al limpiar predicciones: " + err, "error");
                    }
                } catch (e) {
                    console.error(e);
                    showToast("Error de comunicación con el servidor.", "error");
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
            submitBtn.textContent = "⏳ Registrando...";
            submitBtn.disabled = true;

            try {
                const parleySeguroData = processSelections("seguro");
                const parleyArriesgadoData = processSelections("arriesgado");

                if (!parleySeguroData || !parleyArriesgadoData) {
                    showToast("Debes agregar al menos una selección válida en cada combinada.", "error");
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
                    showToast(resJson.message, "success");
                    
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
                    showToast("Error al registrar picks: " + err, "error");
                }
            } catch (err) {
                console.error(err);
                showToast("Error de comunicación con la API del Servidor.", "error");
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
        
        const partidosSet = new Set();
        let duplicateFound = false;
        let duplicateName = "";

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const partido = row.querySelector(".sel-partido").value.trim();
            const pronostico = row.querySelector(".sel-pronostico").value.trim();
            const cuota = parseFloat(row.querySelector(".sel-cuota").value);
            const probabilidadVal = parseFloat(row.querySelector(".sel-probabilidad").value);

            if (partido) {
                // Normalizar nombre de partido para evitar diferencias en espacios, puntos, etc.
                const partidoNorm = partido.toLowerCase()
                    .replace(/\./g, "")
                    .replace(/\s+/g, " ")
                    .replace(/ vs /g, " vs. ")
                    .trim();
                
                if (partidosSet.has(partidoNorm)) {
                    duplicateFound = true;
                    duplicateName = partido;
                    break;
                }
                partidosSet.add(partidoNorm);
            }

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
        }

        if (duplicateFound) {
            showToast(`No se permite repetir el mismo partido en una combinada: ${duplicateName}`, "error");
            return null;
        }

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
                "apuestas_archivadas": [],
                "predicciones_ia": []
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
                    return; 
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
                            <span class="sel-pick">${sel.pronostico} (<b>${formatOdds(cuotaDec)}</b>)</span>
                        </div>
                    `;
                });

                html += `
                        </div>
                        <div class="ticket-footer" style="flex-direction: column; align-items: stretch; gap: 12px; background: rgba(255,255,255,0.01);">
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-secondary);">
                                <span>Cuota Combinada: <b style="color: var(--accent-blue);">${formatOdds(cuotaTotal)}</b></span>
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
                        showToast("Por favor ingresa un monto de inversión válido.", "error");
                        return;
                    }

                    const confirmed = await askConfirmation("🎮 Jugar Combinada", `¿Confirmas que deseas jugar $${stakeVal.toFixed(2)} USD en la combinada "${parley.nombre}"?`);
                    if (confirmed) {
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
                                showToast(resJson.message, "success");
                                await cargarYRenderizar();
                            } else {
                                const errData = await res.json().catch(() => ({}));
                                const errMsg = errData.error || "Error al colocar apuesta.";
                                showToast(errMsg, "error");
                            }
                        } catch (err) {
                            console.error(err);
                            showToast("Error de comunicación con la API del Servidor.", "error");
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
                            <span class="sel-pick">${sel.pronostico} (<b>${formatOdds(cuotaDec)}</b>)</span>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                        <div class="ticket-footer">
                            <span class="ticket-meta">Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b></span>
                            <span class="ticket-odds">Cuota: <b>${formatOdds(tkt.cuota)}</b> (Retorno: $${(tkt.retorno_potencial || 0).toFixed(2)})</span>
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
                            <p>${tkt.tipo_parley} | Jornada: ${tkt.fecha_jornada} | Cuota: ${formatOdds(tkt.cuota)}</p>
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
                        Inversión: <b>$${tkt.inversion.toFixed(2)} USD</b> | Cuota: <b>${formatOdds(tkt.cuota)}</b>
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
                        
                        const confirmed = await askConfirmation("⚙️ Liquidar Ticket", `¿Estás seguro de liquidar el ticket ${id} como "${estado.toUpperCase()}"?`);
                        if (confirmed) {
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

        // Capturar filtros
        const searchInput = document.getElementById("search-prediccion");
        const filterStatus = document.getElementById("filter-prediccion-estado");
        const filterType = document.getElementById("filter-prediccion-tipo");
        
        let filteredPreds = [...preds];
        
        if (searchInput && searchInput.value.trim() !== "") {
            const query = searchInput.value.toLowerCase().trim();
            filteredPreds = filteredPreds.filter(p => 
                (p.partido && p.partido.toLowerCase().includes(query)) ||
                (p.pronostico && p.pronostico.toLowerCase().includes(query))
            );
        }
        
        if (filterStatus && filterStatus.value !== "all") {
            const statusVal = filterStatus.value;
            filteredPreds = filteredPreds.filter(p => p.estado === statusVal);
        }
        
        if (filterType && filterType.value !== "all") {
            const typeVal = filterType.value.toLowerCase();
            filteredPreds = filteredPreds.filter(p => {
                const pType = (p.tipo_parley || "").toLowerCase();
                return pType.includes(typeVal);
            });
        }

        const totalItems = filteredPreds.length;
        const totalPages = Math.ceil(totalItems / predictionsPageSize) || 1;
        
        if (predictionsCurrentPage > totalPages) {
            predictionsCurrentPage = totalPages;
        }
        if (predictionsCurrentPage < 1) {
            predictionsCurrentPage = 1;
        }
        
        if (totalItems > predictionsPageSize) {
            predictionsPaginationDiv.style.display = "flex";
            predictionsPageInfo.textContent = `Página ${predictionsCurrentPage} de ${totalPages}`;
            predictionsPrevBtn.disabled = predictionsCurrentPage === 1;
            predictionsNextBtn.disabled = predictionsCurrentPage === totalPages;
        } else {
            predictionsPaginationDiv.style.display = "none";
        }
        
        const startIndex = (predictionsCurrentPage - 1) * predictionsPageSize;
        const endIndex = startIndex + predictionsPageSize;
        const paginatedPreds = filteredPreds.slice(startIndex, endIndex);

        if (paginatedPreds.length > 0) {
            paginatedPreds.forEach(p => {
                const tr = document.createElement("tr");
                tr.style.borderBottom = "1px solid rgba(255, 255, 255, 0.05)";

                const isGano = p.estado === "Ganado";
                const isPerdido = p.estado === "Perdido";
                
                let badgeClass = "badge-status";
                let stateStyle = "background: rgba(156,163,175,0.15); color: #9ca3af;";
                let dotColor = "purple";
                
                if (isGano) {
                    badgeClass = "badge-status";
                    stateStyle = "background: rgba(16, 185, 129, 0.15); color: var(--accent-green);";
                    dotColor = "green";
                } else if (isPerdido) {
                    badgeClass = "badge-status arriesgada";
                    stateStyle = "background: rgba(239, 68, 68, 0.15); color: var(--accent-red);";
                    dotColor = "red";
                } else {
                    badgeClass = "badge-status";
                    stateStyle = "background: rgba(14, 165, 233, 0.15); color: var(--accent-blue);";
                    dotColor = "blue";
                }
                
                const fechaFmt = p.fecha ? p.fecha.split("T")[0] : "-";
                const cuotaDec = parseFloat(p.cuota);
                
                tr.innerHTML = `
                    <td style="padding: 12px 10px; font-weight: 500; color: var(--text-secondary);">${fechaFmt}</td>
                    <td style="padding: 12px 10px; font-weight: 600;">${p.partido}</td>
                    <td style="padding: 12px 10px; color: var(--accent-blue); font-weight: 500;">${p.pronostico}</td>
                    <td style="padding: 12px 10px; font-weight: 500;">${formatOdds(cuotaDec)}</td>
                    <td style="padding: 12px 10px; text-align: center;">${p.probabilidad_estadistica}%</td>
                    <td style="padding: 12px 10px; text-align: center;">${p.probabilidad_implicita}%</td>
                    <td style="padding: 12px 10px; color: var(--accent-green); font-weight: 600;">${p.valor}</td>
                    <td style="padding: 12px 10px; color: var(--text-secondary);">${p.tipo_parley}</td>
                    <td style="padding: 12px 10px;"><span class="${badgeClass}" style="${stateStyle}"><span class="pulse-dot ${dotColor}"></span>${p.estado}</span></td>
                    <td style="padding: 12px 10px; font-weight: 700; color: var(--accent-purple);">${p.resultado_partido || "-"}</td>
                `;
                predictionsTbody.appendChild(tr);
            });
        } else {
            predictionsTbody.innerHTML = `
                <tr>
                    <td colspan="10" class="loading-text" style="text-align: center; padding: 20px;">No se encontraron predicciones con los filtros aplicados.</td>
                </tr>
            `;
        }
    };

    const setupPredFilters = () => {
        const searchInput = document.getElementById("search-prediccion");
        const filterStatus = document.getElementById("filter-prediccion-estado");
        const filterType = document.getElementById("filter-prediccion-tipo");
        
        if (searchInput) {
            searchInput.addEventListener("input", () => {
                predictionsCurrentPage = 1;
                renderPredictionsTable();
            });
        }
        if (filterStatus) {
            filterStatus.addEventListener("change", () => {
                predictionsCurrentPage = 1;
                renderPredictionsTable();
            });
        }
        if (filterType) {
            filterType.addEventListener("change", () => {
                predictionsCurrentPage = 1;
                renderPredictionsTable();
            });
        }
    };

    const setupParleyFilters = () => {
        const filterBtns = document.querySelectorAll(".filter-parley-btn");
        filterBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                filterBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                parleyFilter = btn.getAttribute("data-filter");
                parleysCurrentPage = 1;
                renderParleysHistory();
            });
        });
    };

    const renderParleysHistory = () => {
        if (!dataBanca) return;
        const activas = dataBanca.apuestas_activas || [];
        const archivadas = dataBanca.apuestas_archivadas || [];
        const predicciones = dataBanca.predicciones_ia || [];
        
        // 1. Agrupar las predicciones de IA por fecha y tipo_parley
        const groupedSuggested = {};
        predicciones.forEach(p => {
            const dateStr = p.fecha ? p.fecha.split("T")[0] : "Sin Fecha";
            const tipo = p.tipo_parley || "Combinada Segura";
            const key = `${dateStr}_${tipo}`;
            
            if (!groupedSuggested[key]) {
                groupedSuggested[key] = {
                    ticket_id: `SUG-${tipo.replace(/\s+/g, '')}-${dateStr}`,
                    fecha_jornada: dateStr,
                    tipo_parley: tipo,
                    cuota: 1.0,
                    estado: "Pendiente",
                    selecciones: [],
                    isSuggestedOnly: true,
                    inversion: 0.0,
                    retorno_potencial: 0.0
                };
            }
            
            groupedSuggested[key].selecciones.push({
                partido: p.partido,
                pronostico: p.pronostico,
                cuota: parseFloat(p.cuota),
                estado_seleccion: p.estado === "Ganado" ? "Ganado" : (p.estado === "Perdido" ? "Perdido" : (p.estado === "Anulado" ? "Anulado" : "Pendiente")),
                resultado_partido: p.resultado_partido
            });
        });

        // 2. Para cada sugerencia agrupada, calcular su cuota combinada y su estado consolidado
        Object.values(groupedSuggested).forEach(gp => {
            let cuotaTotal = 1.0;
            let algunPerdido = false;
            let algunPendiente = false;
            let todoAnulado = true;
            
            gp.selecciones.forEach(sel => {
                cuotaTotal *= sel.cuota;
                if (sel.estado_seleccion === "Perdido") {
                    algunPerdido = true;
                    todoAnulado = false;
                } else if (sel.estado_seleccion === "Pendiente") {
                    algunPendiente = true;
                    todoAnulado = false;
                } else if (sel.estado_seleccion === "Ganado") {
                    todoAnulado = false;
                }
            });
            
            gp.cuota = parseFloat(cuotaTotal.toFixed(2));
            
            if (algunPerdido) {
                gp.estado = "Perdida";
            } else if (algunPendiente) {
                gp.estado = "Pendiente";
            } else if (todoAnulado) {
                gp.estado = "Anulada";
            } else {
                gp.estado = "Ganada";
            }
        });

        // 3. Filtrar las sugerencias que el usuario YA jugó como ticket
        const playedTickets = [...activas, ...archivadas];
        const finalSuggestedParleys = Object.values(groupedSuggested).filter(gp => {
            const isPlayed = playedTickets.some(t => {
                const dateMatch = t.fecha_jornada === gp.fecha_jornada;
                const tType = t.tipo_parley.toLowerCase();
                const gpType = gp.tipo_parley.toLowerCase();
                const typeMatch = tType.includes(gpType) || gpType.includes(tType);
                return dateMatch && typeMatch;
            });
            return !isPlayed;
        });

        // 4. Unir todos los parleys (jugados y sugeridos no jugados)
        let todos = [
            ...activas.map(t => ({ ...t, isSuggestedOnly: false })),
            ...archivadas.map(t => ({ ...t, isSuggestedOnly: false })),
            ...finalSuggestedParleys
        ];
        
        // 5. Ordenar por ID descendente
        todos.sort((a, b) => b.ticket_id.localeCompare(a.ticket_id));
        
        if (parleyFilter !== "all") {
            todos = todos.filter(t => t.estado === parleyFilter);
        }
        
        const totalItems = todos.length;
        const totalPages = Math.ceil(totalItems / parleysPageSize) || 1;
        
        if (parleysCurrentPage > totalPages) {
            parleysCurrentPage = totalPages;
        }
        if (parleysCurrentPage < 1) {
            parleysCurrentPage = 1;
        }
        
        if (totalItems > parleysPageSize) {
            parleysPaginationDiv.style.display = "flex";
            parleysPageInfo.textContent = `Página ${parleysCurrentPage} de ${totalPages}`;
            parleysPrevBtn.disabled = parleysCurrentPage === 1;
            parleysNextBtn.disabled = parleysCurrentPage === totalPages;
        } else {
            parleysPaginationDiv.style.display = "none";
        }
        
        const startIndex = (parleysCurrentPage - 1) * parleysPageSize;
        const endIndex = startIndex + parleysPageSize;
        const paginatedTodos = todos.slice(startIndex, endIndex);
        
        containerParleysHistory.innerHTML = "";
        
        if (paginatedTodos.length === 0) {
            containerParleysHistory.innerHTML = `<p class="loading-text">💡 No se encontraron parleys con el estado seleccionado.</p>`;
            return;
        }
        
        paginatedTodos.forEach(tkt => {
            const isGanada = tkt.estado === "Ganada";
            const isPerdida = tkt.estado === "Perdida";
            const isAnulada = tkt.estado === "Anulada";
            
            let statusBadgeHtml = "";
            let leftBorderColor = "var(--text-muted)";
            let profitText = "";
            let profitClass = "";
            let dotColor = "purple";
            
            if (isGanada) {
                statusBadgeHtml = `<span class="badge-status"><span class="pulse-dot green"></span>Ganada</span>`;
                leftBorderColor = "var(--accent-green)";
                dotColor = "green";
                if (tkt.isSuggestedOnly) {
                    profitText = `Retroalimentación: <b style="color: var(--accent-green);">Sugerencia Acertada</b>`;
                } else {
                    const netWin = tkt.retorno_realizado - tkt.inversion;
                    profitText = `Resultado: <b>+${netWin.toFixed(2)} USD (Ganancia)</b>`;
                }
                profitClass = "color: var(--accent-green);";
            } else if (isPerdida) {
                statusBadgeHtml = `<span class="badge-status arriesgada"><span class="pulse-dot red"></span>Perdida</span>`;
                leftBorderColor = "var(--accent-red)";
                dotColor = "red";
                if (tkt.isSuggestedOnly) {
                    profitText = `Retroalimentación: <b style="color: var(--accent-red);">Sugerencia Fallada</b>`;
                } else {
                    profitText = `Resultado: <b>-${tkt.inversion.toFixed(2)} USD (Pérdida)</b>`;
                }
                profitClass = "color: var(--accent-red);";
            } else if (isAnulada) {
                statusBadgeHtml = `<span class="badge-status" style="background: rgba(156,163,175,0.2); color: #9ca3af;"><span class="pulse-dot purple"></span>Anulada</span>`;
                leftBorderColor = "var(--text-muted)";
                dotColor = "purple";
                if (tkt.isSuggestedOnly) {
                    profitText = `Retroalimentación: <b style="color: #9ca3af;">Sugerencia Anulada</b>`;
                } else {
                    profitText = `Resultado: <b>$0.00 USD (Reembolsado)</b>`;
                }
                profitClass = "color: var(--text-secondary);";
            } else {
                statusBadgeHtml = `<span class="badge-status" style="background: rgba(14,165,233,0.2); color: var(--accent-blue);"><span class="pulse-dot blue"></span>Pendiente</span>`;
                leftBorderColor = "var(--accent-blue)";
                dotColor = "blue";
                if (tkt.isSuggestedOnly) {
                    profitText = `Retroalimentación: <b style="color: var(--accent-blue);">Pendiente</b>`;
                } else {
                    profitText = `Retorno Potencial: <b>$${tkt.retorno_potencial.toFixed(2)} USD</b>`;
                }
                profitClass = "color: var(--accent-blue);";
            }
            
            let cardTitle = "";
            let extraBadgeHtml = "";
            let borderStyle = "solid";
            
            if (tkt.isSuggestedOnly) {
                cardTitle = `🤖 Sugerido (${tkt.tipo_parley})`;
                extraBadgeHtml = `<span class="badge-status" style="background: rgba(139,92,246,0.15); color: var(--accent-purple); margin-right: 8px;">No Jugado</span>`;
                borderStyle = "dashed";
            } else {
                cardTitle = `🎫 Ticket ${tkt.ticket_id}`;
                extraBadgeHtml = `<span class="badge-status" style="background: rgba(16,185,129,0.15); color: var(--accent-green); margin-right: 8px;">Jugado</span>`;
                borderStyle = "solid";
            }
            
            let html = `
                <div class="ticket-card" style="border-left: 3px ${borderStyle} ${leftBorderColor}; margin-bottom: 15px; background: ${tkt.isSuggestedOnly ? 'rgba(139, 92, 246, 0.015)' : 'rgba(255, 255, 255, 0.02)'};">
                    <div class="ticket-header">
                        <div style="display: flex; flex-direction: column; gap: 4px;">
                            <h3 style="font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 700; color: ${tkt.isSuggestedOnly ? '#c084fc' : 'var(--text-primary)'};">${cardTitle}</h3>
                            <span style="font-size: 0.75rem; color: var(--text-secondary);">${tkt.tipo_parley} | Jornada: ${tkt.fecha_jornada}</span>
                        </div>
                        <div style="display: flex; align-items: center;">
                            ${extraBadgeHtml}
                            ${statusBadgeHtml}
                        </div>
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
                            <span class="sel-pick" style="font-size: 0.8rem; color: var(--text-secondary);">${sel.pronostico} (<b>${formatOdds(cuotaDec)}</b>)</span>
                        </div>
                        <div style="align-self: center; font-size: 0.85rem;">
                            ${selBadge}
                        </div>
                    </div>
                `;
            });
            
            const inversionStr = tkt.isSuggestedOnly ? `<span style="color: var(--text-muted); font-style: italic;">No Jugado</span>` : `<b>$${tkt.inversion.toFixed(2)} USD</b>`;
            
            html += `
                    </div>
                    <div class="ticket-footer" style="background: rgba(255,255,255,0.01); border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 12px; margin-top: 12px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                        <span class="ticket-meta">Inversión: ${inversionStr} | Cuota Combinada: <b>${formatOdds(tkt.cuota)}</b></span>
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
                showToast(resJson.message, "success");
                await cargarYRenderizar();
            } else {
                const err = await res.text();
                showToast("Error al liquidar ticket: " + err, "error");
            }
        } catch (err) {
            console.error(err);
            showToast("Error al comunicarse con el servidor.", "error");
        }
    };

    // --- RENDERIZAR GRÁFICO DE CRECIMIENTO ---
    const renderChart = () => {
        const canvas = document.getElementById('growthChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        if (window.growthChartInstance) {
            window.growthChartInstance.destroy();
        }

        // Construir línea de tiempo de la banca
        const labels = ["Inicio"];
        const chartData = [10.0];
        
        if (dataBanca && dataBanca.apuestas_archivadas) {
            let bancaAcumulada = 10.0;
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

        // Unir etiquetas de simulación si existen
        let finalLabels = [...labels];
        if (window.projectedLabels && window.projectedLabels.length > 0) {
            finalLabels = finalLabels.concat(window.projectedLabels);
        }

        const targetLine = Array(finalLabels.length).fill(100.0);

        const datasets = [
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
        ];

        // Rellenar curva de proyección si fue calculada
        if (window.projectedSeries && window.projectedSeries.length > 0) {
            datasets.push({
                label: 'Proyección Simulada ($)',
                data: window.projectedSeries,
                borderColor: '#8b5cf6',
                borderDash: [4, 4],
                backgroundColor: 'rgba(139, 92, 246, 0.04)',
                borderWidth: 2,
                fill: false,
                tension: 0.3,
                pointRadius: 2.5,
                pointBackgroundColor: '#8b5cf6'
            });
        }

        window.growthChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: finalLabels,
                datasets: datasets
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

    // --- SIMULADOR DE PROYECCIONES ---
    const setupSimulator = () => {
        const btnSimular = document.getElementById("btn-simular");
        const inputYield = document.getElementById("sim-yield");
        const inputTickets = document.getElementById("sim-tickets");
        
        if (!btnSimular) return;
        
        btnSimular.addEventListener("click", () => {
            const yieldVal = parseFloat(inputYield.value);
            const numTickets = parseInt(inputTickets.value);
            
            if (isNaN(yieldVal) || isNaN(numTickets) || numTickets <= 0) {
                showToast("Por favor introduce valores de simulación válidos.", "error");
                return;
            }
            
            // Simular a partir de la banca acumulada actual en el historial real
            let bancaAcumulada = 10.0;
            const labelsCount = window.growthChartInstance ? window.growthChartInstance.data.labels.length : 1;
            
            if (dataBanca && dataBanca.apuestas_archivadas) {
                const archivadasOrdenadas = [...dataBanca.apuestas_archivadas].sort((a,b) => a.ticket_id.localeCompare(b.ticket_id));
                let tempBanca = 10.0;
                archivadasOrdenadas.forEach((tkt) => {
                    if (tkt.estado === "Ganada") {
                        tempBanca += (tkt.retorno_realizado - tkt.inversion);
                    } else if (tkt.estado === "Perdida") {
                        tempBanca -= tkt.inversion;
                    }
                });
                bancaAcumulada = tempBanca;
            }
            
            // Stake promedio de $1.00 USD por parley
            const avgStake = 1.00;
            const yieldFactor = yieldVal / 100.0;
            
            const projectionPoints = Array(labelsCount).fill(null);
            // El último punto real es el origen de la línea de proyección
            projectionPoints[labelsCount - 1] = parseFloat(bancaAcumulada.toFixed(2));
            
            let simBanca = bancaAcumulada;
            const newLabels = [];
            
            for (let i = 1; i <= numTickets; i++) {
                simBanca += (avgStake * yieldFactor);
                projectionPoints.push(parseFloat(simBanca.toFixed(2)));
                newLabels.push(`SIM ${i}`);
            }
            
            window.projectedLabels = newLabels;
            window.projectedSeries = projectionPoints;
            
            renderChart();
            showToast(`Simulación completada. Proyección final: $${simBanca.toFixed(2)} USD`, "success");
        });
    };

    // --- CARGAR Y RENDERIZAR LOGS DE AUDITORÍA ---
    const cargarYRenderizarLogsIA = async () => {
        const container = document.getElementById("admin-logs-container");
        if (!container) return;
        
        try {
            const res = await fetch("/api/debug/full_logs");
            if (!res.ok) throw new Error("Status " + res.status);
            
            const logData = await res.json();
            const logs = logData.logs || [];
            
            container.innerHTML = "";
            
            if (logs.length === 0) {
                container.innerHTML = `<p class="loading-text">No hay logs de auditoría en la base de datos.</p>`;
                return;
            }
            
            logs.forEach(log => {
                const item = document.createElement("div");
                item.className = "log-accordion-item";
                
                const fechaFmt = new Date(log.fecha).toLocaleString("es-ES");
                const stateText = log.exito ? "ÉXITO" : "FALLO";
                const stateClass = log.exito ? "success" : "fail";
                
                let formattedJson = "Sin resultado";
                if (log.json_resultado) {
                    try {
                        const parsed = JSON.parse(log.json_resultado);
                        formattedJson = JSON.stringify(parsed, null, 2);
                    } catch (e) {
                        formattedJson = log.json_resultado;
                    }
                }
                
                item.innerHTML = `
                    <div class="log-accordion-header">
                        <div class="log-header-info">
                            <span class="log-status-badge ${stateClass}">${stateText}</span>
                            <span class="log-date">${fechaFmt}</span>
                        </div>
                        <span class="log-arrow">▼</span>
                    </div>
                    <div class="log-accordion-body">
                        <div class="log-block">
                            <h4>Detalles</h4>
                            <p style="font-size: 0.9rem; line-height: 1.45; color: var(--text-secondary);">${log.detalles || "N/A"}</p>
                        </div>
                        <div class="log-block">
                            <h4>Prompt Utilizado</h4>
                            <pre>${log.prompt_usado || "N/A"}</pre>
                        </div>
                        <div class="log-block">
                            <h4>JSON Resultado</h4>
                            <pre>${formattedJson}</pre>
                        </div>
                    </div>
                `;
                
                const header = item.querySelector(".log-accordion-header");
                const body = item.querySelector(".log-accordion-body");
                
                header.addEventListener("click", () => {
                    const isOpen = body.classList.contains("open");
                    container.querySelectorAll(".log-accordion-body").forEach(el => el.classList.remove("open"));
                    container.querySelectorAll(".log-accordion-header").forEach(el => el.classList.remove("active"));
                    
                    if (!isOpen) {
                        body.classList.add("open");
                        header.classList.add("active");
                    }
                });
                
                container.appendChild(item);
            });
        } catch (e) {
            console.error("Error al cargar logs:", e);
            container.innerHTML = `<p class="loading-text" style="color: var(--accent-red);">❌ Error al cargar logs de auditoría: ${e.message}</p>`;
        }
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
                    showToast("Por favor ingresa un monto válido mayor a cero.", "error");
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
                        showToast(resJson.message, "success");
                        formAjusteBanca.reset();
                        await cargarYRenderizar();
                    } else {
                        const err = await res.text();
                        showToast(`Error al ajustar banca: ${err}`, "error");
                    }
                } catch (err) {
                    console.error(err);
                    showToast("Error de comunicación con la API.", "error");
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
                        showToast(msg.replace(/\n/g, ' '), "success");
                        await cargarYRenderizar();
                    } else {
                        const err = await res.text();
                        showToast(`Error al actualizar marcadores: ${err}`, "error");
                    }
                } catch (err) {
                    console.error(err);
                    showToast("Error de comunicación con la API de actualización.", "error");
                } finally {
                    btnActualizarResultados.textContent = originalText;
                    btnActualizarResultados.disabled = false;
                }
            });
        }

        const btnRefrescarLogs = document.getElementById("btn-refrescar-logs");
        if (btnRefrescarLogs) {
            btnRefrescarLogs.addEventListener("click", async () => {
                btnRefrescarLogs.textContent = "⏳ Cargando...";
                btnRefrescarLogs.disabled = true;
                await cargarYRenderizarLogsIA();
                btnRefrescarLogs.textContent = "🔄 Recargar Logs";
                btnRefrescarLogs.disabled = false;
                showToast("Logs de auditoría actualizados.", "success");
            });
        }
    };

    // --- CONFIGURACIÓN DE CONTROLES DE PAGINACIÓN ---
    const setupPagination = () => {
        if (parleysPrevBtn) {
            parleysPrevBtn.addEventListener("click", () => {
                if (parleysCurrentPage > 1) {
                    parleysCurrentPage--;
                    renderParleysHistory();
                }
            });
        }
        if (parleysNextBtn) {
            parleysNextBtn.addEventListener("click", () => {
                parleysCurrentPage++;
                renderParleysHistory();
            });
        }
        
        if (predictionsPrevBtn) {
            predictionsPrevBtn.addEventListener("click", () => {
                if (predictionsCurrentPage > 1) {
                    predictionsCurrentPage--;
                    renderPredictionsTable();
                }
            });
        }
        if (predictionsNextBtn) {
            predictionsNextBtn.addEventListener("click", () => {
                predictionsCurrentPage++;
                renderPredictionsTable();
            });
        }
    };

    // --- LÓGICA DE QUINIELA IA ---
    let listadoPartidosQuiniela = [];

    const cargarPartidosQuiniela = async () => {
        if (!containerQuinielaMatches) return;
        containerQuinielaMatches.innerHTML = `<p class="loading-text">⏳ Cargando partidos de la Copa del Mundo...</p>`;
        
        try {
            const res = await fetch("/api/quiniela/partidos");
            if (!res.ok) throw new Error("HTTP Status " + res.status);
            const data = await res.json();
            
            const manualesPrevios = listadoPartidosQuiniela.filter(p => p.fuente === "Manual");
            
            listadoPartidosQuiniela = data.partidos.map(p => ({
                home: p.home,
                away: p.away,
                fuente: p.fuente,
                checked: true
            }));
            
            listadoPartidosQuiniela = listadoPartidosQuiniela.concat(manualesPrevios);
            renderizarPartidosQuiniela();
        } catch (e) {
            console.error(e);
            containerQuinielaMatches.innerHTML = `<p class="loading-text" style="color: var(--accent-red);">❌ Error al cargar partidos de la API. Puedes agregarlos manualmente abajo.</p>`;
        }
    };

    const renderizarPartidosQuiniela = () => {
        containerQuinielaMatches.innerHTML = "";
        
        if (listadoPartidosQuiniela.length === 0) {
            containerQuinielaMatches.innerHTML = `<p class="loading-text">💡 No hay partidos configurados. Añade partidos manuales abajo.</p>`;
            return;
        }
        
        listadoPartidosQuiniela.forEach((p, idx) => {
            const div = document.createElement("div");
            div.className = "quiniela-match-select-item";
            
            const isManual = p.fuente === "Manual";
            const deleteBtnHtml = isManual ? `<button class="quiniela-manual-delete-btn" data-index="${idx}" title="Eliminar partido">🗑️</button>` : "";
            
            div.innerHTML = `
                <div style="display: flex; align-items: center; flex: 1;">
                    <input type="checkbox" class="quiniela-match-checkbox" data-index="${idx}" ${p.checked ? 'checked' : ''}>
                    <span class="quiniela-match-info">${p.home} vs ${p.away}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="quiniela-match-source">${p.fuente}</span>
                    ${deleteBtnHtml}
                </div>
            `;
            
            div.querySelector(".quiniela-match-checkbox").addEventListener("change", (e) => {
                listadoPartidosQuiniela[idx].checked = e.target.checked;
            });
            
            if (isManual) {
                div.querySelector(".quiniela-manual-delete-btn").addEventListener("click", () => {
                    listadoPartidosQuiniela.splice(idx, 1);
                    renderizarPartidosQuiniela();
                });
            }
            
            containerQuinielaMatches.appendChild(div);
        });
    };

    const setupQuiniela = () => {
        if (btnRecargarPartidosQuiniela) {
            btnRecargarPartidosQuiniela.addEventListener("click", cargarPartidosQuiniela);
        }
        
        if (btnSelectAllQuiniela) {
            btnSelectAllQuiniela.addEventListener("click", () => {
                listadoPartidosQuiniela.forEach(p => p.checked = true);
                renderizarPartidosQuiniela();
            });
        }
        
        if (btnDeselectAllQuiniela) {
            btnDeselectAllQuiniela.addEventListener("click", () => {
                listadoPartidosQuiniela.forEach(p => p.checked = false);
                renderizarPartidosQuiniela();
            });
        }
        
        if (btnAddManualMatch) {
            btnAddManualMatch.addEventListener("click", () => {
                const local = inputManualLocal.value.trim();
                const visitante = inputManualVisitante.value.trim();
                
                if (!local || !visitante) {
                    showToast("Por favor escribe el nombre de ambos equipos.", "error");
                    return;
                }
                
                const existe = listadoPartidosQuiniela.some(p => 
                    p.home.toLowerCase() === local.toLowerCase() && p.away.toLowerCase() === visitante.toLowerCase()
                );
                
                if (existe) {
                    showToast("Este partido ya está en la lista.", "error");
                    return;
                }
                
                listadoPartidosQuiniela.push({
                    home: local,
                    away: visitante,
                    fuente: "Manual",
                    checked: true
                });
                
                inputManualLocal.value = "";
                inputManualVisitante.value = "";
                
                renderizarPartidosQuiniela();
                showToast(`Partido manual añadido: ${local} vs ${visitante}`, "success");
            });
        }
        
        if (btnCalcularQuiniela) {
            btnCalcularQuiniela.addEventListener("click", async () => {
                const seleccionados = listadoPartidosQuiniela.filter(p => p.checked);
                if (seleccionados.length === 0) {
                    showToast("Debes seleccionar al menos un partido para analizar la quiniela.", "error");
                    return;
                }
                
                const originalText = btnCalcularQuiniela.textContent;
                btnCalcularQuiniela.textContent = "⏳ Analizando Quiniela con IA...";
                btnCalcularQuiniela.disabled = true;
                
                containerQuinielaCombinations.innerHTML = `<p class="loading-text">🧠 Analizando probabilidades y ejecutando optimización Dijkstra-heap...</p>`;
                quinielaIndividualTbody.innerHTML = `<tr><td colspan="6" class="loading-text">Cargando desglose...</td></tr>`;
                
                try {
                    const res = await fetch("/api/quiniela/calcular", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ partidos: seleccionados })
                    });
                    
                    if (!res.ok) throw new Error("HTTP Status " + res.status);
                    const resJson = await res.json();
                    
                    if (resJson.ok) {
                        renderizarResultadosQuiniela(resJson.data);
                        showToast("Quiniela analizada con éxito.", "success");
                    } else {
                        showToast("Error al analizar: " + resJson.error, "error");
                    }
                } catch (e) {
                    console.error(e);
                    showToast("Error al comunicarse con la API de cálculo.", "error");
                    containerQuinielaCombinations.innerHTML = `<p class="loading-text" style="color: var(--accent-red);">❌ Error al calcular quiniela.</p>`;
                } finally {
                    btnCalcularQuiniela.textContent = originalText;
                    btnCalcularQuiniela.disabled = false;
                }
            });
        }
    };

    const renderizarResultadosQuiniela = (data) => {
        containerQuinielaCombinations.innerHTML = "";
        const combinaciones = data.top_combinaciones || [];
        
        if (combinaciones.length === 0) {
            containerQuinielaCombinations.innerHTML = `<p class="loading-text">No se pudieron generar combinaciones.</p>`;
            return;
        }
        
        combinaciones.forEach(comb => {
            const card = document.createElement("div");
            card.className = "quiniela-combination-card";
            
            let badgeStyle = "background: rgba(16, 185, 129, 0.15); color: var(--accent-green);";
            if (comb.id_comb === 2) badgeStyle = "background: rgba(14, 165, 233, 0.15); color: var(--accent-blue);";
            if (comb.id_comb === 3) badgeStyle = "background: rgba(139, 92, 246, 0.15); color: var(--accent-purple);";
            
            let html = `
                <div class="quiniela-combination-header">
                    <h3>Ticket #${comb.id_comb}</h3>
                    <span class="badge-status" style="${badgeStyle}">Prob: ${comb.probabilidad_conjunta}%</span>
                </div>
                <div class="quiniela-combination-selections">
            `;
            
            comb.selections.forEach(sel => {
                let outcomeBadgeColor = "var(--text-muted)";
                if (sel.outcome === "1") outcomeBadgeColor = "var(--accent-blue)";
                if (sel.outcome === "2") outcomeBadgeColor = "var(--accent-purple)";
                
                html += `
                    <div class="quiniela-sel-row">
                        <span class="quiniela-sel-match" style="text-align: left;">${sel.home} vs ${sel.away}</span>
                        <span class="quiniela-sel-outcome" style="color: ${outcomeBadgeColor};">${sel.pronostico_desc} (${sel.probabilidad_individual}%)</span>
                    </div>
                `;
            });
            
            html += `</div>`;
            card.innerHTML = html;
            containerQuinielaCombinations.appendChild(card);
        });
        
        quinielaIndividualTbody.innerHTML = "";
        const individuales = data.probabilidades_individuales || [];
        
        individuales.forEach(match => {
            const tr = document.createElement("tr");
            tr.style.borderBottom = "1px solid rgba(255, 255, 255, 0.05)";
            
            tr.innerHTML = `
                <td style="padding: 12px 10px; font-weight: 600; text-align: left;">${match.home} vs ${match.away}</td>
                <td style="padding: 12px 10px; text-align: center;">
                    <div style="font-weight: 700; color: var(--accent-blue);">${match.prob_home}%</div>
                    <div class="quiniela-probability-bar-container"><div class="quiniela-probability-bar home" style="width: ${match.prob_home}%"></div></div>
                </td>
                <td style="padding: 12px 10px; text-align: center;">
                    <div style="font-weight: 700; color: var(--text-secondary);">${match.prob_draw}%</div>
                    <div class="quiniela-probability-bar-container"><div class="quiniela-probability-bar draw" style="width: ${match.prob_draw}%"></div></div>
                </td>
                <td style="padding: 12px 10px; text-align: center;">
                    <div style="font-weight: 700; color: var(--accent-purple);">${match.prob_away}%</div>
                    <div class="quiniela-probability-bar-container"><div class="quiniela-probability-bar away" style="width: ${match.prob_away}%"></div></div>
                </td>
                <td style="padding: 12px 10px; color: var(--text-secondary); font-size: 0.85rem; max-width: 320px; text-align: left; line-height: 1.35;">${match.analisis_contextual || '-'}</td>
                <td style="padding: 12px 10px; color: var(--text-muted); font-size: 0.8rem; text-align: left;">${match.fuente}</td>
            `;
            
            quinielaIndividualTbody.appendChild(tr);
        });
    };

    // --- INICIALIZACIÓN ---
    setupTabs();
    setupOddsToggle();
    setupParleyFilters();
    setupPredFilters();
    setupForm();
    setupSimulator();
    setupQuiniela();
    setupInteractiveElements();
    setupPagination();
    await cargarYRenderizar();
});
