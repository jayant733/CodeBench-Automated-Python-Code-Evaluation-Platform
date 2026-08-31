def transform_api_users(payload: dict) -> list[dict]:
    """Validate and flatten active users from an API payload."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dictionary")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise ValueError("payload must contain data.users")

    transformed: list[dict] = []
    for user in data["users"]:
        if not isinstance(user, dict):
            raise ValueError("users must be dictionaries")
        user_id = user.get("id")
        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise ValueError("user id must be an integer")

        profile = user.get("profile")
        if not isinstance(profile, dict):
            raise ValueError("user profile must be a dictionary")
        display_name = profile.get("display_name")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display name must be a non-empty string")

        active = user.get("active", True)
        if not isinstance(active, bool):
            raise ValueError("active must be a boolean")
        roles = user.get("roles", [])
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise ValueError("roles must be a list of strings")

        if active:
            transformed.append(
                {
                    "id": user_id,
                    "name": display_name.strip(),
                    "roles": list(dict.fromkeys(roles)),
                }
            )
    return transformed

