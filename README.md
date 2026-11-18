# MATRIX PRO (PyQt6)

Calculadora matricial educativa para Windows, Python 3.10+ y PyQt6. La interfaz incluye editor matricial dinámico, panel de resultados y pasos, historial, importación/exportación CSV y PDF, copia al portapapeles y tema claro/oscuro.

## Preparar el entorno

Desde esta carpeta, en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell impide activar el entorno, también se puede invocar directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecutar y probar

```powershell
python main.py
python -m unittest discover -s tests -v
python main.py --self-test-ui
```

Las celdas aceptan enteros, decimales y fracciones como `-3/4`. Las operaciones racionales usan `fractions.Fraction` para conservar exactitud; QR, Cholesky, SVD y valores propios son aproximaciones numéricas.

## Crear el ejecutable de Windows

Con el entorno virtual activado:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MATRIX_PRO main.py
```

El programa quedará en `dist\MATRIX_PRO.exe`. PyInstaller genera un ejecutable para el sistema operativo donde se ejecuta; para Windows, constrúyelo en Windows.

## Alcance numérico

La expansión de Laplace/Sarrus y Gauss-Jordan conserva fracciones exactas. Sarrus solo se habilita para matrices 3×3. QR usa Gram–Schmidt y requiere filas ≥ columnas; Cholesky requiere una matriz simétrica definida positiva. Valores propios se implementan para matrices simétricas por Jacobi; SVD presenta valores singulares aproximados a partir de `AᵀA`. Las dimensiones están limitadas por memoria disponible y por el tamaño práctico del editor Qt.

Esta versión no implementa todavía polinomio característico, diagonalización, vectores singulares, ni resolución de sistemas por Cramer, LU, sustitución o igualación. Los sistemas se clasifican y resuelven mediante Gauss-Jordan. La inversa está disponible por Gauss-Jordan y adjunta/cofactores; las operaciones elementales expuestas son las utilizadas durante la reducción, no un editor general de filas y columnas.
