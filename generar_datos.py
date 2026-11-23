import numpy as np
import pandas as pd


def generar_csv_alquileres(ruta_salida: str = "alquileres.csv", n_registros: int = 150) -> None:
    """
    Genera un dataset ficticio y realista de alquileres mensuales en Bolivianos (Bs)
    siguiendo una relación lineal múltiple con ruido gaussiano controlado.
    """
    # Semilla fija para garantizar reproducibilidad en pruebas y defensa
    rng = np.random.default_rng(42)

    # X1: Superficie habitable en metros cuadrados (35 a 180 m²)
    superficie_m2 = np.round(rng.uniform(35, 180, size=n_registros), 1)

    # X2: Número de habitaciones (1 a 5), correlacionado de forma natural con la superficie
    # Se agrega variabilidad para evitar colinealidad exacta con X1
    habitaciones_base = superficie_m2 / 36.0 + rng.normal(0, 0.65, size=n_registros)
    habitaciones = np.clip(np.round(habitaciones_base), 1, 5).astype(int)

    # X3: Antigüedad del inmueble en años (0 a 30 años)
    antiguedad_anios = rng.integers(0, 31, size=n_registros)

    # X4: Distancia al centro o avenida principal en kilómetros (0.3 a 12.0 km)
    distancia_centro_km = np.round(rng.uniform(0.3, 12.0, size=n_registros), 2)

    # Parámetros reales subyacentes para construir la variable objetivo Y
    beta_0 = 1650.0   # Base mínima estructural (Bs)
    beta_1 = 20.5     # +20.5 Bs por cada m² adicional
    beta_2 = 285.0    # +285 Bs por cada habitación adicional
    beta_3 = -22.0    # -22 Bs por cada año de antigüedad
    beta_4 = -78.0    # -78 Bs por cada km de distancia al centro

    # Ruido aleatorio gaussiano (media 0, desviación estándar 340 Bs)
    # Permite un ajuste realista (R² entre 0.85 y 0.93) en lugar de un 1.00 artificial
    ruido = rng.normal(loc=0.0, scale=340.0, size=n_registros)

    # Ecuación generadora del precio mensual en Bs
    precio_raw = (
        beta_0
        + beta_1 * superficie_m2
        + beta_2 * habitaciones
        + beta_3 * antiguedad_anios
        + beta_4 * distancia_centro_km
        + ruido
    )

    # Mantener los precios dentro de un rango coherente de mercado (1.200 a 6.500 Bs)
    precio_alquiler_bs = np.round(np.clip(precio_raw, 1200.0, 6500.0), 2)

    df = pd.DataFrame({
        "superficie_m2": superficie_m2,
        "habitaciones": habitaciones,
        "antiguedad_anios": antiguedad_anios,
        "distancia_centro_km": distancia_centro_km,
        "precio_alquiler_bs": precio_alquiler_bs,
    })

    df.to_csv(ruta_salida, index=False, encoding="utf-8")
    print(f"Archivo '{ruta_salida}' generado correctamente con {len(df)} registros.")
    print(df.head())


if __name__ == "__main__":
    generar_csv_alquileres()