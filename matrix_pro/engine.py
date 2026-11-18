"""Núcleo matemático de MATRIX PRO. Mantiene fracciones exactas siempre que es posible."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Iterable, Sequence

Number = Fraction
Matrix = list[list[Number]]
FloatMatrix = list[list[float]]
EPSILON = 1e-10


# Tipos de error y estructura común para presentar el resultado de un cálculo.
class MatrixError(ValueError):
    """Error de entrada o de aplicación matemática."""


@dataclass
class Calculation:
    summary: str
    steps: list[str]
    matrix: Matrix | None = None


# Conversión de entradas y validación de dimensiones para mantener cálculos exactos.
def parse_number(value: str | int | float | Fraction) -> Number:
    """Convierte enteros, decimales y cadenas como '-2/3' a Fraction."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MatrixError("Todos los valores deben ser números finitos.")
        return Fraction(str(value))
    try:
        return Fraction(str(value).strip())
    except (ValueError, ZeroDivisionError) as error:
        raise MatrixError(f"Valor numérico no válido: {value!r}.") from error


def format_number(value: Number | float) -> str:
    if isinstance(value, Fraction):
        return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    if not math.isfinite(value):
        return str(value)
    if abs(value) < EPSILON:
        value = 0.0
    return f"{value:.10g}"


def validate_matrix(matrix: Sequence[Sequence[Number]]) -> tuple[int, int]:
    if not matrix or not matrix[0]:
        raise MatrixError("La matriz debe tener al menos una fila y una columna.")
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise MatrixError("La matriz debe ser rectangular.")
    return len(matrix), width


def as_matrix(values: Iterable[Iterable[str | int | float | Fraction]]) -> Matrix:
    result = [[parse_number(value) for value in row] for row in values]
    validate_matrix(result)
    return result


# Operaciones elementales entre matrices y utilidades de formato.
def identity(size: int) -> Matrix:
    if size < 1:
        raise MatrixError("La dimensión debe ser positiva.")
    return [[Fraction(int(row == col)) for col in range(size)] for row in range(size)]


def transpose(matrix: Matrix) -> Matrix:
    rows, cols = validate_matrix(matrix)
    return [[matrix[row][col] for row in range(rows)] for col in range(cols)]


def add(a: Matrix, b: Matrix) -> Matrix:
    rows, cols = validate_matrix(a)
    if validate_matrix(b) != (rows, cols):
        raise MatrixError("La suma requiere matrices de las mismas dimensiones.")
    return [[a[i][j] + b[i][j] for j in range(cols)] for i in range(rows)]


def subtract(a: Matrix, b: Matrix) -> Matrix:
    rows, cols = validate_matrix(a)
    if validate_matrix(b) != (rows, cols):
        raise MatrixError("La resta requiere matrices de las mismas dimensiones.")
    return [[a[i][j] - b[i][j] for j in range(cols)] for i in range(rows)]


def multiply(a: Matrix, b: Matrix) -> Matrix:
    rows, inner = validate_matrix(a)
    other_rows, cols = validate_matrix(b)
    if inner != other_rows:
        raise MatrixError("Para multiplicar, columnas(A) debe ser igual a filas(B).")
    return [
        [sum((a[i][k] * b[k][j] for k in range(inner)), Fraction(0)) for j in range(cols)]
        for i in range(rows)
    ]


def scale(matrix: Matrix, scalar: Number) -> Matrix:
    validate_matrix(matrix)
    return [[value * scalar for value in row] for row in matrix]


def power(matrix: Matrix, exponent: int) -> Matrix:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("Las potencias requieren una matriz cuadrada.")
    if exponent < 0:
        matrix = inverse(matrix, [])
        exponent = -exponent
    result = identity(rows)
    base = matrix
    while exponent:
        if exponent & 1:
            result = multiply(result, base)
        exponent >>= 1
        if exponent:
            base = multiply(base, base)
    return result


