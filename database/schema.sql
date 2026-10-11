CREATE TABLE IF NOT EXISTS admin_recipients (
    id UUID PRIMARY KEY,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    admin_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delivery_mode VARCHAR(50) DEFAULT 'summary',
    destination_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(question_id, admin_id)
);
