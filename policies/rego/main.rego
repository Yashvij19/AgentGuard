package agentguard.policy

import future.keywords

import data.agentguard.policy.capabilities
import data.agentguard.policy.commands
import data.agentguard.policy.filesystem
import data.agentguard.policy.network
import data.agentguard.policy.sensitive

# 1. FAIL-CLOSED DEFAULT
default decision := "DENY"
default matched_rule := "default_deny"
default reason := "Action does not satisfy any explicit allow policy"

# 2. DENY RULES (Highest precedence)
decision := "DENY" if {
    is_denied
}

is_denied if capabilities.denied
is_denied if commands.denied
is_denied if filesystem.denied
is_denied if network.denied

matched_rule := "capability_denied" if capabilities.denied
matched_rule := "command_denied" if commands.denied
matched_rule := "filesystem_denied" if filesystem.denied
matched_rule := "network_denied" if network.denied

reason := "Action capability is explicitly forbidden" if capabilities.denied
reason := "Command pattern is forbidden by security policy" if commands.denied
reason := "Target path is outside permitted filesystem boundaries" if filesystem.denied
reason := "Destination domain is not permitted" if network.denied

# 3. REQUIRE_APPROVAL RULES (Second precedence)
decision := "REQUIRE_APPROVAL" if {
    not is_denied
    is_approval_required
}

is_approval_required if capabilities.requires_approval
is_approval_required if sensitive.requires_approval

matched_rule := "capability_requires_approval" if {
    not is_denied
    capabilities.requires_approval
}

matched_rule := concat(":", ["sensitive_action", sensitive.matched_rule]) if {
    not is_denied
    not capabilities.requires_approval
    sensitive.requires_approval
}

reason := "Capability requires human authorization before execution" if {
    not is_denied
    capabilities.requires_approval
}

reason := "Action impacts high-risk or sensitive infrastructure" if {
    not is_denied
    not capabilities.requires_approval
    sensitive.requires_approval
}

# 4. ALLOW RULES (Lowest precedence — all checks must pass)
decision := "ALLOW" if {
    not is_denied
    not is_approval_required
    capabilities.allowed
    filesystem.allowed
    commands.allowed
    network.allowed
}

matched_rule := "policy_allow" if {
    decision == "ALLOW"
}

reason := "Action complies with all repository security policies" if {
    decision == "ALLOW"
}

# 5. CONSOLIDATED EVALUATION RESULT
result := {
    "decision": decision,
    "rule_matched": matched_rule,
    "reason": reason,
    "target": input.action_intent.target,
    "capability": input.action_intent.capability
}
