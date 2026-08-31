"""Domain exceptions with intentionally sanitized public messages."""


class EvaluatorError(Exception):
    """Base class for expected evaluator failures."""

    code = "evaluator_error"
    public_message = "The evaluator could not complete this request."


class TaskNotFoundError(EvaluatorError):
    code = "task_not_found"
    public_message = "The requested coding task does not exist."


class DockerUnavailableError(EvaluatorError):
    code = "docker_unavailable"
    public_message = (
        "The isolated runner is unavailable. Start Docker and try the evaluation again."
    )


class RunnerImageUnavailableError(EvaluatorError):
    code = "runner_image_unavailable"
    public_message = (
        "The evaluator runner image is not available. Build it using the documented setup command."
    )


class RunnerProtocolError(EvaluatorError):
    code = "runner_protocol_error"
    public_message = "The isolated runner returned an unreadable result."
