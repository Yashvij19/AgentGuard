package agentguard.policy.filesystem

import future.keywords.in

# Non-file actions are not constrained by filesystem rules
allowed if {
    input.action_intent.action != "FILE_READ"
    input.action_intent.action != "FILE_WRITE"
}

# FILE_READ matches an allowed read pattern
allowed if {
    input.action_intent.action == "FILE_READ"
    some pattern in data.policy.filesystem.read
    glob.match(pattern, ["/"], input.action_intent.target)
}

# FILE_WRITE matches an allowed write pattern
allowed if {
    input.action_intent.action == "FILE_WRITE"
    some pattern in data.policy.filesystem.write
    glob.match(pattern, ["/"], input.action_intent.target)
}

# Denied if it is a file action and not allowed
denied if {
    input.action_intent.action in ["FILE_READ", "FILE_WRITE"]
    not allowed
}
