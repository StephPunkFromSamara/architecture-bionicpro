-- Создание таблицы customers
CREATE TABLE IF NOT EXISTS customers (
    user_id INT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

-- Вставка тестовых данных
INSERT INTO customers (user_id, name, email) VALUES
(1, 'Alice', 'alice@example.com'),
(2, 'Bob', 'bob@example.com'),
(3, 'Charlie', 'charlie@example.com');