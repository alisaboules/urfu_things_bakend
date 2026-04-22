-- ============================================================
-- База данных для сервиса поиска потерянных вещей
-- ============================================================

CREATE DATABASE lost_and_found
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    CONNECTION LIMIT = -1;

-- 1. Роли пользователей
CREATE TABLE role (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- 2. Пользователи 
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role_id INTEGER NOT NULL REFERENCES role(role_id) ON DELETE RESTRICT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Категории вещей (с поддержкой вложенности)
CREATE TABLE category (
    cat_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    parent_cat_id INTEGER REFERENCES category(cat_id) ON DELETE SET NULL
);

-- 4. Корпуса университета
CREATE TABLE building (
    building_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    address VARCHAR(100)
);

-- 5. Пункты выдачи
CREATE TABLE pickup_point (
    point_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    location VARCHAR(100),
    building_id INTEGER NOT NULL REFERENCES building(building_id) ON DELETE RESTRICT
);

-- 6. Находки
CREATE TABLE found_item (
    found_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES category(cat_id) ON DELETE RESTRICT,
    pickup_point_id INTEGER NOT NULL REFERENCES pickup_point(point_id) ON DELETE RESTRICT,
    location_type VARCHAR(20) CHECK (location_type IN ('building', 'map', 'free')),
    location_ref VARCHAR(100),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'issued', 'closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Пропажи
CREATE TABLE lost_item (
    lost_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES category(cat_id) ON DELETE RESTRICT,
    location_zone VARCHAR(50),
    location_text VARCHAR(200),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'matched', 'closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Фото (связь либо с находкой, либо с пропажей)
CREATE TABLE photo (
    photo_id SERIAL PRIMARY KEY,
    found_id INTEGER REFERENCES found_item(found_id) ON DELETE CASCADE,
    lost_id INTEGER REFERENCES lost_item(lost_id) ON DELETE CASCADE,
    image_url VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (found_id IS NOT NULL OR lost_id IS NOT NULL)
);

-- 9. Сопоставления находок и пропаж
CREATE TABLE match (
    match_id SERIAL PRIMARY KEY,
    found_id INTEGER NOT NULL REFERENCES found_item(found_id) ON DELETE CASCADE,
    lost_id INTEGER NOT NULL REFERENCES lost_item(lost_id) ON DELETE CASCADE,
    similarity_pct DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Выдачи вещей
CREATE TABLE issuance (
    found_id INTEGER PRIMARY KEY REFERENCES found_item(found_id) ON DELETE CASCADE,
    point_id INTEGER NOT NULL REFERENCES pickup_point(point_id) ON DELETE RESTRICT,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_by VARCHAR(100)
);

-- 11. Логи действий
CREATE TABLE log (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    action_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- ============================================================
-- Индексы для ускорения запросов
-- ============================================================

-- Поиск по пользователям
CREATE INDEX idx_users_role_id ON users(role_id);

-- Поиск по находкам
CREATE INDEX idx_found_item_user_id ON found_item(user_id);
CREATE INDEX idx_found_item_category_id ON found_item(category_id);
CREATE INDEX idx_found_item_pickup_point_id ON found_item(pickup_point_id);
CREATE INDEX idx_found_item_status ON found_item(status);
CREATE INDEX idx_found_item_created_at ON found_item(created_at);

-- Поиск по пропажам
CREATE INDEX idx_lost_item_user_id ON lost_item(user_id);
CREATE INDEX idx_lost_item_category_id ON lost_item(category_id);
CREATE INDEX idx_lost_item_status ON lost_item(status);
CREATE INDEX idx_lost_item_created_at ON lost_item(created_at);

-- Поиск по фото
CREATE INDEX idx_photo_found_id ON photo(found_id);
CREATE INDEX idx_photo_lost_id ON photo(lost_id);

-- Поиск по сопоставлениям
CREATE INDEX idx_match_found_id ON match(found_id);
CREATE INDEX idx_match_lost_id ON match(lost_id);
CREATE INDEX idx_match_status ON match(status);

-- Поиск по выдачам
CREATE INDEX idx_issuance_point_id ON issuance(point_id);
CREATE INDEX idx_issuance_user_id ON issuance(user_id);
CREATE INDEX idx_issuance_issued_at ON issuance(issued_at);

-- Поиск по логам
CREATE INDEX idx_log_user_id ON log(user_id);
CREATE INDEX idx_log_created_at ON log(created_at);
CREATE INDEX idx_log_entity ON log(entity_type, entity_id);

-- ============================================================
-- Начальные данные 
-- ============================================================

-- Роли
INSERT INTO role (name) VALUES ('student'), ('pickup_point'), ('admin');

INSERT INTO category (name, parent_cat_id) VALUES 
    ('Документы', NULL),
    ('Электроника', NULL),
    ('Одежда', NULL),
    ('Ключи', NULL),
    ('Сумки и рюкзаки', NULL),
    ('Паспорт', 1),
    ('Студенческий билет', 1),
    ('Электронный пропуск', 1),
    ('Наушники', 2),
    ('Зарядное устройство', 2),
    ('Телефон', 2),
    ('Куртка', 3),
    ('Рюкзак', 5);
