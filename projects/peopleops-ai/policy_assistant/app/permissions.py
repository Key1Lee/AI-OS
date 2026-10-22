from app.models import DocumentMetadata
from app.rules import default_rules


def may_read_pto(principal, target_employee, tenant=None, security=None):
    """Permit self PTO or an exact delegated scope, never broad access from an HR role."""
    security = security or default_rules().security
    if not principal.active or (tenant is not None and principal.tenant != tenant):
        return False
    if target_employee == principal.employee_id:
        return security.self_permission in principal.permissions
    return bool(principal.delegation_purpose) and security.delegated_permission in principal.permissions and target_employee in principal.record_scope


def may_read_document(principal, metadata: DocumentMetadata, as_of, security=None):
    """Apply all document constraints before evidence can be ranked or sent to a model."""
    security = security or default_rules().security
    if not principal.active or metadata.tenant != principal.tenant:
        return False
    if metadata.status != "approved" or metadata.effective_date > as_of:
        return False
    if metadata.expiration_date and metadata.expiration_date <= as_of:
        return False
    if metadata.country not in ("ALL", principal.country) or principal.role not in metadata.access_roles:
        return False
    if metadata.employee_group != "all_authenticated" and metadata.employee_group not in principal.groups:
        return False
    if metadata.classification == "confidential":
        return False
    if metadata.classification == "restricted":
        return security.restricted_document_permission in principal.permissions
    return metadata.classification == "public" or security.internal_document_permission in principal.permissions
