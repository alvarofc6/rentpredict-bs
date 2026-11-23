const TOKEN_KEY = "rentpredict_token";

const NOMBRES_CORTOS = {
  superficie_m2: "Superficie (m²)",
  habitaciones: "Habitaciones",
  antiguedad_anios: "Antigüedad (años)",
  distancia_centro_km: "Distancia (km)",
  precio_alquiler_bs: "Alquiler (Bs)",
};

const formatoBs = (valor) =>
  Number(valor).toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// ==================== GESTIÓN DE SESIÓN Y FETCH ====================

function obtenerToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function guardarToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function limpiarToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function mostrarVistaAuth(mensajeOpcional = null) {
  document.getElementById("vista-dashboard").classList.add("hidden");
  document.getElementById("vista-auth").classList.remove("hidden");
  if (mensajeOpcional) {
    mostrarAlertaAuth(mensajeOpcional, "info");
  }
}

function mostrarVistaDashboard(usuario) {
  document.getElementById("vista-auth").classList.add("hidden");
  document.getElementById("vista-dashboard").classList.remove("hidden");
  document.getElementById("usuario-activo-nombre").textContent = `${usuario.nombre} (@${usuario.usuario})`;
  lucide.createIcons();
  renderizarKaTeX(document.getElementById("vista-dashboard"));
}

function mostrarAlertaAuth(mensaje, tipo = "error") {
  const box = document.getElementById("auth-alerta");
  const estilos = {
    error: "bg-rose-50 border-rose-200 text-rose-700",
    exito: "bg-emerald-50 border-emerald-200 text-emerald-700",
    info: "bg-indigo-50 border-indigo-200 text-indigo-700",
  };
  box.className = `mx-7 mt-5 px-3.5 py-2.5 rounded-xl text-xs font-medium border ${estilos[tipo] || estilos.error}`;
  box.textContent = mensaje;
  box.classList.remove("hidden");
}

function ocultarAlertaAuth() {
  document.getElementById("auth-alerta").classList.add("hidden");
}

async function fetchConAuth(url, opciones = {}) {
  const token = obtenerToken();
  const headers = {
    ...(opciones.headers || {}),
    Authorization: `Bearer ${token}`,
  };

  const resp = await fetch(url, { ...opciones, headers });
  if (resp.status === 401) {
    limpiarToken();
    mostrarVistaAuth("Tu sesión expiró. Vuelve a iniciar sesión.");
    throw new Error("Sesión no autorizada");
  }
  return resp;
}

// ==================== UTILIDADES DEL DASHBOARD ====================

function mostrarAlerta(mensaje, tipo = "info") {
  const contenedor = document.getElementById("alerta-global");
  const caja = document.getElementById("alerta-caja");
  const texto = document.getElementById("alerta-texto");

  const estilos = {
    error: "bg-rose-50 border-rose-200 text-rose-800",
    exito: "bg-emerald-50 border-emerald-200 text-emerald-800",
    info: "bg-indigo-50 border-indigo-200 text-indigo-800",
  };

  caja.className = `rounded-xl px-4 py-3 text-sm font-medium flex items-center justify-between border ${estilos[tipo] || estilos.info}`;
  texto.textContent = mensaje;
  contenedor.classList.remove("hidden");
}

function ocultarAlerta() {
  document.getElementById("alerta-global").classList.add("hidden");
}

