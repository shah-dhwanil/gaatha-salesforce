from uvicorn import run
from api.settings import get_settings
from api.migrations import MigrationManager
def main():
    settings = get_settings()
    #MigrationManager.apply_company_migrations(settings.POSTGRES, "_019b368a7f187fd19501ae8814b5c588_")
    run(
        "api.app:app",
        host=settings.SERVER.HOST,
        port=settings.SERVER.PORT,
        workers=settings.SERVER.WORKERS,
        reload=settings.SERVER.RELOAD,
        reload_dirs=["api"],
        reload_excludes=["__pycache__", "*.pyc", "*.pyo", "*.pyd", "*.pyw", "*.pyz"],
        reload_includes=["*.py"],
    )

if __name__ == "__main__":
    main()
