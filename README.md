# Simulador de Costos ESAP

Aplicación en Streamlit para simular costos operativos de concursos de mérito, con cálculo paramétrico por ciudad, modalidad, formas de prueba y volumen de aspirantes.

## Objetivo del proyecto

Este simulador centraliza la lógica de costeo para que el presupuesto se genere a partir de reglas de negocio y tarifarios, no de modelos predictivos genéricos. La idea es que el resultado sea auditable, reproducible y fácil de extender.

## Bloques funcionales actuales

El archivo principal está organizado por secciones para facilitar la lectura y el crecimiento futuro:

1. Configuración visual y estilos globales.
2. Datos maestros y tarifarios por ciudad.
3. Motor de cálculo de costos.
4. Capa de interfaz para cotización multi-ciudad.
5. Vistas analíticas y exportación de reportes.

## Qué se puede optimizar

1. Separar la lógica de negocio de la UI para reducir el tamaño del archivo principal.
2. Unificar nombres de claves financieras para evitar errores de totales o gráficos vacíos.
3. Extraer estilos CSS a un archivo dedicado si se van a mantener varias vistas.
4. Agrupar funciones repetidas de resumen, exportación y agregación en utilidades comunes.
5. Mover tarifarios y constantes a módulos de datos para simplificar mantenimiento.

## Estructura modular recomendada

La siguiente división deja la base lista para agregar módulos sin seguir creciendo en un solo archivo:

- `app.py`: punto de entrada Streamlit.
- `core/calculos.py`: funciones de costeo y reglas de negocio.
- `core/datos.py`: tarifarios, constantes y listas maestras.
- `ui/estilos.py`: CSS y componentes visuales compartidos.
- `ui/vistas.py`: renderizado de pantallas, tabs y reportes.
- `utils/exportacion.py`: CSV, HTML y futuros formatos.

## Siguiente paso sugerido

Si quieres, el siguiente refactor puede ser uno de estos:

1. Extraer todo el motor de cálculo a `core/calculos.py`.
2. Separar la vista multi-ciudad en un módulo `ui/vistas.py`.
3. Dividir el tarifario y las constantes en `core/datos.py`.

## Dependencias

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

Para ejecutar la app:

```bash
streamlit run simulador_de_costos.py
```

