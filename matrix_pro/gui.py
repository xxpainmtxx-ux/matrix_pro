"""Interfaz de escritorio de MATRIX PRO, construida con PyQt6."""

from __future__ import annotations

import csv
import html
import random
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import engine


# Operaciones agrupadas para construir la navegación y decidir qué entradas mostrar.
OPERATIONS = {
    "Operaciones básicas": [
        "Suma A + B", "Resta A − B", "Producto A × B",
        "Multiplicar por escalar", "Dividir por escalar", "Potencia Aⁿ",
        "Opuesta −A", "Transpuesta Aᵀ",
    ],
    "Determinantes": [
        "Determinante por Gauss", "Determinante por Laplace/cofactores",
        "Regla de Sarrus (3×3)", "Menores y cofactores",
    ],
    "Matriz inversa": ["Inversa por Gauss–Jordan", "Inversa por adjunta/cofactores"],
    "Análisis": ["Diagonales, elementos y propiedades"],
    "Sistemas lineales": ["Resolver sistema A·x = b"],
    "Espacios vectoriales": ["Rango, bases, nulidad y núcleo"],
    "Descomposiciones": [
        "LU con pivoteo", "QR (Gram–Schmidt)", "Cholesky",
        "SVD (valores singulares)",
    ],
    "Valores propios": ["Valores y vectores propios (matriz simétrica)"],
    "Generador": ["Matriz aleatoria", "Matriz nula", "Matriz identidad"],
}

NEEDS_B = {"Suma A + B", "Resta A − B", "Producto A × B", "Resolver sistema A·x = b"}
NEEDS_SCALAR = {"Multiplicar por escalar", "Dividir por escalar", "Potencia Aⁿ"}


# Genera un informe imprimible con el resultado y sus pasos.
def write_pdf_report(filename: str, summary: str, steps: str) -> None:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(filename)
    document = QTextDocument()
    document.setHtml(
        "<h1>MATRIX PRO</h1><h2>Resultado</h2><pre>"
        + html.escape(summary)
        + "</pre><h2>Procedimiento paso a paso</h2><pre>"
        + html.escape(steps)
        + "</pre>"
    )
    document.print(printer)


# Editor reutilizable que mantiene sincronizadas las dimensiones y las celdas.
class MatrixEditor(QGroupBox):
    """Editor de celdas y dimensiones para una matriz."""

    def __init__(self, title: str, initial: list[list[str]], parent: QWidget | None = None):
        super().__init__(title, parent)
        # Controles de dimensiones, tabla de datos y distribución del editor.
        self.row_count = QSpinBox()
        self.column_count = QSpinBox()
        for control in (self.row_count, self.column_count):
            control.setRange(1, 2_147_483_647)
            control.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
            control.setMinimumWidth(84)
        self.row_count.setValue(len(initial))
        self.column_count.setValue(len(initial[0]))

        dimensions = QHBoxLayout()
        dimensions.addWidget(QLabel("Filas"))
        dimensions.addWidget(self.row_count)
        dimensions.addSpacing(10)
        dimensions.addWidget(QLabel("Columnas"))
        dimensions.addWidget(self.column_count)
        dimensions.addStretch(1)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setDefaultSectionSize(86)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.addLayout(dimensions)
        layout.addWidget(self.table)
        self.row_count.valueChanged.connect(self._resize_table)
        self.column_count.valueChanged.connect(self._resize_table)
        self.set_values(initial)

    def _resize_table(self) -> None:
        # Conserva las celdas existentes y rellena con cero las nuevas posiciones.
        old = [
            [self.table.item(row, col).text() if self.table.item(row, col) else ""
             for col in range(self.table.columnCount())]
            for row in range(self.table.rowCount())
        ]
        rows, cols = self.row_count.value(), self.column_count.value()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.table.setHorizontalHeaderLabels([f"C{col + 1}" for col in range(cols)])
        self.table.setVerticalHeaderLabels([f"F{row + 1}" for row in range(rows)])
        for row in range(rows):
            for col in range(cols):
                text = old[row][col] if row < len(old) and col < len(old[row]) else "0"
                self.table.setItem(row, col, QTableWidgetItem(text))

    def set_values(self, values: list[list[str | int | float]]) -> None:
        # Actualiza dimensiones y celdas sin disparar eventos de redimensionado.
        rows, cols = len(values), len(values[0])
        self.row_count.blockSignals(True)
        self.column_count.blockSignals(True)
        self.row_count.setValue(rows)
        self.column_count.setValue(cols)
        self.row_count.blockSignals(False)
        self.column_count.blockSignals(False)
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.table.setHorizontalHeaderLabels([f"C{col + 1}" for col in range(cols)])
        self.table.setVerticalHeaderLabels([f"F{row + 1}" for row in range(rows)])
        for row in range(rows):
            for col in range(cols):
                self.table.setItem(row, col, QTableWidgetItem(str(values[row][col])))

    def get_matrix(self) -> engine.Matrix:
        # Lee las celdas, valida que no estén vacías y convierte cada valor numérico.
        values: list[list[str]] = []
        for row in range(self.table.rowCount()):
            current: list[str] = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                text = item.text().strip() if item else ""
                if not text:
                    raise engine.MatrixError(
                        f"Falta el valor en {self.title()}[{row + 1},{col + 1}]."
                    )
                current.append(text.replace(",", "."))
            values.append(current)
        return engine.as_matrix(values)


