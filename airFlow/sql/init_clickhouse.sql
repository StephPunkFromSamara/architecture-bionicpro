-- Таблица для объединённых данных
CREATE TABLE IF NOT EXISTS user_metrics_report (
    user_id UInt32,
    name String,
    email String,
    prosthesis_id String,
    usage_hours Float32,
    temperature Float32
)
ENGINE = MergeTree()
ORDER BY user_id;