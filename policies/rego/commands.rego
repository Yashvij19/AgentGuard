package agentguard.policy.commands

import future.keywords

# Non-command actions are not constrained by command rules
allowed if {
    input.action_intent.action != "COMMAND_EXEC"
}

# Command explicitly matches a deny regex
explicitly_denied if {
    input.action_intent.action == "COMMAND_EXEC"
    some pattern in data.policy.commands.deny
    regex.match(pattern, input.action_intent.target)
}

# Command matches an allow regex (and is not explicitly denied)
allowed if {
    input.action_intent.action == "COMMAND_EXEC"
    not explicitly_denied
    some pattern in data.policy.commands.allow
    regex.match(pattern, input.action_intent.target)
}

# Denied if explicitly denied
denied if {
    input.action_intent.action == "COMMAND_EXEC"
    explicitly_denied
}

# Denied if it is a command execution and not allowed
denied if {
    input.action_intent.action == "COMMAND_EXEC"
    not allowed
}
