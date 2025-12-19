from granian.constants import Interfaces, Loops
from granian.log import LogLevels
from api.settings import get_settings
from api.migrations import MigrationManager

from granian.server import Server
def main():
    settings = get_settings()
    # MigrationManager.apply_main_migrations(settings.POSTGRES)
    MigrationManager.apply_company_migrations(
        settings.POSTGRES, schema_name="company_test",
    )
    server = Server(
        target="api.app:app",
        interface=Interfaces.ASGI,
        address=settings.SERVER.HOST,
        port=settings.SERVER.PORT,
        workers=settings.SERVER.WORKERS,
        log_access=True if settings.ENVIRONMENT == "DEV" else False,
        log_level=LogLevels.debug if settings.ENVIRONMENT == "DEV" else LogLevels.info,
        loop=Loops.asyncio,
    )
    server.serve()
if __name__ == "__main__":
    main()
