from __future__ import annotations

import datetime as dt
import math
from decimal import Decimal
from numbers import Number


def scalar_equal(actual, expected, tolerance: float, temporal=False) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (Number, Decimal)) and isinstance(expected, (Number, Decimal)):
        return math.isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance)
    if temporal:
        try:
            a = actual if isinstance(actual, dt.datetime) else dt.datetime.fromisoformat(str(actual).replace("Z", "+00:00"))
            b = expected if isinstance(expected, dt.datetime) else dt.datetime.fromisoformat(str(expected).replace("Z", "+00:00"))
            return a == b
        except ValueError:
            return False
    if isinstance(actual, (dt.datetime, dt.date)):
        actual = actual.isoformat()
    if isinstance(expected, (dt.datetime, dt.date)):
        expected = expected.isoformat()
    return actual == expected


def compare(result: dict, columns: list[str], expected: list[list], *, ordered=False, tolerance=1e-6, expected_types=None) -> tuple[bool, str]:
    if not result.get("ok"):
        return False, result.get("kind", "execution")
    if result.get("columns") != columns:
        return False, "output_schema"
    if expected_types:
        integral = {"TINYINT","SMALLINT","INTEGER","BIGINT","HUGEINT","UTINYINT","USMALLINT","UINTEGER","UBIGINT","UHUGEINT"}
        def accepts(actual, required):
            if required == "NUMERIC":
                return actual in integral | {"FLOAT","DOUBLE"} or actual.startswith("DECIMAL(")
            if required == "INTEGER":
                return actual in integral
            if required == "TIMESTAMPTZ":
                return actual == "TIMESTAMP WITH TIME ZONE"
            return actual == required
        types = result.get("types",[])
        if len(types) != len(expected_types) or not all(accepts(a,e) for a,e in zip(types,expected_types)):
            return False, "output_schema"
    actual = result["rows"]
    if len(actual) != len(expected):
        return False, "row_count"

    def row_equal(left, right):
        return len(left) == len(right) and all(scalar_equal(a, b, tolerance, bool(expected_types and expected_types[i] in {"TIMESTAMP","TIMESTAMPTZ"})) for i,(a,b) in enumerate(zip(left,right)))

    if ordered:
        return (True, "matched") if all(row_equal(a, b) for a, b in zip(actual, expected)) else (False, "row_order_or_values")
    # Bipartite matching preserves multiplicity and handles overlapping float
    # tolerances where greedy matching can reject an otherwise equivalent set.
    edges = [[j for j, row in enumerate(expected) if row_equal(candidate, row)] for candidate in actual]
    matched_expected: dict[int, int] = {}
    matched_actual: dict[int, int] = {}
    for i in range(len(actual)):
        queue = [i]
        visited_actual = {i}
        parent_expected: dict[int, int] = {}
        free = None
        for candidate in queue:
            for j in edges[candidate]:
                if j in parent_expected:
                    continue
                parent_expected[j] = candidate
                if j not in matched_expected:
                    free = j
                    break
                other = matched_expected[j]
                if other not in visited_actual:
                    visited_actual.add(other)
                    queue.append(other)
            if free is not None:
                break
        if free is None:
            return False, "values_or_duplicates"
        # Iterative augmentation avoids recursion failure at the row limit.
        while free is not None:
            candidate = parent_expected[free]
            previous = matched_actual.get(candidate)
            matched_expected[free] = candidate
            matched_actual[candidate] = free
            free = previous
    return True, "matched"
