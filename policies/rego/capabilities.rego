package agentguard.policy.capabilities

import future.keywords

# Capability is explicitly denied
denied if {
    input.action_intent.capability in data.policy.capabilities.deny
}

# Capability requires human approval
requires_approval if {
    not denied
    input.action_intent.capability in data.policy.capabilities.approval
}

# Capability is explicitly allowed
allowed if {
    not denied
    not requires_approval
    input.action_intent.capability in data.policy.capabilities.allow
}