# Determinantes por expansión de Laplace, eliminación de Gauss y regla de Sarrus.
def minor_matrix(matrix: Matrix, skip_row: int, skip_col: int) -> Matrix:
    return [
        [value for col, value in enumerate(row) if col != skip_col]
        for index, row in enumerate(matrix)
        if index != skip_row
    ]


def determinant_laplace(matrix: Matrix, steps: list[str], indent: str = "") -> Number:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("El determinante requiere una matriz cuadrada.")
    if rows == 1:
        return matrix[0][0]
    if rows == 2:
        value = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        steps.append(
            f"{indent}det = {format_number(matrix[0][0])}·{format_number(matrix[1][1])} "
            f"- {format_number(matrix[0][1])}·{format_number(matrix[1][0])} = {format_number(value)}"
        )
        return value

    terms: list[str] = []
    result = Fraction(0)
    for col in range(cols):
        minor = minor_matrix(matrix, 0, col)
        minor_steps: list[str] = []
        minor_det = determinant_laplace(minor, minor_steps, indent + "  ")
        sign = Fraction(1 if col % 2 == 0 else -1)
        cofactor = sign * minor_det
        term = matrix[0][col] * cofactor
        result += term
        steps.append(
            f"{indent}Menor M(1,{col + 1}):\n{format_matrix(minor)}"
        )
        steps.append(
            f"{indent}C(1,{col + 1}) = (-1)^{col + 2}·det(M) "
            f"= {format_number(sign)}·{format_number(minor_det)} = {format_number(cofactor)}"
        )
        steps.extend(minor_steps)
        terms.append(f"({format_number(matrix[0][col])})·({format_number(cofactor)})")
    steps.append(f"{indent}Desarrollo por la fila 1: {' + '.join(terms)} = {format_number(result)}")
    return result


def determinant_gauss(matrix: Matrix, steps: list[str]) -> Number:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("El determinante requiere una matriz cuadrada.")
    work = [row[:] for row in matrix]
    determinant = Fraction(1)
    sign = 1
    for col in range(cols):
        pivot = next((row for row in range(col, rows) if work[row][col] != 0), None)
        if pivot is None:
            steps.append(f"Pivote nulo en la columna {col + 1}; det(A) = 0.")
            return Fraction(0)
        if pivot != col:
            work[pivot], work[col] = work[col], work[pivot]
            sign *= -1
            steps.append(f"F{pivot + 1} ↔ F{col + 1}; el intercambio cambia el signo.")
        pivot_value = work[col][col]
        determinant *= pivot_value
        steps.append(f"Pivote a({col + 1},{col + 1}) = {format_number(pivot_value)}.")
        for row in range(col + 1, rows):
            factor = work[row][col] / pivot_value
            for j in range(col, cols):
                work[row][j] -= factor * work[col][j]
            steps.append(f"F{row + 1} ← F{row + 1} - ({format_number(factor)})F{col + 1}.")
        steps.append("Matriz tras eliminación:\n" + format_matrix(work))
    determinant *= sign
    steps.append(f"Producto diagonal con signo de permutaciones = {format_number(determinant)}.")
    return determinant


def determinant_sarrus(matrix: Matrix, steps: list[str]) -> Number:
    if validate_matrix(matrix) != (3, 3):
        raise MatrixError("La regla de Sarrus solo aplica a matrices 3×3.")
    positive = sum(
        (matrix[0][0] * matrix[1][1] * matrix[2][2],
         matrix[0][1] * matrix[1][2] * matrix[2][0],
         matrix[0][2] * matrix[1][0] * matrix[2][1]),
        Fraction(0),
    )
    negative = sum(
        (matrix[0][2] * matrix[1][1] * matrix[2][0],
         matrix[0][0] * matrix[1][2] * matrix[2][1],
         matrix[0][1] * matrix[1][0] * matrix[2][2]),
        Fraction(0),
    )
    result = positive - negative
    steps.extend([
        f"Diagonales descendentes: {format_number(positive)}.",
        f"Diagonales ascendentes: {format_number(negative)}.",
        f"det(A) = {format_number(positive)} - ({format_number(negative)}) = {format_number(result)}.",
    ])
    return result


