CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    monthly_limit REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    category_id INTEGER NOT NULL,
    note TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);


-- Запросы к БД

-- Проверка наличия таблицы categories
SELECT name FROM sqlite_master WHERE type='table' AND name='categories';

-- Подсчёт категорий
SELECT COUNT(1) FROM categories;

-- Вставка стандартных категорий
INSERT INTO categories (name, monthly_limit) VALUES ('Кофе', 3000);

-- Получение списка расходов
SELECT e.id, e.date, e.amount, e.category_id, e.note, c.name as category
FROM expenses e
JOIN categories c ON e.category_id = c.id;

-- Получение списка категорий
SELECT * FROM categories ORDER BY name;

-- Получение одной записи расхода по id
SELECT e.id, e.date, e.amount, e.category_id, e.note, c.name as category
FROM expenses e
JOIN categories c ON e.category_id = c.id
WHERE e.id = 1;

-- Проверка существования категории
SELECT 1 FROM categories WHERE id = 1;

-- Ежемесячный отчёт
SELECT c.name, SUM(e.amount) AS total
FROM expenses e
JOIN categories c ON e.category_id = c.id
WHERE e.date >= '2026-05-01T00:00' AND e.date < '2026-06-01T00:00'
GROUP BY e.category_id, c.name;

-- Ежедневный отчёт
SELECT c.name, SUM(e.amount) AS total
FROM expenses e
JOIN categories c ON e.category_id = c.id
WHERE e.date >= '2026-05-27T00:00' AND e.date <= '2026-05-27T23:59:59'
GROUP BY e.category_id, c.name;

-- Первое значение id категории
SELECT id FROM categories LIMIT 1;

-- Добавление расхода
INSERT INTO expenses (date, amount, category_id, note) VALUES ('2026-05-27T12:00', 1500.0, 1, 'Моковый расход');

-- Поиск категории по имени
SELECT id FROM categories WHERE name = 'Кофе';

-- Обновление лимита категории
UPDATE categories SET monthly_limit = 5000 WHERE id = 1;

-- Добавление новой категории
INSERT INTO categories (name, monthly_limit) VALUES ('Развлечения', 7000);

-- Удаление категории
DELETE FROM categories WHERE id = 1;

-- Удаление расхода
DELETE FROM expenses WHERE id = 1;

-- Обновление расхода
UPDATE expenses SET date = '2026-05-27T09:00', amount = 2000, category_id = 1, note = 'Обновлённый расход' WHERE id = 1;

-- Обновление лимита существующей категории
UPDATE categories SET monthly_limit = 10000 WHERE id = 1;
