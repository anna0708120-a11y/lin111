"""Legacy Dwell URL compatibility for the Lin Shell Workgroup tab."""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["lin-spaces"])


@router.get("/spaces")
def spaces_page() -> RedirectResponse:
    """Legacy links enter the native Lin Workgroup tab."""
    return RedirectResponse("/?view=workgroup", status_code=307)