def format_matrix(matrix: Sequence[Sequence[Number | float]]) -> str:
    if not matrix:
        return "(matriz vacía)"
    rendered = [[format_number(value) for value in row] for row in matrix]
    widths = [max(len(row[col]) for row in rendered) for col in range(len(rendered[0]))]
    return "\n".join("| " + "  ".join(value.rjust(widths[col]) for col, value in enumerate(row)) + " |"
                    for row in rendered)


# Inversa por Gauss–Jordan y forma escalonada reducida compartida por otros cálculos.
def inverse(matrix: Matrix, steps: list[str]) -> Matrix:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("La inversa requiere una matriz cuadrada.")
    left = [row[:] for row in matrix]
    right = identity(rows)
    steps.append("Iniciar la matriz aumentada [A | I].")
    for col in range(cols):
        pivot = next((row for row in range(col, rows) if left[row][col] != 0), None)
        if pivot is None:
            raise MatrixError("La matriz es singular: no tiene inversa.")
        if pivot != col:
            left[pivot], left[col] = left[col], left[pivot]
            right[pivot], right[col] = right[col], right[pivot]
            steps.append(f"F{pivot + 1} ↔ F{col + 1}.")
        divisor = left[col][col]
        left[col] = [value / divisor for value in left[col]]
        right[col] = [value / divisor for value in right[col]]
        steps.append(f"F{col + 1} ← F{col + 1} / ({format_number(divisor)}).")
        for row in range(rows):
            if row == col:
                continue
            factor = left[row][col]
            if factor == 0:
                continue
            left[row] = [left[row][j] - factor * left[col][j] for j in range(cols)]
            right[row] = [right[row][j] - factor * right[col][j] for j in range(cols)]
            steps.append(f"F{row + 1} ← F{row + 1} - ({format_number(factor)})F{col + 1}.")
        steps.append("Estado de [A | I]:\n" + format_matrix(left) + "\n—\n" + format_matrix(right))
    return right


@dataclass
class Rref:
    matrix: Matrix
    pivots: list[int]


# Resolución de sistemas lineales y construcción de una base del núcleo.
def rref(matrix: Matrix, steps: list[str], pivot_columns: int | None = None) -> Rref:
    rows, cols = validate_matrix(matrix)
    limit = cols if pivot_columns is None else min(cols, pivot_columns)
    work = [row[:] for row in matrix]
    pivots: list[int] = []
    pivot_row = 0
    for col in range(limit):
        if pivot_row >= rows:
            break
        pivot = next((row for row in range(pivot_row, rows) if work[row][col] != 0), None)
        if pivot is None:
            continue
        if pivot != pivot_row:
            work[pivot], work[pivot_row] = work[pivot_row], work[pivot]
            steps.append(f"F{pivot + 1} ↔ F{pivot_row + 1}.")
        divisor = work[pivot_row][col]
        work[pivot_row] = [value / divisor for value in work[pivot_row]]
        steps.append(f"F{pivot_row + 1} ← F{pivot_row + 1} / ({format_number(divisor)}).")
        for row in range(rows):
            if row == pivot_row:
                continue
            factor = work[row][col]
            if factor == 0:
                continue
            work[row] = [work[row][j] - factor * work[pivot_row][j] for j in range(cols)]
            steps.append(f"F{row + 1} ← F{row + 1} - ({format_number(factor)})F{pivot_row + 1}.")
        pivots.append(col)
        steps.append("Estado de la matriz:\n" + format_matrix(work))
        pivot_row += 1
    return Rref(work, pivots)


