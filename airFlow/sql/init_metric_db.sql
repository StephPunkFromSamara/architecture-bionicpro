-- Создание таблицы user_metrics
CREATE TABLE IF NOT EXISTS user_metrics (
    user_id INT PRIMARY KEY,
    name TEXT,
    age INT,
    prosthesis_id TEXT,
    usage_hours FLOAT,
    temperature FLOAT
);

-- Вставка тестовых данных
INSERT INTO user_metrics (user_id, name, age, prosthesis_id, usage_hours, temperature) VALUES
(1, 'Alice', 30, 'P123', 12.5, 36.6),
(2, 'Bob', 45, 'P124', 8.0, 36.8),
(3, 'Charlie', 50, 'P125', 15.0, 37.0);