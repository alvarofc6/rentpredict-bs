import base64
import io
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")  # Backend sin ventana gráfica, seguro para servidores web
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


COLUMNAS_X = [
    "superficie_m2",
    "habitaciones",
    "antiguedad_anios",
    "distancia_centro_km",
]
COLUMNA_Y = "precio_alquiler_bs"
COLUMNAS_REQUERIDAS = COLUMNAS_X + [COLUMNA_Y]

METADATOS_VARIABLES = [
    {"simbolo": "β₀", "variable": "intercepto", "etiqueta": "Intercepto (Término independiente)", "unidad": "Bs base"},
    {"simbolo": "β₁", "variable": "superficie_m2", "etiqueta": "Superficie habitable (X₁)", "unidad": "m²"},
    {"simbolo": "β₂", "variable": "habitaciones", "etiqueta": "Número de habitaciones (X₂)", "unidad": "habitación"},
    {"simbolo": "β₃", "variable": "antiguedad_anios", "etiqueta": "Antigüedad del inmueble (X₃)", "unidad": "año de antigüedad"},
    {"simbolo": "β₄", "variable": "distancia_centro_km", "etiqueta": "Distancia al centro/avenida (X₄)", "unidad": "km de distancia"},
]


class ModeloAlquilerLineal:
    """
    Modelo de Regresión Lineal Múltiple implementado desde cero con Álgebra Lineal
    mediante la Ecuación Normal: β = (Xᵀ · X)⁻¹ · Xᵀ · Y
    """

    def __init__(self) -> None:
        self.df: pd.DataFrame | None = None
        self.archivo_activo: str = "Sin archivo"
        self.entrenado: bool = False

        # Matrices clave de la ecuación normal
        self.X: np.ndarray | None = None
        self.X_T: np.ndarray | None = None
        self.X_T_X: np.ndarray | None = None
        self.X_T_X_inv: np.ndarray | None = None
        self.Y: np.ndarray | None = None
        self.beta: np.ndarray | None = None
        self.y_pred: np.ndarray | None = None

        # Métricas de rendimiento
        self.mae: float = 0.0
        self.rmse: float = 0.0
        self.r2: float = 0.0
        self.validacion_sklearn: Dict[str, float] = {}

    def entrenar_desde_dataframe(self, df: pd.DataFrame, nombre_archivo: str = "alquileres.csv") -> None:
        """
        Valida los datos, construye las matrices y resuelve la ecuación normal.
        """
        # 1. Verificar columnas obligatorias
        faltantes = [col for col in COLUMNAS_REQUERIDAS if col not in df.columns]
        if faltantes:
            raise ValueError(
                f"El archivo CSV no contiene las columnas obligatorias: {', '.join(faltantes)}. "
                f"Se esperan: {', '.join(COLUMNAS_REQUERIDAS)}."
            )

        # 2. Limpiar y convertir a valores numéricos
        df_limpio = df[COLUMNAS_REQUERIDAS].copy()
        for col in COLUMNAS_REQUERIDAS:
            df_limpio[col] = pd.to_numeric(df_limpio[col], errors="coerce")

        df_limpio = df_limpio.dropna().reset_index(drop=True)

        if len(df_limpio) <= len(COLUMNAS_X) + 1:
            raise ValueError(
                f"Se requieren al menos {len(COLUMNAS_X) + 2} registros numéricos válidos para entrenar el modelo."
            )

        self.df = df_limpio
        self.archivo_activo = nombre_archivo

        # 3. Construcción de la matriz de diseño X con columna inicial de unos (1)
        # La columna de unos multiplica a β₀ (intercepto) para que el plano de regresión
        # no quede forzado a pasar por el origen (0, 0, 0, 0).
        n_muestras = len(df_limpio)
        columna_unos = np.ones((n_muestras, 1), dtype=float)
        matriz_caracteristicas = df_limpio[COLUMNAS_X].to_numpy(dtype=float)

        # Matriz X de dimensión (n × 5)
        self.X = np.hstack([columna_unos, matriz_caracteristicas])

        # Vector columna Y de dimensión (n × 1)
        self.Y = df_limpio[[COLUMNA_Y]].to_numpy(dtype=float)

        # 4. Aplicación paso a paso de la Ecuación Normal: β = (Xᵀ · X)⁻¹ · Xᵀ · Y
        # .T obtiene la matriz transpuesta Xᵀ de dimensión (5 × n)
        self.X_T = self.X.T

        # El operador @ realiza la multiplicación matricial estándar: (5 × n) @ (n × 5) -> (5 × 5)
        self.X_T_X = self.X_T @ self.X

        # np.linalg.inv calcula la matriz inversa (Xᵀ · X)⁻¹.
        # Si dos variables son linealmente dependientes (colinealidad exacta), el determinante
        # es 0 y NumPy lanza LinAlgError (matriz singular).
        try:
            self.X_T_X_inv = np.linalg.inv(self.X_T_X)
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                "Error de Álgebra Lineal: la matriz (Xᵀ · X) es singular y no tiene inversa. "
                "Verifica que no existan columnas constantes ni variables redundantes en tu CSV."
            ) from exc

        # Producto (Xᵀ · Y) de dimensión (5 × 1)
        X_T_Y = self.X_T @ self.Y

        # Vector final de coeficientes β de dimensión (5 × 1)
        self.beta = self.X_T_X_inv @ X_T_Y

        # 5. Predicciones sobre el conjunto de datos: Ŷ = X · β
        self.y_pred = self.X @ self.beta

        # 6. Cálculo de métricas de evaluación
        y_real_1d = self.Y.ravel()
        y_pred_1d = self.y_pred.ravel()

        self.mae = float(mean_absolute_error(y_real_1d, y_pred_1d))
        self.rmse = float(np.sqrt(mean_squared_error(y_real_1d, y_pred_1d)))
        self.r2 = float(r2_score(y_real_1d, y_pred_1d))

        # Validación cruzada contra Scikit-learn para comprobar exactitud matemática
        modelo_sk = LinearRegression()
        modelo_sk.fit(matriz_caracteristicas, y_real_1d)
        y_pred_sk = modelo_sk.predict(matriz_caracteristicas)
        self.validacion_sklearn = {
            "mae": round(float(mean_absolute_error(y_real_1d, y_pred_sk)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_real_1d, y_pred_sk))), 4),
            "r2": round(float(r2_score(y_real_1d, y_pred_sk)), 6),
        }

        self.entrenado = True

    def predecir(
        self,
        superficie_m2: float,
        habitaciones: int,
        antiguedad_anios: float,
        distancia_centro_km: float,
    ) -> Dict[str, Any]:
        """
        Estima el alquiler mensual para un nuevo inmueble usando ŷ = x · β
        y devuelve el desglose individual de cada variable.
        """
        if not self.entrenado or self.beta is None:
            raise RuntimeError("El modelo aún no ha sido entrenado. Carga un archivo CSV primero.")

        # Vector fila del nuevo inmueble con 1 al inicio para el intercepto β₀
        vector_x = np.array([1.0, superficie_m2, float(habitaciones), antiguedad_anios, distancia_centro_km])
        betas = self.beta.ravel()

        # Producto punto x · β
        precio_estimado = float(vector_x @ betas)
        precio_mostrable = max(0.0, precio_estimado)

        rango_min = max(0.0, precio_mostrable - self.rmse)
        rango_max = precio_mostrable + self.rmse

        desglose = []
        for idx, meta in enumerate(METADATOS_VARIABLES):
            coef = float(betas[idx])
            val_entrada = float(vector_x[idx])
            aporte = coef * val_entrada
            desglose.append({
                "simbolo": meta["simbolo"],
                "nombre": meta["etiqueta"],
                "valor_entrada": round(val_entrada, 2),
                "coeficiente": round(coef, 2),
                "aporte": round(aporte, 2),
            })

        formula_evaluada = (
            f"{betas[0]:.2f} "
            f"{'+' if betas[1] >= 0 else '-'} ({abs(betas[1]):.2f} × {superficie_m2}) "
            f"{'+' if betas[2] >= 0 else '-'} ({abs(betas[2]):.2f} × {habitaciones}) "
            f"{'+' if betas[3] >= 0 else '-'} ({abs(betas[3]):.2f} × {antiguedad_anios}) "
            f"{'+' if betas[4] >= 0 else '-'} ({abs(betas[4]):.2f} × {distancia_centro_km}) "
            f"= {precio_estimado:.2f} Bs"
        )

        return {
            "precio_estimado": round(precio_mostrable, 2),
            "rango_minimo": round(rango_min, 2),
            "rango_maximo": round(rango_max, 2),
            "rmse": round(self.rmse, 2),
            "desglose": desglose,
            "formula_evaluada": formula_evaluada,
        }

    def _interpretar_coeficientes(self) -> List[Dict[str, Any]]:
        """Genera interpretaciones automáticas en lenguaje natural para cada β."""
        betas = self.beta.ravel()
        lista = []
        for idx, meta in enumerate(METADATOS_VARIABLES):
            valor = float(betas[idx])
            if idx == 0:
                texto = (
                    f"Valor base teórico de partida ({valor:,.2f} Bs) cuando todas las variables "
                    "explicativas se evalúan en cero."
                )
            else:
                verbo = "aumenta" if valor >= 0 else "disminuye"
                texto = (
                    f"Por cada {meta['unidad']} adicional, el alquiler mensual {verbo} en promedio "
                    f"{abs(valor):,.2f} Bs, manteniendo constantes las demás variables."
                )
            lista.append({
                "simbolo": meta["simbolo"],
                "variable": meta["variable"],
                "etiqueta": meta["etiqueta"],
                "valor": round(valor, 4),
                "interpretacion": texto,
            })
        return lista

    def _evaluar_calidad_r2(self) -> Dict[str, str]:
        if self.r2 >= 0.85:
            return {
                "etiqueta": "Ajuste Excelente",
                "descripcion": "El modelo explica gran parte de la variabilidad de los precios de alquiler.",
            }
        if self.r2 >= 0.70:
            return {
                "etiqueta": "Ajuste Bueno",
                "descripcion": "El modelo captura adecuadamente la tendencia general de los alquileres.",
            }
        if self.r2 >= 0.50:
            return {
                "etiqueta": "Ajuste Moderado",
                "descripcion": "Existen otros factores externos (zona, acabados, garaje) que influyen en el precio.",
            }
        return {
            "etiqueta": "Ajuste Bajo",
            "descripcion": "La relación lineal en los datos cargados es débil; revisa la calidad del CSV.",
        }

    @staticmethod
    def _figura_a_base64(fig: plt.Figure) -> str:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buffer.seek(0)
        codificado = base64.b64encode(buffer.read()).decode("utf-8")
        return f"data:image/png;base64,{codificado}"

    def _generar_grafica_real_vs_predicho(self) -> str:
        y_real = self.Y.ravel()
        y_pred = self.y_pred.ravel()

        fig, ax = plt.subplots(figsize=(6.4, 4.4))
        ax.scatter(
            y_real,
            y_pred,
            color="#4f46e5",
            alpha=0.72,
            edgecolors="white",
            linewidth=0.6,
            s=52,
            label="Inmuebles evaluados",
        )

        # Línea de ajuste ideal y = x
        lim_min = min(y_real.min(), y_pred.min()) * 0.95
        lim_max = max(y_real.max(), y_pred.max()) * 1.03
        ax.plot(
            [lim_min, lim_max],
            [lim_min, lim_max],
            color="#10b981",
            linestyle="--",
            linewidth=2.2,
            label="Ajuste ideal (y = x)",
        )

        ax.set_title("Precio Real vs. Precio Predicho", fontsize=12, fontweight="bold", color="#0f172a", pad=12)
        ax.set_xlabel("Alquiler Real (Bs)", fontsize=10, color="#334155")
        ax.set_ylabel("Alquiler Predicho por el Modelo (Bs)", fontsize=10, color="#334155")
        ax.grid(True, linestyle=":", alpha=0.5, color="#cbd5e1")
        ax.legend(frameon=True, facecolor="white", edgecolor="#e2e8f0")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        return self._figura_a_base64(fig)

    def _generar_grafica_residuos(self) -> str:
        y_real = self.Y.ravel()
        y_pred = self.y_pred.ravel()
        residuos = y_real - y_pred

        fig, ax = plt.subplots(figsize=(6.4, 4.4))
        ax.hist(
            residuos,
            bins=18,
            color="#0ea5e9",
            alpha=0.78,
            edgecolor="white",
            linewidth=0.9,
        )
        ax.axvline(0, color="#ef4444", linestyle="--", linewidth=2.0, label="Error cero (0 Bs)")

        ax.set_title("Distribución de Errores Residuales (Real - Predicho)", fontsize=12, fontweight="bold", color="#0f172a", pad=12)
        ax.set_xlabel("Residuo / Error de predicción (Bs)", fontsize=10, color="#334155")
        ax.set_ylabel("Frecuencia (cantidad de inmuebles)", fontsize=10, color="#334155")
        ax.grid(True, axis="y", linestyle=":", alpha=0.5, color="#cbd5e1")
        ax.legend(frameon=True, facecolor="white", edgecolor="#e2e8f0")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        return self._figura_a_base64(fig)

    def obtener_analisis_completo(self) -> Dict[str, Any]:
        """
        Compila toda la información del modelo en un diccionario listo para serializar a JSON.
        """
        if not self.entrenado or self.df is None or self.beta is None:
            raise RuntimeError("El modelo no está entrenado.")

        df = self.df
        betas = self.beta.ravel()

        # KPIs principales
        kpis = {
            "total_registros": int(len(df)),
            "alquiler_promedio": round(float(df[COLUMNA_Y].mean()), 2),
            "superficie_promedio": round(float(df["superficie_m2"].mean()), 1),
            "precio_minimo": round(float(df[COLUMNA_Y].min()), 2),
            "precio_maximo": round(float(df[COLUMNA_Y].max()), 2),
        }

        # Estadísticas descriptivas
        desc = df.describe().round(2)
        estadisticas = {}
        for col in COLUMNAS_REQUERIDAS:
            estadisticas[col] = {
                "media": float(desc.loc["mean", col]),
                "desv_std": float(desc.loc["std", col]),
                "min": float(desc.loc["min", col]),
                "mediana": float(desc.loc["50%", col]),
                "max": float(desc.loc["max", col]),
            }

        # Matriz de correlación
        corr_df = df.corr().round(3)
        correlaciones = {
            "columnas": COLUMNAS_REQUERIDAS,
            "matriz": corr_df.to_numpy().tolist(),
        }

        # Ecuación final en formato LaTeX para KaTeX
        s1 = "+" if betas[1] >= 0 else "-"
        s2 = "+" if betas[2] >= 0 else "-"
        s3 = "+" if betas[3] >= 0 else "-"
        s4 = "+" if betas[4] >= 0 else "-"
        ecuacion_latex = (
            f"\\hat{{Y}} = {betas[0]:.2f} "
            f"{s1} {abs(betas[1]):.2f}\\,X_1 "
            f"{s2} {abs(betas[2]):.2f}\\,X_2 "
            f"{s3} {abs(betas[3]):.2f}\\,X_3 "
            f"{s4} {abs(betas[4]):.2f}\\,X_4"
        )

        calidad = self._evaluar_calidad_r2()

        return {
            "archivo_activo": self.archivo_activo,
            "kpis": kpis,
            "datos_muestra": df.head(200).round(2).to_dict(orient="records"),
            "estadisticas": estadisticas,
            "correlaciones": correlaciones,
            "algebra_lineal": {
                "dimensiones": {
                    "X": f"{self.X.shape[0]} × {self.X.shape[1]}",
                    "X_T": f"{self.X_T.shape[0]} × {self.X_T.shape[1]}",
                    "X_T_X": f"{self.X_T_X.shape[0]} × {self.X_T_X.shape[1]}",
                    "X_T_X_inv": f"{self.X_T_X_inv.shape[0]} × {self.X_T_X_inv.shape[1]}",
                    "Y": f"{self.Y.shape[0]} × {self.Y.shape[1]}",
                    "beta": f"{self.beta.shape[0]} × {self.beta.shape[1]}",
                },
                "vistas_previas": {
                    "X": np.round(self.X[:6, :], 2).tolist(),
                    "X_T": np.round(self.X_T[:, :6], 2).tolist(),
                    "X_T_X": np.round(self.X_T_X, 2).tolist(),
                    "X_T_X_inv": np.round(self.X_T_X_inv, 6).tolist(),
                    "Y": np.round(self.Y[:6, :], 2).tolist(),
                    "beta": np.round(self.beta, 4).tolist(),
                },
                "coeficientes": self._interpretar_coeficientes(),
                "ecuacion_latex": ecuacion_latex,
            },
            "metricas": {
                "mae": round(self.mae, 2),
                "rmse": round(self.rmse, 2),
                "r2": round(self.r2, 4),
                "r2_porcentaje": round(max(0.0, min(100.0, self.r2 * 100.0)), 2),
                "calidad_etiqueta": calidad["etiqueta"],
                "calidad_descripcion": calidad["descripcion"],
                "validacion_sklearn": self.validacion_sklearn,
            },
            "graficas": {
                "real_vs_predicho": self._generar_grafica_real_vs_predicho(),
                "residuos": self._generar_grafica_residuos(),
            },
        }