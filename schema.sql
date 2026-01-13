-- Expense Manager Database Schema
-- Generated on: 2026-01-07

-- Drop existing tables
DROP TABLE IF EXISTS chat_message CASCADE;
DROP TABLE IF EXISTS investment CASCADE;
DROP TABLE IF EXISTS investment_type CASCADE;
DROP TABLE IF EXISTS budget CASCADE;
DROP TABLE IF EXISTS expense CASCADE;
DROP TABLE IF EXISTS payment_method CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

-- Table: user
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    monthly_budget DOUBLE PRECISION DEFAULT 0.0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITHOUT TIME ZONE
);

-- Table: category
CREATE TABLE category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) DEFAULT 'fas fa-tag',
    color VARCHAR(20) DEFAULT 'primary',
    user_id INTEGER REFERENCES "user"(id),
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: payment_method
CREATE TABLE payment_method (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    icon VARCHAR(50) DEFAULT 'fas fa-credit-card',
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: investment_type
CREATE TABLE investment_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    icon VARCHAR(50) DEFAULT 'fas fa-chart-line',
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    user_id INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: expense
CREATE TABLE expense (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    amount DOUBLE PRECISION NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    payment_method VARCHAR(50) DEFAULT 'cash',
    payment_method_id INTEGER REFERENCES payment_method(id),
    receipt_filename VARCHAR(255),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    category_id INTEGER NOT NULL REFERENCES category(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: budget
CREATE TABLE budget (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES category(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    amount DOUBLE PRECISION NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: investment
CREATE TABLE investment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    investment_type_id INTEGER NOT NULL REFERENCES investment_type(id),
    amount DOUBLE PRECISION NOT NULL,
    investment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_return DOUBLE PRECISION,
    maturity_date DATE,
    current_value DOUBLE PRECISION,
    notes TEXT,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: chat_message
CREATE TABLE chat_message (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    message TEXT NOT NULL,
    response TEXT,
    response_type VARCHAR(20) DEFAULT 'text',
    image_data TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_expense_user_id ON expense(user_id);
CREATE INDEX idx_expense_category_id ON expense(category_id);
CREATE INDEX idx_expense_date ON expense(date);
CREATE INDEX idx_expense_payment_method_id ON expense(payment_method_id);
CREATE INDEX idx_category_user_id ON category(user_id);
CREATE INDEX idx_payment_method_user_id ON payment_method(user_id);
CREATE INDEX idx_budget_user_id ON budget(user_id);
CREATE INDEX idx_budget_category_id ON budget(category_id);
CREATE INDEX idx_investment_user_id ON investment(user_id);
CREATE INDEX idx_investment_date ON investment(investment_date);
CREATE INDEX idx_chat_message_user_id ON chat_message(user_id);
CREATE INDEX idx_chat_message_created_at ON chat_message(created_at);
