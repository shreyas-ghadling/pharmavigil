"""Apply additive workflow migrations without resetting application data."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import dotenv_values
from app.database.mysql_client import MySQLClient
from app.database.mongo_client import MongoDBClient


def clients(hosted=False, database="pharmavigil_db"):
    sql, mongo = MySQLClient(), MongoDBClient()
    if hosted:
        env = dotenv_values(ROOT / ".env.production.local")
        sql.host, sql.port = env["MYSQL_HOST"], int(env["MYSQL_PORT"])
        sql.user, sql.password, sql.database = env["MYSQL_USER"], env["MYSQL_PASSWORD"], env["MYSQL_DATABASE"]
        mongo.uri, mongo.db_name = env["MONGO_URI"], env["MONGO_DB_NAME"]
    else:
        sql.database = mongo.db_name = database
    return sql, mongo


def migrate_mongo(mongo):
    collection = mongo.get_adverse_reports_collection()
    collection.create_index("submission_key", unique=True, sparse=True, name="idx_submission_key_unique")
    collection.create_index("case_key", unique=True, sparse=True, name="idx_case_key_unique")
    print("Report retry and case-reference indexes ready.")


def migrate_stock(sql):
    sql.execute_update("CREATE TABLE IF NOT EXISTS app_schema_migrations (name VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    sql.execute_update("""CREATE TABLE IF NOT EXISTS stock_receipts (
        receipt_id INT AUTO_INCREMENT PRIMARY KEY, batch_number VARCHAR(50) NOT NULL,
        quantity_received INT NOT NULL, receipt_date DATE NOT NULL, reference VARCHAR(100) NOT NULL,
        source_type VARCHAR(25) NOT NULL DEFAULT 'RECEIPT', recorded_by VARCHAR(100) NOT NULL,
        CONSTRAINT fk_receipt_batch FOREIGN KEY (batch_number) REFERENCES batches(batch_number),
        CONSTRAINT chk_receipt_quantity CHECK (quantity_received > 0),
        UNIQUE KEY uq_receipt_reference (batch_number, reference)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    # Preserve the pre-migration model's balances, without claiming a verified receipt.
    with sql.get_cursor(dictionary=False) as cursor:
        cursor.execute("INSERT IGNORE INTO app_schema_migrations(name) VALUES ('stock-receipts-v1')")
        if cursor.rowcount:
            cursor.execute("""INSERT INTO stock_receipts
        (batch_number, quantity_received, receipt_date, reference, source_type, recorded_by)
        SELECT b.batch_number, b.total_units_produced, b.manufacturing_date,
               'LEGACY-OPENING', 'LEGACY_OPENING', 'Workflow migration'
        FROM batches b LEFT JOIN stock_receipts r ON r.batch_number=b.batch_number
        WHERE r.receipt_id IS NULL""")
    print("Stock receipt ledger ready; legacy opening balances labelled explicitly.")


def migrate_units(sql):
    existing = sql.execute_one("SELECT COUNT(*) AS n FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='medicines' AND column_name='stock_unit'")
    if not existing["n"]:
        sql.execute_update("ALTER TABLE medicines ADD COLUMN stock_unit VARCHAR(20) NOT NULL DEFAULT 'unspecified'")
    for medicine_id, name, unit in [(101,"Cardiomax","tablet"),(102,"Neurocalm","capsule"),
        (103,"Glucoguard","tablet"),(104,"PulmoBreeze","inhaler"),(105,"GastroRelief","capsule"),(106,"Dermacure","tube")]:
        sql.execute_update("UPDATE medicines SET stock_unit=%s WHERE medicine_id=%s AND commercial_name=%s AND stock_unit='unspecified'", (unit,medicine_id,name))
    print("Demo stock units defined; other catalog entries retain an explicit unspecified unit.")


def migrate_recall(sql):
    """Install the versioned atomic recall routine; keep the earlier routine for older deployments."""
    exists = sql.execute_one("SELECT COUNT(*) AS n FROM information_schema.routines WHERE routine_schema=DATABASE() AND routine_name='sp_recall_batch_v2'")
    if not exists['n']:
        source = (ROOT / 'sql_scripts' / 'stored_procedures.sql').read_text()
        statement = source[source.index('CREATE PROCEDURE'):source.index('END //') + len('END')]
        sql.execute_update(statement)
    print('Atomic recall routine ready.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosted", action="store_true")
    parser.add_argument("--database", default="pharmavigil_db")
    args = parser.parse_args()
    sql, mongo = clients(args.hosted, args.database)
    migrate_mongo(mongo)
    migrate_stock(sql)
    migrate_units(sql)
    migrate_recall(sql)
    mongo.close()
