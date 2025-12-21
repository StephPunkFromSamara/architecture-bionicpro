-- Создаем схему (если нужно)
CREATE SCHEMA IF NOT EXISTS metrics;

-- Таблица метрик протезов
CREATE TABLE IF NOT EXISTS metrics.device_metrics (
    id SERIAL PRIMARY KEY,
    user_id INT,
    prosthesis_id VARCHAR(50),
    usage_hours FLOAT,
    temperature FLOAT
);

-- Очищаем таблицу (игнорируем ошибку если таблицы нет)
DO $$
BEGIN
    TRUNCATE TABLE metrics.device_metrics;
EXCEPTION
    WHEN undefined_table THEN NULL;
END $$;

-- Тестовые данные
INSERT INTO metrics.device_metrics (user_id, prosthesis_id, usage_hours, temperature) VALUES
(1, 'PX-101', 120.5, 36.6),
(2, 'PX-202', 85.0, 37.1),
(3, 'PX-303', 42.3, 36.8),
(4, 'PX-404', 150.2, 37.0),
(5, 'PX-505', 210.8, 36.5);