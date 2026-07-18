"""
Send's a trace to Langfuse for testing purposes.
"""

from langfuse import Langfuse

from app.core.config import settings


def main() -> None:
    langfuse = Langfuse(public_key=settings.langfuse_public_key, secret_key=settings.langfuse_secret_key, host=settings.langfuse_host)

    with langfuse.start_as_current_observation(as_type="span", name="nexusdoc-smoke-test", input={"ping": True}) as span:
        span.update(output={"pong": True})

    langfuse.flush()

    print("Trace sent to Langfuse - check Langfuse UI -> 'nexusdoc-smoke-test'")


if __name__ == "__main__":
    main()