def solve_system(coefficients: Matrix, constants: Matrix, steps: list[str]) -> tuple[str, str]:
    rows, variables = validate_matrix(coefficients)
    if validate_matrix(constants) != (rows, 1):
        raise MatrixError("El vector b debe tener una columna y tantas filas como A.")
    augmented = [coefficients[i][:] + constants[i][:] for i in range(rows)]
    steps.append("Matriz aumentada inicial [A | b]:\n" + format_matrix(augmented))
    reduced = rref(augmented, steps, variables)
    inconsistent = any(
        all(value == 0 for value in reduced.matrix[row][:variables])
        and reduced.matrix[row][variables] != 0
        for row in range(rows)
    )
    if inconsistent:
        return "Sistema incompatible: no tiene solución.", ""
    free = [col for col in range(variables) if col not in reduced.pivots]
    if not free:
        solution = [Fraction(0) for _ in range(variables)]
        for row, pivot in enumerate(reduced.pivots):
            solution[pivot] = reduced.matrix[row][variables]
        details = "\n".join(f"x{i + 1} = {format_number(value)}" for i, value in enumerate(solution))
        return "Sistema compatible determinado.", details
    lines = ["Sistema compatible indeterminado."]
    lines.append("Variables libres: " + ", ".join(f"x{i + 1}" for i in free))
    for row, pivot in enumerate(reduced.pivots):
        expression = format_number(reduced.matrix[row][variables])
        for col in free:
            coefficient = -reduced.matrix[row][col]
            if coefficient:
                expression += f" + ({format_number(coefficient)})·x{col + 1}"
        lines.append(f"x{pivot + 1} = {expression}")
    return "Sistema compatible indeterminado.", "\n".join(lines)


def nullspace_basis(reduced: Rref, columns: int) -> list[list[Number]]:
    basis: list[list[Number]] = []
    for free_col in range(columns):
        if free_col in reduced.pivots:
            continue
        vector = [Fraction(0) for _ in range(columns)]
        vector[free_col] = Fraction(1)
        for row, pivot in enumerate(reduced.pivots):
            vector[pivot] = -reduced.matrix[row][free_col]
        basis.append(vector)
    return basis


# Clasificación de propiedades, dimensiones, diagonales y determinante de una matriz.
def analyze(matrix: Matrix) -> tuple[str, list[str]]:
    rows, cols = validate_matrix(matrix)
    values = [value for row in matrix for value in row]
    lines = [
        f"Dimensiones: {rows} × {cols}",
        f"Suma total: {format_number(sum(values, Fraction(0)))}",
        f"Mínimo: {format_number(min(values))}",
        f"Máximo: {format_number(max(values))}",
    ]
    steps: list[str] = []
    if rows != cols:
        lines.append("No es cuadrada; clasificación limitada a propiedades rectangulares.")
        lines.append("Diagonal principal: " + ", ".join(format_number(matrix[i][i]) for i in range(min(rows, cols))))
        lines.append("Diagonal secundaria: " + ", ".join(
            format_number(matrix[i][cols - 1 - i]) for i in range(min(rows, cols))
        ))
        return "\n".join(lines), steps

    size = rows
    trace = sum((matrix[i][i] for i in range(size)), Fraction(0))
    diagonal = all(matrix[i][j] == 0 for i in range(size) for j in range(size) if i != j)
    scalar = diagonal and len({matrix[i][i] for i in range(size)}) <= 1
    identity_matrix = all(matrix[i][j] == Fraction(int(i == j)) for i in range(size) for j in range(size))
    symmetric = matrix == transpose(matrix)
    skew = all(matrix[i][j] == -matrix[j][i] for i in range(size) for j in range(size))
    upper = all(matrix[i][j] == 0 for i in range(size) for j in range(i))
    lower = all(matrix[i][j] == 0 for i in range(size) for j in range(i + 1, size))
    square_matrix = multiply(matrix, matrix)
    idempotent = square_matrix == matrix
    orthogonal = multiply(transpose(matrix), matrix) == identity(size)
    nilpotent = False
    current = matrix
    for _ in range(size):
        if all(value == 0 for row in current for value in row):
            nilpotent = True
            break
        current = multiply(current, matrix)
    det = determinant_gauss(matrix, steps)
    lines.extend([
        f"Traza: {format_number(trace)}",
        f"Suma diagonal principal: {format_number(trace)}",
        "Suma diagonal secundaria: " + format_number(sum(
            (matrix[i][size - 1 - i] for i in range(size)), Fraction(0)
        )),
        f"Nula: {'sí' if all(value == 0 for value in values) else 'no'}",
        f"Identidad: {'sí' if identity_matrix else 'no'}",
        f"Diagonal: {'sí' if diagonal else 'no'}",
        f"Escalar: {'sí' if scalar else 'no'}",
        f"Simétrica: {'sí' if symmetric else 'no'}",
        f"Antisimétrica: {'sí' if skew else 'no'}",
        f"Triangular superior: {'sí' if upper else 'no'}",
        f"Triangular inferior: {'sí' if lower else 'no'}",
        f"Ortogonal: {'sí' if orthogonal else 'no'}",
        f"Idempotente: {'sí' if idempotent else 'no'}",
        f"Nilpotente: {'sí' if nilpotent else 'no'}",
        f"Determinante: {format_number(det)}",
        f"Singular: {'sí' if det == 0 else 'no'}",
        f"Invertible: {'no' if det == 0 else 'sí'}",
    ])
    return "\n".join(lines), steps


