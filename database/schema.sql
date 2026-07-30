-- Vote App Database Schema
-- Privacy-first voting system with user vote linkage

-- Users Table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(255) UNIQUE NOT NULL,
  email_hash VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Questions Table
CREATE TABLE questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(500) NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'open',
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Votes Table (USER-CONNECTED)
-- Key feature: Every vote is linked to a user so we can:
-- - Prevent duplicate votes from same user on same question
-- - Track voting patterns for transparency
-- - Verify vote integrity
-- - Maintain audit trails
CREATE TABLE votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  question_id UUID NOT NULL,
  answer VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- Foreign Keys to link votes to users and questions
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
  
  -- Constraint: One vote per user per question
  UNIQUE(user_id, question_id),
  
  -- Indexes for performance
  INDEX idx_user_id (user_id),
  INDEX idx_question_id (question_id),
  INDEX idx_created_at (created_at)
);

-- Audit Log Table
-- Tracks all changes to votes for transparency
CREATE TABLE vote_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vote_id UUID NOT NULL,
  user_id UUID NOT NULL,
  action VARCHAR(50) NOT NULL,  -- 'created', 'updated', 'deleted'
  old_value VARCHAR(255),
  new_value VARCHAR(255),
  reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (vote_id) REFERENCES votes(id) ON DELETE CASCADE,
  
  INDEX idx_user_id (user_id),
  INDEX idx_vote_id (vote_id),
  INDEX idx_created_at (created_at)
);

-- Create indexes for common queries
CREATE INDEX idx_votes_user_created ON votes(user_id, created_at);
CREATE INDEX idx_votes_question_created ON votes(question_id, created_at);
CREATE INDEX idx_audit_user_created ON vote_audit_log(user_id, created_at);

-- View: User Voting Summary
-- Shows all votes by a user (for verification/transparency)
CREATE VIEW user_vote_summary AS
SELECT 
  u.id as user_id,
  u.username,
  COUNT(v.id) as total_votes,
  MIN(v.created_at) as first_vote,
  MAX(v.created_at) as last_vote
FROM users u
LEFT JOIN votes v ON u.id = v.user_id
GROUP BY u.id, u.username;

-- View: Question Results with Vote Traceability
-- Shows aggregate results but can trace individual votes
CREATE VIEW question_results AS
SELECT 
  q.id as question_id,
  q.title,
  v.answer,
  COUNT(v.id) as vote_count,
  ROUND(100.0 * COUNT(v.id) / SUM(COUNT(v.id)) OVER (PARTITION BY q.id), 2) as percentage
FROM questions q
LEFT JOIN votes v ON q.id = v.question_id
GROUP BY q.id, q.title, v.answer;
