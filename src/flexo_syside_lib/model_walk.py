from __future__ import annotations

import syside


def children_iter(elem):
    children = getattr(elem, "owned_elements", None)
    if not children:
        return []
    try:
        return list(children)
    except TypeError:
        out = []
        children.for_each(lambda e: out.append(e))
        return out


def find_partusage_by_definition(
    elem,
    defining_part_name: str,
    usage_name: str | None = None,
):
    def has_matching_def(node):
        if not node.try_cast(syside.PartUsage):
            return False
        try:
            for pd in node.part_definitions:
                if getattr(pd, "name", None) == defining_part_name:
                    return True
        except Exception:
            pass
        return False

    def matches_usage_name(node):
        if usage_name is None:
            return True
        return getattr(node, "name", None) == usage_name

    def dfs(node):
        is_part = bool(node.try_cast(syside.PartUsage))
        here_matches = is_part and has_matching_def(node) and matches_usage_name(node)

        subtree_has_match = here_matches
        child_found = None

        for child in children_iter(node):
            found, child_has = dfs(child)
            subtree_has_match = subtree_has_match or child_has or (found is not None)
            if found is not None and child_found is None:
                child_found = found

        if here_matches:
            return node, True

        if child_found is not None:
            return child_found, True

        return None, subtree_has_match

    found, _ = dfs(elem)
    return found


def find_component_partusage(elem):
    def is_component_partusage(node) -> bool:
        pu = node.try_cast(syside.PartUsage)
        if not pu:
            return False
        try:
            for pd in pu.part_definitions:
                if getattr(pd, "name", None) == "Component":
                    return True
        except Exception:
            pass
        return False

    def first_direct_partusage_child(node):
        for child in children_iter(node):
            pu_child = child.try_cast(syside.PartUsage)
            if pu_child:
                return child
        return None

    def dfs(node):
        if is_component_partusage(node):
            direct_child = first_direct_partusage_child(node)
            if direct_child is not None:
                return direct_child

        for child in children_iter(node):
            found = dfs(child)
            if found is not None:
                return found

        return None

    return dfs(elem)


def walk_ownership_tree(element, level: int = 0) -> None:
    if element.try_cast(syside.AttributeUsage):
        attr = element.cast(syside.AttributeUsage)
        expression_a1 = next(iter(attr.owned_elements), None)
        if expression_a1 is not None and isinstance(expression_a1, syside.LiteralRational):
            print("  " * level, f"{attr.name} = {expression_a1.value}")
        elif expression_a1 is not None and isinstance(expression_a1, syside.LiteralInteger):
            print("  " * level, f"{attr.name} = {expression_a1.value}")
        else:
            print("  " * level, f"{attr.name}", type(expression_a1))
    elif element.name is not None:
        print("  " * level, element.name)

    element.owned_elements.for_each(
        lambda owned_element: walk_ownership_tree(owned_element, level + 1)
    )


def find_part_by_name(element, name: str, part_level: int = 0):
    part = element.try_cast(syside.PartUsage)
    if part:
        print("  " * part_level + part.name)
        if part.name == name:
            return part
        part_level += 1

    children = getattr(element, "owned_elements", None)
    if not children:
        return None

    try:
        iterator = iter(children)
    except TypeError:
        lst = []
        children.for_each(lambda e: lst.append(e))
        iterator = iter(lst)

    for child in iterator:
        found = find_part_by_name(child, name, part_level)
        if found is not None:
            return found

    return None


def find_expression_attribute_values(element, level=0):
    del level

    if hasattr(element, "try_cast") and element.try_cast(syside.AttributeUsage):
        attr = element.cast(syside.AttributeUsage)
        expression_a1 = None
        try:
            expression_a1 = next(iter(attr.owned_elements), None)
        except Exception:
            expression_a1 = None
        if expression_a1 is not None and isinstance(expression_a1, syside.Expression):
            compiler = syside.Compiler()
            result, report = compiler.evaluate(expression_a1)
            assert not report.fatal, report.diagnostics
            name = (
                getattr(attr, "qualified_name", None)
                or getattr(attr, "declared_name", None)
                or "<unnamed>"
            )
            print(f"{name}: {result}")

    try:
        element.owned_elements.for_each(
            lambda owned_element: find_expression_attribute_values(
                owned_element, 1
            )
        )
    except Exception:
        try:
            for owned_element in element.owned_elements:
                find_expression_attribute_values(owned_element, 1)
        except Exception:
            pass