function renderizarKaTeX(elemento) {
  if (typeof renderMathInElement === "function") {
    renderMathInElement(elemento, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }
}

function construirTablaMatriz(matriz, resaltarPrimeraColumna = false) {
  const filas = matriz
    .map((fila) => {
      const celdas = fila
        .map((val, colIdx) => {
          const claseResalte =
            resaltarPrimeraColumna && colIdx === 0
              ? "bg-indigo-50 text-indigo-700 font-bold"
              : "text-slate-700";
          return `<td class="px-2.5 py-1.5 border border-slate-200 font-mono text-xs text-right ${claseResalte}">${val}</td>`;
        })
        .join("");
      return `<tr>${celdas}</tr>`;
    })
    .join("");

  return `<table class="w-full border-collapse rounded-lg overflow-hidden"><tbody>${filas}</tbody></table>`;
}

// ==================== RENDERIZADO DEL DASHBOARD ====================

function renderizarDashboard(data) {
  document.getElementById("nombre-archivo").textContent = data.archivo_activo;
  document.getElementById("contador-registros").textContent = `${data.kpis.total_registros} reg.`;

  // 1. Exploración de Datos
  document.getElementById("kpi-total").textContent = data.kpis.total_registros;
  document.getElementById("kpi-promedio").textContent = `${formatoBs(data.kpis.alquiler_promedio)} Bs`;
  document.getElementById("kpi-superficie").textContent = `${data.kpis.superficie_promedio} m²`;
  document.getElementById("kpi-rango").textContent = `${formatoBs(data.kpis.precio_minimo)} - ${formatoBs(data.kpis.precio_maximo)} Bs`;

  document.getElementById("tabla-datos-body").innerHTML = data.datos_muestra
    .map(
      (fila, idx) => `
      <tr class="hover:bg-slate-50 transition">
        <td class="px-4 py-2 text-slate-400 font-mono text-xs">${idx + 1}</td>
        <td class="px-4 py-2">${fila.superficie_m2}</td>
        <td class="px-4 py-2">${fila.habitaciones}</td>
        <td class="px-4 py-2">${fila.antiguedad_anios}</td>
        <td class="px-4 py-2">${fila.distancia_centro_km}</td>
        <td class="px-4 py-2 font-semibold text-emerald-700">${formatoBs(fila.precio_alquiler_bs)} Bs</td>
      </tr>`
    )
    .join("");

  document.getElementById("tabla-estadisticas-body").innerHTML = Object.entries(data.estadisticas)
    .map(
      ([col, est]) => `
      <tr class="hover:bg-slate-50">
        <td class="px-4 py-2.5 font-semibold text-slate-800">${NOMBRES_CORTOS[col] || col}</td>
        <td class="px-3 py-2.5 font-mono">${est.media}</td>
        <td class="px-3 py-2.5 font-mono">${est.desv_std}</td>
        <td class="px-3 py-2.5 font-mono">${est.min}</td>
        <td class="px-3 py-2.5 font-mono">${est.mediana}</td>
        <td class="px-3 py-2.5 font-mono">${est.max}</td>
      </tr>`
    )
    .join("");

  const { columnas, matriz } = data.correlaciones;
  const headerCorr = `<tr><th class="p-2"></th>${columnas
    .map((c) => `<th class="p-2 font-semibold text-slate-600">${NOMBRES_CORTOS[c].split(" ")[0]}</th>`)
    .join("")}</tr>`;

  const bodyCorr = matriz
    .map((fila, i) => {
      const celdas = fila
        .map((v) => {
          const intensidad = Math.min(0.85, Math.abs(v) * 0.75);
          const bg =
            v >= 0
              ? `rgba(16, 185, 129, ${intensidad.toFixed(2)})`
              : `rgba(244, 63, 94, ${intensidad.toFixed(2)})`;
          const colorTexto = Math.abs(v) > 0.55 ? "#ffffff" : "#0f172a";
          return `<td class="p-2 font-mono font-semibold border border-white rounded" style="background:${bg};color:${colorTexto}">${v.toFixed(2)}</td>`;
        })
        .join("");
      return `<tr><th class="p-2 text-left font-semibold text-slate-700">${NOMBRES_CORTOS[columnas[i]].split(" ")[0]}</th>${celdas}</tr>`;
    })
    .join("");
  document.getElementById("tabla-correlacion").innerHTML = `<thead>${headerCorr}</thead><tbody>${bodyCorr}</tbody>`;

  // 2. Álgebra Lineal
  const alg = data.algebra_lineal;
  document.getElementById("dim-X").textContent = alg.dimensiones.X;
  document.getElementById("dim-XT").textContent = alg.dimensiones.X_T;
  document.getElementById("dim-Y").textContent = `Y: ${alg.dimensiones.Y}`;
  document.getElementById("dim-beta").textContent = `β: ${alg.dimensiones.beta}`;
  document.getElementById("dim-inv").textContent = alg.dimensiones.X_T_X_inv;

  document.getElementById("preview-X").innerHTML = construirTablaMatriz(alg.vistas_previas.X, true);
  document.getElementById("preview-XT").innerHTML = construirTablaMatriz(alg.vistas_previas.X_T, false);
  document.getElementById("preview-Y").innerHTML = construirTablaMatriz(alg.vistas_previas.Y, false);
  document.getElementById("preview-beta").innerHTML = construirTablaMatriz(alg.vistas_previas.beta, false);
  document.getElementById("preview-inv").innerHTML = construirTablaMatriz(alg.vistas_previas.X_T_X_inv, false);

  const ecuacionEl = document.getElementById("ecuacion-final-katex");
  ecuacionEl.textContent = `$$${alg.ecuacion_latex}$$`;
  renderizarKaTeX(document.getElementById("tab-algebra"));

  document.getElementById("lista-interpretaciones").innerHTML = alg.coeficientes
    .map((c) => {
      const badgeColor = c.valor >= 0
        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
        : "bg-rose-50 text-rose-700 border-rose-200";
      return `
        <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
          <div class="flex items-center justify-between gap-2 mb-1.5">
            <span class="font-bold text-slate-800 text-sm">${c.simbolo} · ${c.etiqueta}</span>
            <span class="font-mono text-xs font-bold px-2.5 py-0.5 rounded-lg border ${badgeColor}">
              ${c.valor >= 0 ? "+" : ""}${c.valor}
            </span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">${c.interpretacion}</p>
        </div>`;
    })
    .join("");

  // 3. Evaluación y Gráficas
  const met = data.metricas;
  document.getElementById("metrica-mae").textContent = `${formatoBs(met.mae)} Bs`;
  document.getElementById("metrica-rmse").textContent = `${formatoBs(met.rmse)} Bs`;
  document.getElementById("metrica-r2").textContent = `${met.r2_porcentaje}% (${met.r2})`;
  document.getElementById("barra-r2").style.width = `${met.r2_porcentaje}%`;
  document.getElementById("badge-calidad").textContent = met.calidad_etiqueta;
  document.getElementById("texto-calidad").textContent = met.calidad_descripcion;
  document.getElementById("validacion-sklearn").textContent =
    `MAE: ${met.validacion_sklearn.mae} Bs | RMSE: ${met.validacion_sklearn.rmse} Bs | R²: ${met.validacion_sklearn.r2}`;

  document.getElementById("img-real-vs-predicho").src = data.graficas.real_vs_predicho;
  document.getElementById("img-residuos").src = data.graficas.residuos;
}

// ==================== LLAMADAS A LA API ====================

async function verificarSesionInicial() {
  const token = obtenerToken();
  if (!token) {
    mostrarVistaAuth();
    return;
  }

  try {
    const resp = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) {
      limpiarToken();
      mostrarVistaAuth();
      return;
    }
    const usuario = await resp.json();
    mostrarVistaDashboard(usuario);
    await cargarAnalisisInicial();
  } catch (err) {
    mostrarVistaAuth("No se pudo conectar con el servidor.");
  }
}

