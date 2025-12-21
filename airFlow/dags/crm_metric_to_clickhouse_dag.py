from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import clickhouse_connect
import psycopg2
import os


# ==== Настройки ====
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 1, 1),
}

OUTPUT_SQL = './dags/sql/insert_clickhouse.sql'


# ==== 1️⃣ Создание таблицы в ClickHouse ====
def create_clickhouse_table():
    client = clickhouse_connect.get_client(
        host='clickhouse',
        port=8123,
        username='airflow',
        password='airflow'
    )
    client.command("""
        CREATE TABLE IF NOT EXISTS user_metrics_report (
            user_id UInt32,
            name String,
            age UInt8,
            prosthesis_id String,
            usage_hours Float32,
            temperature Float32
        ) ENGINE = MergeTree()
        ORDER BY user_id;
    """)
    print("✅ ClickHouse table 'user_metrics_report' ensured.")


# ==== 2️⃣ Извлечение и объединение данных из Postgres ====
def extract_and_merge_data():
    crm_conn = psycopg2.connect(
        dbname="crm_db",
        user="airflow",
        password="airflow",
        host="postgres-crm",
        port=5432,
    )
    metric_conn = psycopg2.connect(
        dbname="metric_db",
        user="airflow",
        password="airflow",
        host="postgres-metric",
        port=5432,
    )

    crm_df = pd.read_sql("SELECT user_id, name, age FROM crm.customers;", crm_conn)
    metric_df = pd.read_sql("SELECT user_id, prosthesis_id, usage_hours, temperature FROM metrics.device_metrics;", metric_conn)

    merged_df = pd.merge(crm_df, metric_df, on="user_id", how="inner")

    os.makedirs(os.path.dirname(OUTPUT_SQL), exist_ok=True)
    with open(OUTPUT_SQL, "w") as f:
        for _, row in merged_df.iterrows():
            q = (
                f"INSERT INTO user_metrics_report "
                f"(user_id, name, age, prosthesis_id, usage_hours, temperature) "
                f"VALUES ({row['user_id']}, '{row['name']}', {row['age']}, "
                f"'{row['prosthesis_id']}', {row['usage_hours']}, {row['temperature']});"
            )
            f.write(q + "\n")

    crm_conn.close()
    metric_conn.close()
    print(f"✅ Data merged ({len(merged_df)} rows) and SQL file prepared.")


# ==== 3️⃣ Загрузка данных в ClickHouse ====
def load_to_clickhouse():
    client = clickhouse_connect.get_client(
        host='clickhouse',
        port=8123,
        username='airflow',
        password='airflow'
    )
    with open(OUTPUT_SQL, "r") as f:
        for query in f:
            client.command(query.strip())
    print("✅ Data successfully inserted into ClickHouse.")


# ==== DAG ====
with DAG(
    'crm_metric_db_to_clickhouse_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
) as dag:

    create_table = PythonOperator(
        task_id='create_clickhouse_table',
        python_callable=create_clickhouse_table
    )

    prepare_data = PythonOperator(
        task_id='extract_and_merge',
        python_callable=extract_and_merge_data
    )

    load_data = PythonOperator(
        task_id='load_to_clickhouse',
        python_callable=load_to_clickhouse
    )

    create_table >> prepare_data >> load_data