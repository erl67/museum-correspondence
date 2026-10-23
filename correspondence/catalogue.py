"""Staff catalogue labels, separate from readings, attribution and matching."""


NAME_FIELDS = ("sender", "recipient", "attributed_author")


def name_key(value):
    return " ".join((value or "").split()).casefold()


def catalogue_names(metadata, hints, people):
    """Only explicitly enabled, unique authority aliases supply display labels.

    Never assign a person_id to a reading, resolve a conflicting alias, or use a
    filename to override an existing reading. No fuzzy/initial/surname matching.
    """
    aliases = {}
    for pid, person in people.items():
        if person.get("standardize_display"):
            for alias in [person["name"], *person["aliases"]]:
                key = name_key(alias)
                if key:
                    aliases.setdefault(key, set()).add(pid)
    labels = {}
    for name in NAME_FIELDS:
        field = metadata.get(name, {})
        readings = [v for v in (field.get("value"), field.get("normalized")) if name_key(v)]
        basis = "metadata" if readings else "filename hint"
        values = readings or [hints.get(name)]
        pid = field.get("person_id")
        if pid:
            candidates = {pid} if pid in people else set()
        else:
            candidates = set().union(*(aliases.get(name_key(v), set()) for v in values))
        if len(candidates) == 1:
            person = people[next(iter(candidates))]
            labels[name] = dict(name=person["name"], authority_id=person["person_id"],
                                basis=basis, matched_values=values, source=person["source"],
                                match="person_id" if pid else "catalogue alias")
    return labels