# Descomposiciones LU, QR y Cholesky con registro de sus pasos.
def lu_decomposition(matrix: Matrix, steps: list[str]) -> tuple[Matrix, Matrix, list[int]]:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("La descomposición LU requiere una matriz cuadrada.")
    size = rows
    upper = [row[:] for row in matrix]
    lower = identity(size)
    permutation = list(range(size))
    for col in range(size):
        pivot = next((row for row in range(col, size) if upper[row][col] != 0), None)
        if pivot is None:
            raise MatrixError("LU requiere pivote no nulo; la matriz es singular.")
        if pivot != col:
            upper[pivot], upper[col] = upper[col], upper[pivot]
            permutation[pivot], permutation[col] = permutation[col], permutation[pivot]
            for j in range(col):
                lower[pivot][j], lower[col][j] = lower[col][j], lower[pivot][j]
            steps.append(f"Intercambiar filas {pivot + 1} y {col + 1}.")
        for row in range(col + 1, size):
            lower[row][col] = upper[row][col] / upper[col][col]
            for j in range(col, size):
                upper[row][j] -= lower[row][col] * upper[col][j]
            steps.append(f"L({row + 1},{col + 1}) = {format_number(lower[row][col])}; eliminar debajo.")
    return lower, upper, permutation


def qr_decomposition(matrix: Matrix, steps: list[str]) -> tuple[FloatMatrix, FloatMatrix]:
    rows, cols = validate_matrix(matrix)
    if rows < cols:
        raise MatrixError("QR reducido por Gram–Schmidt requiere filas ≥ columnas.")
    q = [[0.0 for _ in range(cols)] for _ in range(rows)]
    r = [[0.0 for _ in range(cols)] for _ in range(cols)]
    for col in range(cols):
        vector = [float(matrix[row][col]) for row in range(rows)]
        for previous in range(col):
            dot = sum(q[row][previous] * vector[row] for row in range(rows))
            r[previous][col] = dot
            vector = [vector[row] - dot * q[row][previous] for row in range(rows)]
            steps.append(f"Proyección columna {col + 1} sobre q{previous + 1}: {format_number(dot)}.")
        norm = math.sqrt(sum(value * value for value in vector))
        if norm <= EPSILON:
            raise MatrixError("Las columnas son dependientes; QR reducido no es único.")
        r[col][col] = norm
        for row in range(rows):
            q[row][col] = vector[row] / norm
        steps.append(f"Normalizar columna {col + 1}; norma = {format_number(norm)}.")
    return q, r


