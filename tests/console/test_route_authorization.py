"""Systemic authorization guard for the HTTP surface.

Motivation (2026-09-18): ``/api/v1/ocr/*`` shipped with no visibility check at
all, so any authenticated user could read another organization's document text
by id (fixed in the same session). Reviewing every router by hand found no
further gaps, but hand review does not survive the next endpoint someone adds.

These tests make "an endpoint that talks to the API must be authenticated" a
checked invariant: every ``/api/**`` route must either be listed as intentionally
public here, or resolve ``get_current_user`` somewhere in its dependency tree.

Scope and limits, stated honestly: this catches a *missing* auth dependency. It
cannot detect a route that authenticates but omits a resource-visibility check
(the OCR defect), because those checks happen inside the endpoint body. Resource
level checks remain covered by the per-feature tests (e.g. test_ocr.py,
test_security_authz_fixes.py).
"""

from fastapi.routing import APIRoute

from auth.dependencies import get_current_user
from main import app

# Routes that must work without a bearer token, by design. Every entry is
# asserted to exist, so a stale entry fails the suite instead of silently
# widening the allowlist.
PUBLIC_API_ROUTES: set[tuple[str, str]] = {
    ("POST", "/api/v1/auth/token"),  # login
    ("POST", "/api/v1/auth/refresh"),  # refresh an expired access token
    ("POST", "/api/v1/auth/password-reset/request"),  # locked-out user
    ("POST", "/api/v1/auth/password-reset/confirm"),
    ("GET", "/api/v1/auth/oidc/login"),  # SSO handshake redirect
    ("GET", "/api/v1/auth/oidc/callback"),
    # M365 login bridge: the caller has no CivilPDF token yet by definition.
    # Guarded by a default-deny network allowlist (M365_ALLOWED_NETWORKS), rate
    # limiting, and full audit logging — see docs/architecture/m365-auth-design.md §3.
    ("POST", "/api/v1/auth/m365/login"),
}

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _api_routes() -> list[APIRoute]:
    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/"):
            continue
        routes.append(route)
    return routes


def _dependency_calls(dependant) -> set:
    """Every callable in a route's dependency tree, recursively."""
    found = set()
    for sub in dependant.dependencies:
        if sub.call is not None:
            found.add(sub.call)
        found |= _dependency_calls(sub)
    return found


def _route_methods(route: APIRoute) -> set[str]:
    return {m for m in route.methods if m in _HTTP_METHODS}


def _find_unprotected(
    routes, allowlist: set[tuple[str, str]] = PUBLIC_API_ROUTES
) -> list[str]:
    """Return ``"METHOD /path"`` for every API route with no auth dependency."""
    unprotected: list[str] = []
    for route in routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in sorted(_route_methods(route)):
            if (method, route.path) in allowlist:
                continue
            if get_current_user not in _dependency_calls(route.dependant):
                unprotected.append(f"{method} {route.path}")
    return unprotected


def test_api_route_inventory_is_not_empty():
    """Guard the guard: the introspection must actually find the API."""
    routes = _api_routes()
    assert len(routes) > 50, f"expected the full API surface, found {len(routes)}"


def test_dependency_introspection_works():
    """Guard the guard: a known-protected route must resolve get_current_user."""
    for route in _api_routes():
        if route.path == "/api/v1/documents/" and "GET" in route.methods:
            assert get_current_user in _dependency_calls(route.dependant)
            return
    raise AssertionError("GET /api/v1/documents/ not found — inventory changed")


def test_guard_detects_a_route_that_forgets_authentication():
    """Negative test: without this the invariant above could pass vacuously."""
    from fastapi import Depends, FastAPI

    probe = FastAPI()

    @probe.get("/api/v1/unprotected")
    def unprotected_route():  # deliberately has no auth dependency
        return {}

    @probe.get("/api/v1/protected")
    def protected_route(user=Depends(get_current_user)):  # noqa: ARG001
        return {}

    @probe.get("/api/v1/documents/")
    def allowlisted_ok(user=Depends(get_current_user)):  # noqa: ARG001
        return {}

    found = _find_unprotected(probe.routes)
    assert "GET /api/v1/unprotected" in found, "the guard failed to flag a bare route"
    assert "GET /api/v1/protected" not in found
    assert "GET /api/v1/documents/" not in found


def test_guard_honours_the_allowlist():
    """An allowlisted route is skipped even without an auth dependency."""
    from fastapi import FastAPI

    probe = FastAPI()

    @probe.post("/api/v1/auth/token")
    def login_without_token():
        return {}

    assert _find_unprotected(probe.routes) == []


def test_every_api_route_requires_authentication_unless_allowlisted():
    """No endpoint may be reachable without a token unless it is listed here."""
    unprotected = _find_unprotected(_api_routes())
    assert not unprotected, (
        "These API routes have no authentication dependency. Either add "
        "Depends(get_current_user) (directly or via require_admin/"
        "require_manager) or add an explicit entry to PUBLIC_API_ROUTES with a "
        "comment explaining why it is safe to expose:\n  "
        + "\n  ".join(unprotected)
    )


def test_public_allowlist_has_no_stale_entries():
    """A removed endpoint must not linger in the allowlist (it would hide one)."""
    existing = {(m, r.path) for r in _api_routes() for m in _route_methods(r)}
    stale = sorted(PUBLIC_API_ROUTES - existing)
    assert not stale, f"PUBLIC_API_ROUTES lists routes that no longer exist: {stale}"


def test_public_endpoints_are_few_and_deliberate():
    """Make widening the unauthenticated surface a visible, reviewable act."""
    public_api = [
        (m, r.path)
        for r in _api_routes()
        for m in _route_methods(r)
        if (m, r.path) in PUBLIC_API_ROUTES
    ]
    assert len(public_api) == len(PUBLIC_API_ROUTES), (
        "the allowlist and the router disagree on the public surface: "
        f"{sorted(public_api)}"
    )
    # Only the auth/SSO handshake may be unauthenticated.
    for method, path in public_api:
        assert path.startswith("/api/v1/auth/"), f"unexpected public route: {method} {path}"
