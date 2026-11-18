"""Punto de entrada de MATRIX PRO."""

import sys
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from matrix_pro.gui import MatrixProWindow, write_pdf_report


def main() -> int:
    # Inicializa Qt y configura la identidad de la aplicación.
    app = QApplication(sys.argv)
    app.setApplicationName("MATRIX PRO")
    app.setOrganizationName("MATRIX PRO")
    window = MatrixProWindow()
    # Ejecuta una comprobación automatizada de operaciones y exportación PDF si se solicita.
    if "--self-test-ui" in sys.argv:
        if window.operation_combo.count() == 0 or window.editor_a.table.rowCount() < 1:
            return 1
        window.navigation.setCurrentRow(1)
        window.operation_combo.setCurrentIndex(1)
        window.calculate()
        if "det(A) = -2" not in window.result_view.toPlainText():
            return 1
        window.navigation.setCurrentRow(2)
        window.operation_combo.setCurrentIndex(1)
        window.editor_a.set_values([["5"]])
        window.calculate()
        if "1/5" not in window.result_view.toPlainText():
            return 1
        window.navigation.setCurrentRow(4)
        window.editor_a.set_values([["2", "1"], ["1", "-1"]])
        window.editor_b.set_values([["5"], ["1"]])
        window.calculate()
        if "x1 = 2" not in window.result_view.toPlainText() or "x2 = 1" not in window.result_view.toPlainText():
            return 1
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "smoke-test.pdf"
            write_pdf_report(str(pdf_path), window.result_view.toPlainText(), window.steps_view.toPlainText())
            if not pdf_path.is_file() or pdf_path.read_bytes()[:5] != b"%PDF-":
                return 1
        window.close()
        return 0
    # Muestra la ventana y cede el control al ciclo de eventos de Qt.
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
