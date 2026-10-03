package agentguard.policy.network

import future.keywords

# Non-network actions are not constrained by network rules
allowed if {
    input.action_intent.action != "NETWORK_REQUEST"
}

# Allowed if the target domain is in allowed_domains
allowed if {
    input.action_intent.action == "NETWORK_REQUEST"
    input.action_intent.target in data.policy.network.allowed_domains
}

# Denied if network request to an unapproved domain
denied if {
    input.action_intent.action == "NETWORK_REQUEST"
    not allowed
}