# Ventana principal: coordina navegación, editores, cálculos y utilidades de archivo.
class MatrixProWindow(QMainWindow):
    """Ventana principal con navegación, edición, pasos y utilidades."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MATRIX PRO")
        self.resize(1420, 900)
        self.setMinimumSize(980, 680)
        self.dark_mode = True
        self.history: list[str] = []
        self.last_matrix: list[list[engine.Number | float]] | None = None
        self._build_ui()
        self._apply_theme()
        self.navigation.setCurrentRow(0)

    def _build_ui(self) -> None:
        # Panel lateral con marca, categorías de operaciones y selector de tema.
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(238)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(18, 24, 14, 18)
        brand = QLabel("MATRIX PRO")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        subtitle = QLabel("LABORATORIO MATEMÁTICO")
        subtitle.setObjectName("sideSubtitle")
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(18)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setSpacing(5)
        for category in OPERATIONS:
            item = QListWidgetItem("  " + category)
            item.setData(Qt.ItemDataRole.UserRole, category)
            self.navigation.addItem(item)
        self.navigation.currentRowChanged.connect(self._select_category)
        side_layout.addWidget(self.navigation, 1)

        self.theme_button = QPushButton("☀  Cambiar a modo claro")
        self.theme_button.clicked.connect(self._toggle_theme)
        side_layout.addWidget(self.theme_button)

        # Encabezado de contenido y controles de operación/parámetros.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 22, 26, 22)
        content_layout.setSpacing(14)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        self.page_title = QLabel("Operaciones básicas")
        self.page_title.setObjectName("pageTitle")
        heading.addWidget(self.page_title)
        self.page_description = QLabel("Calcula con fracciones exactas y consulta cada transformación.")
        self.page_description.setObjectName("muted")
        heading.addWidget(self.page_description)
        header.addLayout(heading, 1)
        self.operation_combo = QComboBox()
        self.operation_combo.setMinimumWidth(270)
        self.operation_combo.currentTextChanged.connect(self._operation_changed)
        header.addWidget(QLabel("Operación"))
        header.addWidget(self.operation_combo)
        content_layout.addLayout(header)

        parameter_row = QHBoxLayout()
        self.parameter_label = QLabel("Parámetro")
        self.parameter_edit = QLineEdit()
        self.parameter_edit.setPlaceholderText("Ej.: 3/4, -2 o 1.25")
        self.parameter_edit.setMaximumWidth(190)
        parameter_row.addWidget(self.parameter_label)
        parameter_row.addWidget(self.parameter_edit)
        self.generator_hint = QLabel("Introduce fracciones (3/4), decimales o negativos en las celdas.")
        self.generator_hint.setObjectName("muted")
        parameter_row.addWidget(self.generator_hint, 1)
        content_layout.addLayout(parameter_row)

        # Editores de matrices A y B colocados en un divisor redimensionable.
        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_a = MatrixEditor("Matriz A", [["1", "2"], ["3", "4"]])
        self.editor_b = MatrixEditor("Matriz B / vector b", [["5", "6"], ["7", "8"]])
        self.editor_splitter.addWidget(self.editor_a)
        self.editor_splitter.addWidget(self.editor_b)
        self.editor_splitter.setSizes([1, 1])
        content_layout.addWidget(self.editor_splitter, 3)

        # Acciones de cálculo, edición, copia e importación/exportación.
        actions = QHBoxLayout()
        self.calculate_button = QPushButton("Calcular")
        self.calculate_button.setObjectName("primaryButton")
        self.calculate_button.clicked.connect(self.calculate)
        actions.addWidget(self.calculate_button)
        clear_button = QPushButton("Limpiar")
        clear_button.clicked.connect(self.clear_output)
        actions.addWidget(clear_button)
        reset_button = QPushButton("Reiniciar matrices")
        reset_button.clicked.connect(self.reset_matrices)
        actions.addWidget(reset_button)
        actions.addStretch(1)
        import_button = QPushButton("Importar CSV")
        import_button.clicked.connect(self.import_csv)
        actions.addWidget(import_button)
        copy_button = QPushButton("Copiar")
        copy_button.clicked.connect(self.copy_result)
        actions.addWidget(copy_button)
        csv_button = QPushButton("Exportar CSV")
        csv_button.clicked.connect(self.export_csv)
        actions.addWidget(csv_button)
        pdf_button = QPushButton("Exportar PDF")
        pdf_button.clicked.connect(self.export_pdf)
        actions.addWidget(pdf_button)
        save_button = QPushButton("Guardar ejercicio")
        save_button.clicked.connect(self.save_history)
        actions.addWidget(save_button)
        content_layout.addLayout(actions)

        # Paneles de salida para el resumen del resultado y el procedimiento detallado.
        output_splitter = QSplitter(Qt.Orientation.Horizontal)
        result_group = QGroupBox("Resultado")
        result_layout = QVBoxLayout(result_group)
        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setPlaceholderText("El resultado aparecerá aquí.")
        result_layout.addWidget(self.result_view)
        output_splitter.addWidget(result_group)

        steps_group = QGroupBox("Procedimiento paso a paso")
        steps_layout = QVBoxLayout(steps_group)
        self.steps_view = QPlainTextEdit()
        self.steps_view.setReadOnly(True)
        self.steps_view.setPlaceholderText("Las operaciones y transformaciones se mostrarán aquí.")
        steps_layout.addWidget(self.steps_view)
        output_splitter.addWidget(steps_group)
        output_splitter.setSizes([1, 1])
        content_layout.addWidget(output_splitter, 2)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Listo · Fracciones exactas habilitadas")

    def _apply_theme(self) -> None:
        # Selecciona la paleta activa y la aplica de forma uniforme a los widgets.
        if self.dark_mode:
            background, panel, text, muted, border = "#0b1220", "#111c2f", "#e7edf7", "#93a4bd", "#24354d"
            accent, table_alt = "#32c4a0", "#142238"
        else:
            background, panel, text, muted, border = "#f3f6fb", "#ffffff", "#182437", "#62728a", "#d9e1ed"
            accent, table_alt = "#087f69", "#f5f8fc"
        self.setStyleSheet(f"""
            QWidget {{ background: {background}; color: {text}; font-size: 13px; }}
            #sidebar {{ background: {panel}; border-right: 1px solid {border}; }}
            #brand {{ font-size: 24px; font-weight: 800; color: {accent}; letter-spacing: 1px; }}
            #sideSubtitle, #muted {{ color: {muted}; }}
            #sideSubtitle {{ font-size: 10px; letter-spacing: 1.3px; }}
            #pageTitle {{ font-size: 24px; font-weight: 700; }}
            QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {{
                background: {panel}; border: 1px solid {border}; border-radius: 7px; padding: 6px;
                selection-background-color: {accent}; selection-color: #07131d;
            }}
            QListWidget {{ border: 0; background: transparent; }}
            QListWidget::item {{ padding: 12px 8px; border-radius: 7px; }}
            QListWidget::item:selected {{ background: {accent}; color: #07131d; font-weight: 700; }}
            QPushButton {{ background: {panel}; border: 1px solid {border}; border-radius: 7px; padding: 9px 12px; }}
            QPushButton:hover {{ border-color: {accent}; }}
            #primaryButton {{ background: {accent}; color: #07131d; font-weight: 800; border: 0; }}
            QGroupBox {{ border: 1px solid {border}; border-radius: 9px; margin-top: 12px; padding-top: 10px; font-weight: 700; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; }}
            QHeaderView::section {{ background: {panel}; color: {muted}; border: 0; padding: 5px; }}
            QTableWidget {{ alternate-background-color: {table_alt}; gridline-color: {border}; }}
            QStatusBar {{ color: {muted}; }}
        """)

    def _toggle_theme(self) -> None:
        # Cambia entre paletas y actualiza la etiqueta del botón.
        self.dark_mode = not self.dark_mode
        self.theme_button.setText("☀  Cambiar a modo claro" if self.dark_mode else "☾  Cambiar a modo oscuro")
        self._apply_theme()

    def _select_category(self, row: int) -> None:
        # Carga las operaciones de la categoría seleccionada en el menú superior.
        if row < 0:
            return
        category = list(OPERATIONS)[row]
        self.page_title.setText(category)
        self.operation_combo.blockSignals(True)
        self.operation_combo.clear()
        self.operation_combo.addItems(OPERATIONS[category])
        self.operation_combo.blockSignals(False)
        self._operation_changed(self.operation_combo.currentText())

    def _operation_changed(self, operation: str) -> None:
        # Muestra solo los controles requeridos por la operación actual.
        if not operation:
            return
        self.editor_b.setVisible(operation in NEEDS_B)
        self.parameter_label.setVisible(operation in NEEDS_SCALAR)
        self.parameter_edit.setVisible(operation in NEEDS_SCALAR)
        self.generator_hint.setText(
            "Generador: valores aleatorios enteros de −9 a 9." if operation == "Matriz aleatoria"
            else "Introduce fracciones (3/4), decimales o negativos en las celdas."
        )

    def _show_result(self, summary: str, steps: list[str], matrix: list[list[engine.Number | float]] | None = None) -> None:
        # Actualiza vistas, matriz exportable, historial y estado de la aplicación.
        self.result_view.setPlainText(summary)
        self.steps_view.setPlainText(
            "\n\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
            if steps else "Este cálculo no necesita transformaciones intermedias."
        )
        self.last_matrix = matrix
        record = f"MATRIX PRO\n{summary}\n\nPROCEDIMIENTO\n" + "\n\n".join(steps)
        self.history.append(record)
        self.statusBar().showMessage("Cálculo completado correctamente", 5000)

    def calculate(self) -> None:
        operation = self.operation_combo.currentText()
        steps: list[str] = []
        try:
            # Las operaciones generadoras reemplazan A y muestran la matriz creada.
            if operation.startswith("Matriz "):
                rows, cols = self.editor_a.row_count.value(), self.editor_a.column_count.value()
                if operation == "Matriz identidad" and rows != cols:
                    raise engine.MatrixError("Para generar la identidad, A debe ser cuadrada.")
                if operation == "Matriz identidad":
                    matrix = engine.identity(rows)
                elif operation == "Matriz nula":
                    matrix = [[engine.Fraction(0) for _ in range(cols)] for _ in range(rows)]
                else:
                    matrix = [[engine.Fraction(random.randint(-9, 9)) for _ in range(cols)] for _ in range(rows)]
                self.editor_a.set_values([[engine.format_number(value) for value in row] for row in matrix])
                self._show_result(f"{operation} ({rows}×{cols}):\n\n{engine.format_matrix(matrix)}",
                                  ["Se generó la matriz solicitada; sus valores se copiaron al editor A."], matrix)
                return

            # Convierte los editores a matrices y prepara las entradas opcionales.
            a = self.editor_a.get_matrix()
            b = self.editor_b.get_matrix() if operation in NEEDS_B else None
            matrix: list[list[engine.Number | float]] | None = None
            # Operaciones aritméticas y transformaciones básicas de A.
            if operation == "Suma A + B":
                matrix = engine.add(a, b)  # type: ignore[arg-type]
                summary = "A + B =\n" + engine.format_matrix(matrix)
            elif operation == "Resta A − B":
                matrix = engine.subtract(a, b)  # type: ignore[arg-type]
                summary = "A − B =\n" + engine.format_matrix(matrix)
            elif operation == "Producto A × B":
                matrix = engine.multiply(a, b)  # type: ignore[arg-type]
                summary = "A × B =\n" + engine.format_matrix(matrix)
            elif operation in {"Multiplicar por escalar", "Dividir por escalar"}:
                scalar = engine.parse_number(self.parameter_edit.text())
                if operation == "Dividir por escalar":
                    if scalar == 0:
                        raise engine.MatrixError("No se puede dividir por cero.")
                    scalar = 1 / scalar
                    steps.append("Dividir cada elemento de A entre el escalar indicado.")
                else:
                    steps.append(f"Multiplicar cada elemento de A por {engine.format_number(scalar)}.")
                matrix = engine.scale(a, scalar)
                summary = "Resultado:\n" + engine.format_matrix(matrix)
            elif operation == "Potencia Aⁿ":
                exponent = int(self.parameter_edit.text().strip())
                matrix = engine.power(a, exponent)
                steps.append(f"Potenciación por cuadrados sucesivos; exponente n = {exponent}.")
                summary = f"A^{exponent} =\n" + engine.format_matrix(matrix)
            elif operation == "Opuesta −A":
                matrix = engine.scale(a, engine.Fraction(-1))
                steps.append("Aplicar (−A)ᵢⱼ = −Aᵢⱼ.")
                summary = "−A =\n" + engine.format_matrix(matrix)
            elif operation == "Transpuesta Aᵀ":
                matrix = engine.transpose(a)
                steps.append("Intercambiar filas por columnas: (Aᵀ)ᵢⱼ = Aⱼᵢ.")
                summary = "Aᵀ =\n" + engine.format_matrix(matrix)
            # Cálculo de determinantes y matrices de menores/cofactores.
            elif operation == "Determinante por Gauss":
                value = engine.determinant_gauss(a, steps)
                summary = f"det(A) = {engine.format_number(value)}"
            elif operation == "Determinante por Laplace/cofactores":
                value = engine.determinant_laplace(a, steps)
                summary = f"det(A) = {engine.format_number(value)}"
            elif operation == "Regla de Sarrus (3×3)":
                value = engine.determinant_sarrus(a, steps)
                summary = f"det(A) = {engine.format_number(value)}"
            elif operation == "Menores y cofactores":
                rows, cols = engine.validate_matrix(a)
                if rows != cols or rows < 2:
                    raise engine.MatrixError("Menores y cofactores requieren una matriz cuadrada de orden ≥ 2.")
                minors: list[list[engine.Number]] = []
                cofactors: list[list[engine.Number]] = []
                for i in range(rows):
                    minor_row, cofactor_row = [], []
                    for j in range(cols):
                        minor = engine.minor_matrix(a, i, j)
                        minor_det = engine.determinant_laplace(minor, steps)
                        cofactor = (-1) ** (i + j) * minor_det
                        minor_row.append(minor_det)
                        cofactor_row.append(cofactor)
                        steps.append(
                            f"M({i + 1},{j + 1}) = {engine.format_number(minor_det)}; "
                            f"C({i + 1},{j + 1}) = (−1)^{i + j}·M = {engine.format_number(cofactor)}."
                        )
                    minors.append(minor_row)
                    cofactors.append(cofactor_row)
                summary = "Matriz de menores:\n" + engine.format_matrix(minors)
                summary += "\n\nMatriz de cofactores:\n" + engine.format_matrix(cofactors)
            # Inversas por reducción o mediante la matriz adjunta.
            elif operation == "Inversa por Gauss–Jordan":
                matrix = engine.inverse(a, steps)
                summary = "A⁻¹ =\n" + engine.format_matrix(matrix)
            elif operation == "Inversa por adjunta/cofactores":
                rows, cols = engine.validate_matrix(a)
                if rows != cols:
                    raise engine.MatrixError("La inversa requiere una matriz cuadrada.")
                det_steps: list[str] = []
                det = engine.determinant_laplace(a, det_steps)
                if det == 0:
                    raise engine.MatrixError("La matriz es singular: no tiene inversa.")
                cofactors = ([[engine.Fraction(1)]] if rows == 1 else [
                    [(-1) ** (i + j) * engine.determinant_laplace(engine.minor_matrix(a, i, j), steps)
                     for j in range(cols)]
                    for i in range(rows)
                ])
                adjugate = engine.transpose(cofactors)
                matrix = engine.scale(adjugate, 1 / det)
                steps.extend(det_steps)
                steps.append(f"Dividir adj(A) entre det(A) = {engine.format_number(det)}.")
                summary = "A⁻¹ = adj(A)/det(A):\n" + engine.format_matrix(matrix)
            # Análisis de propiedades, sistemas lineales, rango, bases y núcleo.
            elif operation == "Diagonales, elementos y propiedades":
                summary, steps = engine.analyze(a)
                rows, cols = engine.validate_matrix(a)
                if rows == cols:
                    steps.append(f"Diagonal principal: {', '.join(engine.format_number(a[i][i]) for i in range(rows))}.")
                    steps.append("Diagonal secundaria: " + ", ".join(
                        engine.format_number(a[i][cols - 1 - i]) for i in range(rows)
                    ) + ".")
                    steps.append("Suma total de elementos: " + engine.format_number(
                        sum((value for row in a for value in row), engine.Fraction(0))
                    ) + ".")
            elif operation == "Resolver sistema A·x = b":
                classification, details = engine.solve_system(a, b, steps)  # type: ignore[arg-type]
                summary = classification + ("\n\n" + details if details else "")
            elif operation == "Rango, bases, nulidad y núcleo":
                rows, cols = engine.validate_matrix(a)
                reduced = engine.rref(a, steps)
                row_basis = reduced.matrix[:len(reduced.pivots)]
                col_basis = [[a[row][col] for row in range(rows)] for col in reduced.pivots]
                kernel = engine.nullspace_basis(reduced, cols)
                summary = (
                    f"Rango(A) = {len(reduced.pivots)}\nNulidad(A) = {cols - len(reduced.pivots)}\n"
                    f"Columnas linealmente independientes: {'sí' if len(reduced.pivots) == cols else 'no'}\n\n"
                    f"Forma escalonada reducida:\n{engine.format_matrix(reduced.matrix)}\n\n"
                    f"Base del espacio fila (filas):\n{engine.format_matrix(row_basis) if row_basis else '∅'}\n\n"
                    f"Base del espacio columna (columnas mostradas como filas):\n"
                    f"{engine.format_matrix(col_basis) if col_basis else '∅'}\n\n"
                    "Base del núcleo (vectores mostrados como filas):\n"
                    f"{engine.format_matrix(kernel) if kernel else '∅'}"
                )
            # Descomposiciones matriciales y cálculos espectrales aproximados.
            elif operation == "LU con pivoteo":
                lower, upper, permutation = engine.lu_decomposition(a, steps)
                matrix = lower
                summary = (
                    "P·A = L·U\n\nL:\n" + engine.format_matrix(lower)
                    + "\n\nU:\n" + engine.format_matrix(upper)
                    + "\n\nPermutación de filas: " + ", ".join(str(value + 1) for value in permutation)
                )
                steps.append("El pivoteo mantiene P·A = L·U.")
            elif operation == "QR (Gram–Schmidt)":
                q, r = engine.qr_decomposition(a, steps)
                matrix = q
                summary = "A = Q·R\n\nQ:\n" + engine.format_matrix(q) + "\n\nR:\n" + engine.format_matrix(r)
            elif operation == "Cholesky":
                lower = engine.cholesky(a, steps)
                matrix = lower
                summary = "A = L·Lᵀ\n\nL:\n" + engine.format_matrix(lower)
            elif operation == "SVD (valores singulares)":
                values = engine.singular_values(a, steps)
                summary = "Valores singulares aproximados (en orden descendente):\n" + "\n".join(
                    f"σ{i + 1} = {engine.format_number(value)}" for i, value in enumerate(values)
                )
            elif operation == "Valores y vectores propios (matriz simétrica)":
                values, vectors = engine.symmetric_eigen(a, steps)
                summary = "Valores propios aproximados:\n" + "\n".join(
                    f"λ{i + 1} = {engine.format_number(value)}" for i, value in enumerate(values)
                )
                summary += "\n\nVectores propios (columnas):\n" + engine.format_matrix(vectors)
            else:
                raise engine.MatrixError("Operación todavía no disponible.")
            self._show_result(summary, steps, matrix)
        except (engine.MatrixError, ValueError, OverflowError) as error:
            self.statusBar().showMessage("No se pudo completar el cálculo", 5000)
            QMessageBox.warning(self, "MATRIX PRO · Entrada no válida", str(error))

    def clear_output(self) -> None:
        # Limpia los paneles de salida y descarta la matriz disponible para exportar.
        self.result_view.clear()
        self.steps_view.clear()
        self.last_matrix = None

    def reset_matrices(self) -> None:
        # Restaura matrices de ejemplo, limpia el parámetro y vacía las salidas.
        self.editor_a.set_values([["1", "2"], ["3", "4"]])
        self.editor_b.set_values([["5", "6"], ["7", "8"]])
        self.parameter_edit.clear()
        self.clear_output()
        self.statusBar().showMessage("Matrices reiniciadas", 3000)

    def import_csv(self) -> None:
        # Importa un CSV rectangular y carga sus datos en el editor de la matriz A.
        filename, _ = QFileDialog.getOpenFileName(self, "Importar matriz CSV", "", "CSV (*.csv);;Todos (*.*)")
        if not filename:
            return
        try:
            with open(filename, newline="", encoding="utf-8-sig") as file:
                rows = [[cell.strip() for cell in row] for row in csv.reader(file) if row]
            matrix = engine.as_matrix(rows)
            self.editor_a.set_values([[engine.format_number(value) for value in row] for row in matrix])
            self.statusBar().showMessage(f"Matriz importada: {Path(filename).name}", 5000)
        except (OSError, engine.MatrixError, csv.Error) as error:
            QMessageBox.warning(self, "No se pudo importar el CSV", str(error))

    def copy_result(self) -> None:
        # Copia al portapapeles el resultado junto con los pasos del cálculo.
        text = self.result_view.toPlainText()
        if not text:
            self.statusBar().showMessage("No hay resultados para copiar", 3000)
            return
        QApplication.clipboard().setText(text + "\n\nProcedimiento:\n" + self.steps_view.toPlainText())
        self.statusBar().showMessage("Resultado y procedimiento copiados", 3000)

    def export_csv(self) -> None:
        # Guarda como CSV la matriz producida por el último cálculo.
        if self.last_matrix is None:
            QMessageBox.information(self, "Exportar CSV", "El último cálculo no produjo una matriz.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar matriz CSV", "resultado.csv", "CSV (*.csv)")
        if not filename:
            return
        try:
            with open(filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows([[engine.format_number(value) for value in row] for row in self.last_matrix])
            self.statusBar().showMessage(f"CSV guardado: {Path(filename).name}", 5000)
        except OSError as error:
            QMessageBox.critical(self, "Error al exportar CSV", str(error))

    def export_pdf(self) -> None:
        # Exporta a PDF el resultado y el procedimiento actualmente visibles.
        if not self.result_view.toPlainText():
            QMessageBox.information(self, "Exportar PDF", "Primero realiza un cálculo.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar procedimiento PDF", "ejercicio.pdf", "PDF (*.pdf)")
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        try:
            write_pdf_report(filename, self.result_view.toPlainText(), self.steps_view.toPlainText())
            self.statusBar().showMessage(f"PDF guardado: {Path(filename).name}", 5000)
        except OSError as error:
            QMessageBox.critical(self, "Error al exportar PDF", str(error))

    def save_history(self) -> None:
        # Persiste todos los ejercicios completados en un archivo de texto.
        if not self.history:
            QMessageBox.information(self, "Guardar ejercicios", "Aún no hay cálculos en el historial.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Guardar historial de ejercicios", "matrix_pro_ejercicios.txt", "Texto (*.txt)"
        )
        if not filename:
            return
        try:
            Path(filename).write_text(
                ("\n\n" + ("=" * 72) + "\n\n").join(self.history), encoding="utf-8"
            )
            self.statusBar().showMessage("Historial guardado correctamente", 5000)
        except OSError as error:
            QMessageBox.critical(self, "Error al guardar", str(error))

