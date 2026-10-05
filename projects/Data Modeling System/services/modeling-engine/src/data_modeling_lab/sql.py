from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError
from sqlglot.optimizer.scope import traverse_scope
from sqlglot.tokens import TokenType


class LabError(ValueError):
    def __init__(self, message: str, code: str = "invalid_request", status_code: int = 422):
        self.code = code
        self.status_code = status_code
        super().__init__(message)


SAFE_FUNCTIONS = {
    "ABS", "AVG", "CAST", "TRY_CAST", "COALESCE", "COUNT", "SUM", "MIN", "MAX",
    "ROUND", "UPPER", "LOWER", "TRIM", "LTRIM", "RTRIM", "ROW_NUMBER", "RANK",
    "DENSE_RANK", "FIRST_VALUE", "LAST_VALUE", "LAG", "LEAD", "NULLIF", "IF",
    "IFNULL", "DATE_TRUNC", "TIMESTAMP_TRUNC", "TIME_TO_STR", "STRFTIME", "EXTRACT",
    "CONCAT", "CONCAT_WS", "SUBSTRING", "LENGTH", "REPLACE", "GREATEST", "LEAST",
    "BOOL_AND", "BOOL_OR", "FLOOR", "CEIL", "ARRAY_AGG", "GROUP_CONCAT", "CASE",
    "TS_OR_DS_TO_DATE", "DATE", "STR_TO_TIME", "TIME_STR_TO_TIME", "DIV", "INT_DIV",
}


def inspect_query(sql: str, available_tables: set[str]) -> tuple[str, list[str], exp.Expression]:
    try:
        return _inspect_query(sql, available_tables)
    except (RecursionError, TokenError) as exc:
        raise LabError("SQL is too deeply nested or cannot be tokenized. Simplify the query.", "sql_complexity") from exc


def _inspect_query(sql: str, available_tables: set[str]) -> tuple[str, list[str], exp.Expression]:
    if not sql.strip() or len(sql) > 10000:
        raise LabError("Provide one query of at most 10,000 characters.", "sql_scope")
    tokens = sqlglot.tokenize(sql, read="duckdb")
    if len(tokens) > 2000:
        raise LabError("This fixture lab supports at most 2,000 SQL tokens.", "sql_complexity")
    depth = 0
    for token in tokens:
        if token.token_type == TokenType.L_PAREN:
            depth += 1
            if depth > 48:
                raise LabError("This fixture lab supports at most 48 levels of SQL nesting.", "sql_complexity")
        elif token.token_type == TokenType.R_PAREN:
            depth -= 1
    try:
        statements = [stmt for stmt in sqlglot.parse(sql, read="duckdb") if stmt is not None]
    except ParseError as exc:
        raise LabError(f"SQL could not be parsed: {exc}", "sql_parse") from exc
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise LabError("Use one read-only SELECT query; WITH and set operations are supported.", "sql_scope")
    tree = statements[0]
    if sum(1 for _ in tree.walk()) > 3000:
        raise LabError("This query is too complex for the small-fixture lab.", "sql_complexity")
    pending = [(tree, 0)]
    while pending:
        node, node_depth = pending.pop()
        if node_depth > 48:
            raise LabError("SQL expression depth exceeds this small-fixture lab's limit.", "sql_complexity")
        pending.extend((child, node_depth + 1) for child in node.iter_expressions())
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command, exp.Into)
    if any(isinstance(node, forbidden) for node in tree.walk()):
        raise LabError("Only read-only transformations are allowed.", "sql_scope")
    for function in tree.find_all(exp.Func):
        name = function.name.upper() if isinstance(function, exp.Anonymous) else function.sql_name()
        if name not in SAFE_FUNCTIONS:
            raise LabError(f"Function {name} is outside this deterministic fixture lab.", "sql_function")
    parents: set[str] = set()
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if not isinstance(source, exp.Table):
                continue  # A CTE or a derived query; inspect its own scope separately.
            if not isinstance(source.this, exp.Identifier) or source.catalog or source.db:
                raise LabError("External tables and table functions are not allowed.", "sql_scope")
            name = source.name.lower()
            if name not in available_tables:
                raise LabError(f"Unknown fixture/model table: {source.name}.", "sql_table")
            parents.add(name)
    return tree.sql(dialect="duckdb"), sorted(parents), tree
