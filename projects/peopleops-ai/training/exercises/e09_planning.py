from lab.contracts import Plan, Principal, PendingExercise


def plan_action(message: str, principal: Principal) -> Plan:
    """E09: select an allowlisted tool with validated arguments; never execute.

    'Employee needs help with payroll' => create_ticket, Payroll category.
    Ambiguous requests => clarify; dates/hours must not be invented.
    """
    raise PendingExercise("E09 plan_action")
