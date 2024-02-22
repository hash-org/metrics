import structlog.stdlib
import structlog

from structlog.processors import TimeStamper, add_log_level


# Configure structlog to remove logger name from output
structlog.configure(
    processors=[
        structlog.processors.format_exc_info,
        add_log_level,
        TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(colors=True),
    ]
)

LOG = structlog.get_logger("runner")
