-- Создаем схему (если нужно)
CREATE SCHEMA IF NOT EXISTS crm;

-- Создаем таблицу клиентов
CREATE TABLE IF NOT EXISTS crm.customers (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT
);

-- Очищаем таблицу, чтобы можно было перезапускать (игнорируем ошибку если таблицы нет)
DO $$
BEGIN
    TRUNCATE TABLE crm.customers;
EXCEPTION
    WHEN undefined_table THEN NULL;
END $$;

-- Вставляем тестовые данные
INSERT INTO crm.customers (name, age) VALUES
('Иван', 35),
('Мария', 42),
('Андрей', 28),
('Ольга', 31),
('Дмитрий', 45);