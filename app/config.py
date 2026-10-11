"""
Application Configuration Module for Pharmavigil
Handles environment variable loading, database parameters, and filesystem directories.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


@dataclass(frozen=True)
class MySQLConfig:
    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", 3306))
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "rootpassword")
    database: str = os.getenv("MYSQL_DATABASE", "pharmavigil_db")


@dataclass(frozen=True)
class MongoConfig:
    uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    database: str = os.getenv("MONGO_DB_NAME", "pharmavigil_db")
    adverse_collection: str = os.getenv("MONGO_ADVERSE_COLLECTION", "adverse_reports")


@dataclass(frozen=True)
class AppConfig:
    env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("APP_DEBUG", "true").lower() in ("true", "1", "yes")
    secret_key: str = os.getenv("APP_SECRET_KEY", "pharmavigil_default_secret_key_change_in_production")
    
    # Directories
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    exports_dir: Path = BASE_DIR / os.getenv("EXPORTS_DIR", "data/exports")
    sql_scripts_dir: Path = BASE_DIR / "sql_scripts"
    
    # Sub-configs
    mysql: MySQLConfig = MySQLConfig()
    mongo: MongoConfig = MongoConfig()


# Singleton configuration instance
config = AppConfig()

# Ensure required runtime directories exist
config.exports_dir.mkdir(parents=True, exist_ok=True)
config.data_dir.mkdir(parents=True, exist_ok=True)
