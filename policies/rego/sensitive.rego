package agentguard.policy.sensitive

import future.keywords

# Escalates if action touches a sensitive file pattern
requires_approval if {
    some rule in data.policy.sensitive_actions
    rule.trigger == "file_pattern"
    input.action_intent.action in ["FILE_WRITE", "FILE_READ"]
    glob.match(rule.pattern, ["/"], input.action_intent.target)
}

# Identify which sensitive rule triggered
matched_rule := rule.name if {
    some rule in data.policy.sensitive_actions
    rule.trigger == "file_pattern"
    input.action_intent.action in ["FILE_WRITE", "FILE_READ"]
    glob.match(rule.pattern, ["/"], input.action_intent.target)
}
