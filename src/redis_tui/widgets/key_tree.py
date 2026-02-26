from __future__ import annotations
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.message import Message
from redis_tui.models.key_info import KeyInfo, KeyType, TreeNodeData


class RedisKeyTree(Tree):
    """Tree widget for browsing Redis keys with lazy loading."""

    BORDER_TITLE = "Keys"

    BINDINGS = [("space", "toggle_select", "Select")]

    class KeySelected(Message):
        def __init__(self, key_name: str) -> None:
            super().__init__()
            self.key_name = key_name

    class FolderExpanded(Message):
        def __init__(self, prefix: str, node: TreeNode) -> None:
            super().__init__()
            self.prefix = prefix
            self.node = node

    class SelectionChanged(Message):
        def __init__(self, selected_keys: set[str]) -> None:
            super().__init__()
            self.selected_keys = selected_keys

    def __init__(self, *args, **kwargs):
        super().__init__("Redis", *args, **kwargs)
        self._loading_nodes: set = set()
        self._selected_keys: set[str] = set()
        self._node_by_key: dict[str, TreeNode] = {}

    def populate(self, keys: list[str], separator: str = ":") -> None:
        """Populate tree from a flat list of keys."""
        self._node_by_key.clear()
        self._selected_keys.clear()
        self.clear()
        root = self.root
        root.expand()

        # Group keys by first segment
        folders: dict[str, list[str]] = {}
        leaves: list[str] = []

        for key in sorted(keys):
            parts = key.split(separator, 1)
            if len(parts) == 1:
                leaves.append(key)
            else:
                prefix = parts[0]
                folders.setdefault(prefix, []).append(key)

        # Add folders first
        for prefix in sorted(folders.keys()):
            folder_node = root.add(
                f"[+] {prefix}",
                data=TreeNodeData(is_leaf=False, prefix=prefix),
                expand=False,
            )
            # Add placeholder child to make it expandable
            folder_node.add_leaf(
                "...",
                data=TreeNodeData(is_leaf=False, prefix="__loading__"),
            )

        # Add direct leaves
        for key in sorted(leaves):
            leaf_node = root.add_leaf(
                key,
                data=TreeNodeData(is_leaf=True, key_name=key),
            )
            self._node_by_key[key] = leaf_node

    def populate_folder(
        self,
        folder_node: TreeNode,
        keys: list[str],
        prefix: str,
        separator: str = ":",
    ) -> None:
        """Populate a folder node with its children."""
        # Remove loading placeholder
        for child in list(folder_node.children):
            child.remove()

        prefix_with_sep = f"{prefix}{separator}"
        subfolders: dict[str, list[str]] = {}
        leaves: list[str] = []

        for key in sorted(keys):
            if not key.startswith(prefix_with_sep):
                continue
            remainder = key[len(prefix_with_sep):]
            parts = remainder.split(separator, 1)
            if len(parts) == 1:
                leaves.append(key)
            else:
                sub_prefix = parts[0]
                subfolders.setdefault(sub_prefix, []).append(key)

        for sub_prefix in sorted(subfolders.keys()):
            full_prefix = f"{prefix}{separator}{sub_prefix}"
            sub_node = folder_node.add(
                f"[+] {sub_prefix}",
                data=TreeNodeData(is_leaf=False, prefix=full_prefix),
                expand=False,
            )
            sub_node.add_leaf(
                "...",
                data=TreeNodeData(is_leaf=False, prefix="__loading__"),
            )

        for key in sorted(leaves):
            label = self._format_leaf_label(key, prefix, separator)
            leaf_node = folder_node.add_leaf(
                label,
                data=TreeNodeData(is_leaf=True, key_name=key),
            )
            self._node_by_key[key] = leaf_node

    def _format_leaf_label(self, key: str, prefix: str, separator: str) -> str:
        """Format a leaf label, stripping the parent prefix."""
        prefix_with_sep = f"{prefix}{separator}"
        if key.startswith(prefix_with_sep):
            return key[len(prefix_with_sep):]
        return key

    def update_key_type(self, key_name: str, key_type: KeyType) -> None:
        """Update a leaf node label to show key type icon."""
        pass  # Can be implemented for visual type indicators

    # --- Selection ---

    def action_toggle_select(self) -> None:
        """Toggle selection of the currently focused leaf node."""
        cursor_node = self.cursor_node
        if cursor_node is None:
            return
        node_data: TreeNodeData | None = cursor_node.data
        if node_data and node_data.is_leaf and node_data.key_name:
            self.toggle_selection(node_data.key_name)

    def toggle_selection(self, key_name: str) -> None:
        """Add or remove a key from the selection, updating its label."""
        if key_name in self._selected_keys:
            self._selected_keys.discard(key_name)
        else:
            self._selected_keys.add(key_name)

        node = self._node_by_key.get(key_name)
        if node is not None:
            if key_name in self._selected_keys:
                # Show checkmark prefix — use short label only
                parts = key_name.rsplit(":", 1)
                short = parts[-1] if len(parts) > 1 else key_name
                node.set_label(f"[+] {short}")
            else:
                # Restore original short label
                parts = key_name.rsplit(":", 1)
                node.set_label(parts[-1] if len(parts) > 1 else key_name)

        self.post_message(self.SelectionChanged(self._selected_keys.copy()))

    def clear_selection(self) -> None:
        """Clear all selected keys and restore their labels."""
        keys_to_clear = self._selected_keys.copy()
        self._selected_keys.clear()
        for key_name in keys_to_clear:
            node = self._node_by_key.get(key_name)
            if node is not None:
                parts = key_name.rsplit(":", 1)
                node.set_label(parts[-1] if len(parts) > 1 else key_name)
        self.post_message(self.SelectionChanged(set()))

    def get_selected_keys(self) -> set[str]:
        """Return a copy of the currently selected key names."""
        return self._selected_keys.copy()

    def has_selection(self) -> bool:
        """Return True if at least one key is selected."""
        return len(self._selected_keys) > 0

    # --- Tree events ---

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        event.stop()
        node_data: TreeNodeData | None = event.node.data
        if node_data and node_data.is_leaf and node_data.key_name:
            self.post_message(self.KeySelected(node_data.key_name))

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        event.stop()
        node_data: TreeNodeData | None = event.node.data
        if node_data and not node_data.is_leaf and node_data.prefix:
            if node_data.prefix != "__loading__":
                self.post_message(self.FolderExpanded(node_data.prefix, event.node))