async function manejarLogin(e) {
  e.preventDefault();
  ocultarAlertaAuth();

  const usuario = document.getElementById("login-usuario").value.trim();
  const contrasena = document.getElementById("login-contrasena").value;

  try {
    const resp = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, contrasena }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      mostrarAlertaAuth(data.detail || "Credenciales inválidas.", "error");
      return;
    }

    guardarToken(data.token);
    document.getElementById("form-login").reset();
    mostrarVistaDashboard(data);
    await cargarAnalisisInicial();
  } catch (err) {
    mostrarAlertaAuth("Error de conexión con el servidor.", "error");
  }
}

async function manejarRegistro(e) {
  e.preventDefault();
  ocultarAlertaAuth();

  const nombre = document.getElementById("reg-nombre").value.trim();
  const usuario = document.getElementById("reg-usuario").value.trim();
  const contrasena = document.getElementById("reg-contrasena").value;
  const confirmar = document.getElementById("reg-confirmar").value;

  if (contrasena !== confirmar) {
    mostrarAlertaAuth("Las contraseñas no coinciden.", "error");
    return;
  }

  try {
    const resp = await fetch("/api/auth/registro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, usuario, contrasena }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      mostrarAlertaAuth(data.detail || "No se pudo crear la cuenta.", "error");
      return;
    }

    guardarToken(data.token);
    document.getElementById("form-registro").reset();
    mostrarVistaDashboard(data);
    mostrarAlerta(`¡Bienvenido, ${data.nombre}! Tu cuenta ha sido creada correctamente.`, "exito");
    await cargarAnalisisInicial();
  } catch (err) {
    mostrarAlertaAuth("Error de conexión con el servidor.", "error");
  }
}

