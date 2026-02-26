from __future__ import annotations
from collections import defaultdict


class TreeNode:
    """Represents a node in the key tree."""
    def __init__(self, label: str, full_path: str = "", is_leaf: bool = False):
        self.label = label
        self.full_path = full_path
        self.is_leaf = is_leaf
        self.children: dict[str, TreeNode] = {}

    def __repr__(self):
        return f"TreeNode({self.label!r}, leaf={self.is_leaf})"


class TreeBuilder:
    def __init__(self, separator: str = ":"):
        self.separator = separator

    def build(self, keys: list[str]) -> TreeNode:
        """Build a tree from a flat list of keys."""
        root = TreeNode(label="root", full_path="")
        for key in keys:
            self._insert(root, key, key)
        return root

    def _insert(self, node: TreeNode, key: str, full_key: str) -> None:
        parts = key.split(self.separator, 1)
        if len(parts) == 1:
            # Leaf node
            leaf = TreeNode(label=parts[0], full_path=full_key, is_leaf=True)
            node.children[parts[0]] = leaf
        else:
            prefix, rest = parts
            if prefix not in node.children:
                folder_path = f"{node.full_path}{self.separator}{prefix}" if node.full_path else prefix
                node.children[prefix] = TreeNode(label=prefix, full_path=folder_path, is_leaf=False)
            self._insert(node.children[prefix], rest, full_key)

    def get_immediate_children(self, keys: list[str], prefix: str = "") -> list[tuple[str, bool]]:
        """
        Given a list of keys and a prefix, return immediate children as
        list of (label, is_leaf). is_leaf=True means it's a direct key.
        """
        result: dict[str, bool] = {}
        prefix_with_sep = f"{prefix}{self.separator}" if prefix else ""
        prefix_len = len(prefix_with_sep)

        for key in keys:
            if prefix and not key.startswith(prefix_with_sep):
                continue
            remainder = key[prefix_len:]
            parts = remainder.split(self.separator, 1)
            child_label = parts[0]
            is_leaf = len(parts) == 1

            if child_label in result:
                # If we already have a folder with this name, keep it as folder
                if not is_leaf:
                    result[child_label] = False
            else:
                result[child_label] = is_leaf

        return sorted(result.items(), key=lambda x: (x[1], x[0]))  # folders first, then leaves
