import math
from typing import Iterable, List

from digital_twin.core.entities import Vector3


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def magnitude(vector: Vector3) -> float:
    return math.sqrt(vector.x * vector.x + vector.y * vector.y + vector.z * vector.z)


def normalize(vector: Vector3) -> Vector3:
    length = magnitude(vector)
    if length <= 1e-9:
        return Vector3(0.0, 0.0, 0.0)
    return Vector3(vector.x / length, vector.y / length, vector.z / length)


def subtract(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(a.x - b.x, a.y - b.y, a.z - b.z)


def dot(a: Vector3, b: Vector3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def distance(a: Vector3, b: Vector3) -> float:
    return magnitude(subtract(a, b))


def spaced_values(max_value: float, count: int) -> List[float]:
    if count <= 1:
        return [max_value / 2.0]
    step = max_value / float(count - 1)
    return [index * step for index in range(count)]


def mean(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / float(len(items))


def solve_linear_system(matrix: List[List[float]], vector: List[float]) -> List[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]

    for pivot_index in range(size):
        pivot_row = max(range(pivot_index, size), key=lambda row_index: abs(augmented[row_index][pivot_index]))
        if abs(augmented[pivot_row][pivot_index]) < 1e-9:
            augmented[pivot_row][pivot_index] = 1e-9
        augmented[pivot_index], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_index]

        pivot_value = augmented[pivot_index][pivot_index]
        for column_index in range(pivot_index, size + 1):
            augmented[pivot_index][column_index] /= pivot_value

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            for column_index in range(pivot_index, size + 1):
                augmented[row_index][column_index] -= factor * augmented[pivot_index][column_index]

    return [augmented[row_index][size] for row_index in range(size)]