async function manejarLogout() {
  const token = obtenerToken();
  if (token) {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (_err) {
      // Continuar limpieza local
    }
  }
  limpiarToken();
  ocultarAlerta();
  mostrarVistaAuth("Sesión cerrada correctamente.");
}

async function cargarAnalisisInicial() {
  try {
    const resp = await fetchConAuth("/api/analisis");
    const data = await resp.json();
    if (!resp.ok) {
      mostrarAlerta(data.detail || "No se pudo cargar el análisis inicial.", "error");
      return;
    }
    renderizarDashboard(data);
    await ejecutarPrediccion();
  } catch (err) {
    if (err.message !== "Sesión no autorizada") {
      mostrarAlerta("Error de conexión con el servidor FastAPI.", "error");
    }
  }
}

async function subirArchivoCSV(archivo) {
  const formData = new FormData();
  formData.append("file", archivo);

  try {
    mostrarAlerta(`Procesando y entrenando modelo con "${archivo.name}"...`, "info");
    const resp = await fetchConAuth("/api/cargar-csv", {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();

    if (!resp.ok) {
      mostrarAlerta(data.detail || "El archivo CSV no pudo ser procesado.", "error");
      return;
    }

    renderizarDashboard(data);
    await ejecutarPrediccion();
    mostrarAlerta(`Modelo reentrenado correctamente con "${archivo.name}" (${data.kpis.total_registros} registros).`, "exito");
  } catch (err) {
    if (err.message !== "Sesión no autorizada") {
      mostrarAlerta("Error al subir el archivo CSV al servidor.", "error");
    }
  }
}

async function ejecutarPrediccion() {
  const payload = {
    superficie_m2: parseFloat(document.getElementById("num-x1").value),
    habitaciones: parseInt(document.getElementById("num-x2").value, 10),
    antiguedad_anios: parseFloat(document.getElementById("num-x3").value),
    distancia_centro_km: parseFloat(document.getElementById("num-x4").value),
  };

  try {
    const resp = await fetchConAuth("/api/predecir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();

    if (!resp.ok) {
      mostrarAlerta(data.detail || "Revisa los valores ingresados en el simulador.", "error");
      return;
    }

    document.getElementById("resultado-precio").textContent = formatoBs(data.precio_estimado);
    document.getElementById("resultado-rango").textContent =
      `${formatoBs(data.rango_minimo)} Bs — ${formatoBs(data.rango_maximo)} Bs`;
    document.getElementById("formula-evaluada").textContent = data.formula_evaluada;

    document.getElementById("desglose-lista").innerHTML = data.desglose
      .map((item) => {
        const positivo = item.aporte >= 0;
        const colorAporte = positivo ? "text-emerald-600" : "text-rose-600";
        const signo = positivo ? "+" : "-";
        return `
          <div class="flex items-center justify-between gap-2 px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-100 text-sm">
            <div>
              <span class="font-bold text-indigo-700 mr-1">${item.simbolo}</span>
              <span class="font-medium text-slate-800">${item.nombre}</span>
              <p class="text-[11px] text-slate-400 font-mono">
                (${item.coeficiente}) × ${item.valor_entrada}
              </p>
            </div>
            <span class="font-mono font-bold ${colorAporte}">
              ${signo}${formatoBs(Math.abs(item.aporte))} Bs
            </span>
          </div>`;
      })
      .join("");
  } catch (err) {
    if (err.message !== "Sesión no autorizada") {
      mostrarAlerta("No se pudo conectar con el servicio de predicción.", "error");
    }
  }
}

// ==================== EVENTOS E INICIALIZACIÓN ====================

function inicializarSelectorAuth() {
  const btnLogin = document.getElementById("btn-modo-login");
  const btnRegistro = document.getElementById("btn-modo-registro");
  const formLogin = document.getElementById("form-login");
  const formRegistro = document.getElementById("form-registro");

  btnLogin.addEventListener("click", () => {
    ocultarAlertaAuth();
    formLogin.classList.remove("hidden");
    formRegistro.classList.add("hidden");
    btnLogin.className = "py-2 text-sm font-semibold rounded-lg bg-white text-indigo-700 shadow-sm transition cursor-pointer";
    btnRegistro.className = "py-2 text-sm font-medium rounded-lg text-slate-600 hover:text-slate-900 transition cursor-pointer";
  });

  btnRegistro.addEventListener("click", () => {
    ocultarAlertaAuth();
    formRegistro.classList.remove("hidden");
    formLogin.classList.add("hidden");
    btnRegistro.className = "py-2 text-sm font-semibold rounded-lg bg-white text-indigo-700 shadow-sm transition cursor-pointer";
    btnLogin.className = "py-2 text-sm font-medium rounded-lg text-slate-600 hover:text-slate-900 transition cursor-pointer";
  });

  // Botón rápido para autocompletar la credencial por defecto
  document.getElementById("btn-rellenar-demo").addEventListener("click", () => {
    document.getElementById("login-usuario").value = "admin";
    document.getElementById("login-contrasena").value = "admin123";
  });
}

function inicializarPestanas() {
  const botones = document.querySelectorAll(".tab-btn");
  const paneles = document.querySelectorAll(".tab-panel");

  botones.forEach((btn) => {
    btn.addEventListener("click", () => {
      const destino = btn.dataset.tab;

      botones.forEach((b) => {
        b.classList.remove("bg-indigo-50", "text-indigo-700", "font-semibold");
        b.classList.add("text-slate-600", "hover:bg-slate-100", "font-medium");
      });
      btn.classList.add("bg-indigo-50", "text-indigo-700", "font-semibold");
      btn.classList.remove("text-slate-600", "hover:bg-slate-100", "font-medium");

      paneles.forEach((p) => p.classList.remove("active"));
      document.getElementById(`tab-${destino}`).classList.add("active");
    });
  });
}

function sincronizarSliders() {
  const pares = [
    ["slider-x1", "num-x1"],
    ["slider-x2", "num-x2"],
    ["slider-x3", "num-x3"],
    ["slider-x4", "num-x4"],
  ];

  pares.forEach(([sliderId, numId]) => {
    const slider = document.getElementById(sliderId);
    const num = document.getElementById(numId);

    slider.addEventListener("input", () => {
      num.value = slider.value;
    });

    num.addEventListener("input", () => {
      if (num.value !== "") {
        slider.value = num.value;
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  inicializarSelectorAuth();
  inicializarPestanas();
  sincronizarSliders();

  // Eventos de autenticación
  document.getElementById("form-login").addEventListener("submit", manejarLogin);
  document.getElementById("form-registro").addEventListener("submit", manejarRegistro);
  document.getElementById("btn-cerrar-sesion").addEventListener("click", manejarLogout);

  // Eventos del dashboard
  const inputCsv = document.getElementById("input-csv");
  document.getElementById("btn-subir-csv").addEventListener("click", () => inputCsv.click());
  inputCsv.addEventListener("change", (e) => {
    const archivo = e.target.files[0];
    if (archivo) {
      subirArchivoCSV(archivo);
      inputCsv.value = "";
    }
  });

  document.getElementById("form-simulador").addEventListener("submit", (e) => {
    e.preventDefault();
    ejecutarPrediccion();
  });

  document.getElementById("cerrar-alerta").addEventListener("click", ocultarAlerta);

  // Verificar si ya hay sesión activa
  verificarSesionInicial();
});