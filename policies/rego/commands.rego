package agentguard.policy.commands

import future.keywords.in

# Non-command actions are not constrained by command rules
allowed if {
    input.action_intent.action != "COMMAND_EXEC"
}

# Command explicitly matches a deny regex
denied if {
    input.action_intent.action == "COMMAND_EXEC"
    some pattern in data.policy.commands.deny
    regex.match(pattern, input.action_intent.target)
}

# Command matches an allow regex (and is not denied)
allowed if {
    input.action_intent.action == "COMMAND_EXEC"
    not denied
    some pattern in data.policy.commands.allow
    regex.match(pattern, input.action_intent.target)
}

# Denied if it is a command execution and not explicitly allowed
denied if {
    input.action_intent.action == "COMMAND_EXEC"
    not allowed
}