def cholesky(matrix: Matrix, steps: list[str]) -> FloatMatrix:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("Cholesky requiere una matriz cuadrada.")
    if any(abs(float(matrix[i][j] - matrix[j][i])) > EPSILON for i in range(rows) for j in range(rows)):
        raise MatrixError("Cholesky requiere una matriz simétrica.")
    lower = [[0.0 for _ in range(rows)] for _ in range(rows)]
    for i in range(rows):
        for j in range(i + 1):
            value = float(matrix[i][j]) - sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                if value <= EPSILON:
                    raise MatrixError("La matriz debe ser definida positiva para aplicar Cholesky.")
                lower[i][j] = math.sqrt(value)
                steps.append(f"L({i + 1},{j + 1}) = √({format_number(value)}) = {format_number(lower[i][j])}.")
            else:
                lower[i][j] = value / lower[j][j]
                steps.append(f"L({i + 1},{j + 1}) = {format_number(lower[i][j])}.")
    return lower


# Cálculo aproximado de valores/vectores propios y valores singulares.
def symmetric_eigen(matrix: Matrix, steps: list[str]) -> tuple[list[float], FloatMatrix]:
    rows, cols = validate_matrix(matrix)
    if rows != cols:
        raise MatrixError("Los valores propios requieren una matriz cuadrada.")
    if any(abs(float(matrix[i][j] - matrix[j][i])) > EPSILON for i in range(rows) for j in range(rows)):
        raise MatrixError("Esta implementación de valores propios requiere una matriz simétrica.")
    work = [[float(value) for value in row] for row in matrix]
    vectors = [[float(i == j) for j in range(rows)] for i in range(rows)]
    scale_value = max((abs(value) for row in work for value in row), default=0.0)
    tolerance = EPSILON * max(1.0, scale_value)
    for _ in range(max(1, 50 * rows * rows)):
        p, q, largest = 0, 0, 0.0
        for i in range(rows):
            for j in range(i + 1, rows):
                if abs(work[i][j]) > largest:
                    p, q, largest = i, j, abs(work[i][j])
        if largest <= tolerance:
            break
        angle = 0.5 * math.atan2(2 * work[p][q], work[q][q] - work[p][p])
        c, s = math.cos(angle), math.sin(angle)
        app, aqq, apq = work[p][p], work[q][q], work[p][q]
        work[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        work[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
        work[p][q] = work[q][p] = 0.0
        for k in range(rows):
            if k not in (p, q):
                akp, akq = work[k][p], work[k][q]
                work[k][p] = work[p][k] = c * akp - s * akq
                work[k][q] = work[q][k] = s * akp + c * akq
            vkp, vkq = vectors[k][p], vectors[k][q]
            vectors[k][p] = c * vkp - s * vkq
            vectors[k][q] = s * vkp + c * vkq
    eigenvalues = [work[i][i] for i in range(rows)]
    order = sorted(range(rows), key=lambda i: eigenvalues[i], reverse=True)
    steps.append("Se aplicaron rotaciones de Jacobi hasta anular los términos fuera de la diagonal.")
    return [eigenvalues[i] for i in order], [[vectors[row][i] for i in order] for row in range(rows)]


def singular_values(matrix: Matrix, steps: list[str]) -> list[float]:
    rows, cols = validate_matrix(matrix)
    ata = multiply(transpose(matrix), matrix)
    eigenvalues, _ = symmetric_eigen(ata, steps)
    steps.append("Se obtienen los valores singulares como √λ de AᵀA; aproximación en aritmética flotante.")
    return [math.sqrt(max(0.0, value)) for value in eigenvalues[: min(rows, cols)]]
