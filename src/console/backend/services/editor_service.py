from models.document import DocumentStatus


def determine_editor_status(sidecar: dict) -> DocumentStatus:
    stamps = sidecar.get("stamps", [])
    if stamps and all(s.get("status") == "approved" for s in stamps):
        return DocumentStatus.EDITOR_REVIEWED
    return DocumentStatus.EDITOR_DRAFT
