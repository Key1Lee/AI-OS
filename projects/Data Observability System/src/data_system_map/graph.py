from __future__ import annotations

from collections import deque

from data_system_map.contracts import GraphSnapshot


class Graph:
    """Declared data dependencies. Test associations never imply data flow."""

    def __init__(self, snapshot: GraphSnapshot):
        self.snapshot = snapshot
        self.nodes = {node.id: node for node in snapshot.nodes}
        self.parents = {key: set() for key in self.nodes}
        self.children = {key: set() for key in self.nodes}
        for edge in snapshot.edges:
            if edge.relationship_type == "depends_on":
                self.parents[edge.to_node].add(edge.from_node)
                self.children[edge.from_node].add(edge.to_node)

    def get_node(self, key: str):
        return self.nodes[key]

    def direct_parents(self, key: str) -> list[str]:
        return sorted(self.parents[key])

    def direct_children(self, key: str) -> list[str]:
        return sorted(self.children[key])

    def _walk(self, key: str, adjacency: dict[str, set[str]]) -> list[str]:
        self.get_node(key)
        seen, queue = {key}, deque(sorted(adjacency[key]))
        while queue:
            current = queue.popleft()
            if current not in seen:
                seen.add(current)
                queue.extend(sorted(adjacency[current] - seen))
        return sorted(seen - {key})

    def upstream(self, key: str) -> list[str]:
        return self._walk(key, self.parents)

    def downstream(self, key: str) -> list[str]:
        return self._walk(key, self.children)

    def impact(self, key: str) -> dict:
        direct, all_nodes = self.direct_children(key), self.downstream(key)
        return {"direct": direct, "transitive": sorted(set(all_nodes) - set(direct)),
                "affected_outputs": [n for n in all_nodes if self.nodes[n].node_type in {"output", "metric"}]}

    def shortest_path(self, start: str, end: str) -> list[str] | None:
        self.get_node(start)
        self.get_node(end)
        queue, seen = deque([[start]]), {start}
        while queue:
            path = queue.popleft()
            if path[-1] == end:
                return path
            for child in self.direct_children(path[-1]):
                if child not in seen:
                    seen.add(child)
                    queue.append([*path, child])
        return None

    def all_paths(self, start: str, end: str, limit: int = 32, max_depth: int = 64) -> dict:
        self.get_node(start)
        self.get_node(end)
        if not 1 <= limit <= 100 or not 1 <= max_depth <= 100:
            raise ValueError("Path query limits are out of range")
        found, stack, truncated, expanded = [], [[start]], False, 0
        while stack:
            path = stack.pop()
            expanded += 1
            if expanded > 10000:
                truncated = True
                break
            if path[-1] == end:
                found.append(path)
                if len(found) > limit:
                    truncated = True
                    break
                continue
            next_nodes = [n for n in self.direct_children(path[-1]) if n not in path]
            if len(path) >= max_depth and next_nodes:
                truncated = True
                continue
            stack.extend([*path, node] for node in reversed(next_nodes))
        return {"paths": found[:limit], "truncated": truncated}

    def cycles(self) -> list[list[str]]:
        color, found = {}, []
        for root in sorted(self.nodes):
            if color.get(root):
                continue
            path, positions = [root], {root: 0}
            color[root] = 1
            stack = [(root, iter(self.direct_children(root)))]
            while stack:
                node, children = stack[-1]
                child = next(children, None)
                if child is None:
                    stack.pop()
                    color[node] = 2
                    positions.pop(node)
                    path.pop()
                elif color.get(child) == 1:
                    found.append([*path[positions[child]:], child])
                    if len(found) >= 20:
                        return found
                elif not color.get(child):
                    color[child] = 1
                    positions[child] = len(path)
                    path.append(child)
                    stack.append((child, iter(self.direct_children(child))))
        return found

    def failed_path(self, failure: str) -> dict:
        self.get_node(failure)
        relevant = set([failure, *self.upstream(failure), *self.downstream(failure)])
        return {"observed_failure": failure, "node_ids": sorted(relevant),
                "edges": [edge.model_dump() for edge in self.snapshot.edges
                          if edge.relationship_type == "depends_on" and edge.from_node in relevant and edge.to_node in relevant],
                "impact": self.impact(failure)}

    def column_lineage(self, key: str, column: str) -> dict:
        node = self.get_node(key)
        if not any(item.name == column for item in node.columns):
            raise KeyError(column)
        return {"status": "unavailable", "message": "Lineage unavailable. Column relationships have not been established by this adapter.", "paths": []}
