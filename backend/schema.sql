-- =============================================================================
-- AI Exam Guardian — MySQL Schema
-- Database: AWS RDS MySQL 8.0+
--
-- Tables:
--   users, students, teachers, exams, exam_rules,
--   exam_sessions, events, risk_scores, incidents,
--   evidence, ai_provider_logs, rag_documents, rag_chunks, audit_logs
--
-- Usage:
--   mysql -h <host> -u root -p < schema.sql
--   (script creates and selects the database automatically)
-- =============================================================================

-- =============================================================================
-- DATABASE BOOTSTRAP
-- =============================================================================
CREATE DATABASE IF NOT EXISTS exam_guardian
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE exam_guardian;

-- =============================================================================
-- SESSION SETTINGS
-- =============================================================================
SET FOREIGN_KEY_CHECKS = 0;
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- =============================================================================
-- USERS (base identity table — teachers and students extend this)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            CHAR(36)        NOT NULL DEFAULT (UUID()),
    email         VARCHAR(255)    NOT NULL,
    password_hash VARCHAR(255)    NOT NULL,
    role          ENUM('teacher', 'student', 'admin') NOT NULL DEFAULT 'student',
    is_active     TINYINT(1)      NOT NULL DEFAULT 1,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- STUDENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS students (
    id            CHAR(36)        NOT NULL DEFAULT (UUID()),
    user_id       CHAR(36)        NOT NULL,
    full_name     VARCHAR(255)    NOT NULL,
    student_number VARCHAR(100)   NULL,
    institution   VARCHAR(255)    NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_students_user_id (user_id),
    INDEX idx_students_institution (institution),
    CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- TEACHERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS teachers (
    id            CHAR(36)        NOT NULL DEFAULT (UUID()),
    user_id       CHAR(36)        NOT NULL,
    full_name     VARCHAR(255)    NOT NULL,
    institution   VARCHAR(255)    NULL,
    department    VARCHAR(255)    NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_teachers_user_id (user_id),
    INDEX idx_teachers_institution (institution),
    CONSTRAINT fk_teachers_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- EXAMS
-- =============================================================================
CREATE TABLE IF NOT EXISTS exams (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    teacher_id      CHAR(36)        NOT NULL,
    title           VARCHAR(255)    NOT NULL,
    description     TEXT            NULL,
    duration_minutes INT            NOT NULL DEFAULT 60,
    status          ENUM('draft', 'active', 'closed', 'archived') NOT NULL DEFAULT 'draft',
    starts_at       DATETIME        NULL,
    ends_at         DATETIME        NULL,
    allow_resources TINYINT(1)      NOT NULL DEFAULT 0,  -- closed-book by default
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_exams_teacher_id (teacher_id),
    INDEX idx_exams_status (status),
    INDEX idx_exams_starts_at (starts_at),
    CONSTRAINT fk_exams_teacher FOREIGN KEY (teacher_id) REFERENCES teachers (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- EXAM_RULES  (configurable per-exam scoring weights)
-- =============================================================================
CREATE TABLE IF NOT EXISTS exam_rules (
    id                              CHAR(36)    NOT NULL DEFAULT (UUID()),
    exam_id                         CHAR(36)    NOT NULL,
    -- Risk score weights (override global defaults from env vars)
    weight_tab_switch               INT         NOT NULL DEFAULT 10,
    weight_focus_loss               INT         NOT NULL DEFAULT 5,
    weight_copy                     INT         NOT NULL DEFAULT 15,
    weight_paste                    INT         NOT NULL DEFAULT 15,
    weight_fullscreen_exit          INT         NOT NULL DEFAULT 10,
    weight_suspicious_navigation    INT         NOT NULL DEFAULT 20,
    weight_ai_assistant_signal      INT         NOT NULL DEFAULT 25,
    weight_repeated_violations      INT         NOT NULL DEFAULT 20,
    weight_suspicious_sequence      INT         NOT NULL DEFAULT 20,
    -- Thresholds
    threshold_monitoring            INT         NOT NULL DEFAULT 20,
    threshold_attention             INT         NOT NULL DEFAULT 40,
    threshold_review_required       INT         NOT NULL DEFAULT 60,
    threshold_high_priority         INT         NOT NULL DEFAULT 80,
    -- Flags
    fullscreen_required             TINYINT(1)  NOT NULL DEFAULT 1,
    ai_detection_enabled            TINYINT(1)  NOT NULL DEFAULT 1,
    created_at                      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_exam_rules_exam_id (exam_id),
    CONSTRAINT fk_exam_rules_exam FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- EXAM_SESSIONS  (one row per student attempt)
-- =============================================================================
CREATE TABLE IF NOT EXISTS exam_sessions (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    exam_id         CHAR(36)        NOT NULL,
    student_id      CHAR(36)        NOT NULL,
    started_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at        DATETIME        NULL,
    status          ENUM('active', 'completed', 'flagged', 'abandoned') NOT NULL DEFAULT 'active',
    ip_address      VARCHAR(45)     NULL,   -- IPv4 or IPv6
    user_agent      TEXT            NULL,
    extension_active TINYINT(1)     NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_sessions_exam_id (exam_id),
    INDEX idx_sessions_student_id (student_id),
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_started_at (started_at),
    CONSTRAINT fk_sessions_exam    FOREIGN KEY (exam_id)    REFERENCES exams    (id) ON DELETE RESTRICT,
    CONSTRAINT fk_sessions_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- EVENTS  (raw telemetry from browser extension)
-- =============================================================================
CREATE TABLE IF NOT EXISTS events (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    session_id      CHAR(36)        NOT NULL,
    event_type      VARCHAR(64)     NOT NULL,  -- TAB_SWITCH, FOCUS_LOSS, COPY, PASTE, etc.
    occurred_at     DATETIME(3)     NOT NULL,  -- millisecond precision
    received_at     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    source          VARCHAR(64)     NOT NULL DEFAULT 'extension',  -- extension | backend | mcp
    metadata        JSON            NULL,      -- flexible per-event payload
    processed       TINYINT(1)      NOT NULL DEFAULT 0,

    PRIMARY KEY (id),
    INDEX idx_events_session_id (session_id),
    INDEX idx_events_event_type (event_type),
    INDEX idx_events_occurred_at (occurred_at),
    INDEX idx_events_processed (processed),
    CONSTRAINT fk_events_session FOREIGN KEY (session_id) REFERENCES exam_sessions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- RISK_SCORES  (deterministic score snapshots — updated by MCP Rules Engine)
-- =============================================================================
CREATE TABLE IF NOT EXISTS risk_scores (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    session_id      CHAR(36)        NOT NULL,
    score           INT             NOT NULL DEFAULT 0,  -- 0–100
    risk_level      ENUM('NORMAL','MONITORING','ATTENTION','REVIEW_REQUIRED','HIGH_PRIORITY_REVIEW')
                                    NOT NULL DEFAULT 'NORMAL',
    calculated_at   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    contributing_events JSON        NULL,   -- snapshot of event IDs and weights
    notes           TEXT            NULL,

    PRIMARY KEY (id),
    INDEX idx_risk_session_id (session_id),
    INDEX idx_risk_level (risk_level),
    INDEX idx_risk_calculated_at (calculated_at),
    CONSTRAINT fk_risk_session FOREIGN KEY (session_id) REFERENCES exam_sessions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- INCIDENTS  (flagged sessions requiring teacher review)
-- =============================================================================
CREATE TABLE IF NOT EXISTS incidents (
    id                  CHAR(36)        NOT NULL DEFAULT (UUID()),
    session_id          CHAR(36)        NOT NULL,
    created_by          VARCHAR(64)     NOT NULL DEFAULT 'system',  -- system | teacher_id
    status              ENUM('open','under_review','resolved','dismissed') NOT NULL DEFAULT 'open',
    risk_score_at_flag  INT             NOT NULL DEFAULT 0,
    risk_level_at_flag  ENUM('NORMAL','MONITORING','ATTENTION','REVIEW_REQUIRED','HIGH_PRIORITY_REVIEW')
                                        NOT NULL DEFAULT 'NORMAL',
    ai_explanation      TEXT            NULL,   -- Groq/NVIDIA generated summary
    ai_provider_used    VARCHAR(64)     NULL,   -- groq | nvidia | none
    teacher_notes       TEXT            NULL,
    resolved_at         DATETIME        NULL,
    resolved_by         CHAR(36)        NULL,   -- teacher user_id
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_incidents_session_id (session_id),
    INDEX idx_incidents_status (status),
    INDEX idx_incidents_created_at (created_at),
    CONSTRAINT fk_incidents_session FOREIGN KEY (session_id) REFERENCES exam_sessions (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- EVIDENCE  (individual evidence items linked to an incident)
-- =============================================================================
CREATE TABLE IF NOT EXISTS evidence (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    incident_id     CHAR(36)        NOT NULL,
    event_id        CHAR(36)        NULL,       -- optional link to raw event
    evidence_type   VARCHAR(64)     NOT NULL,   -- AI_SIGNAL, BEHAVIORAL, SEQUENCE, POLICY
    description     TEXT            NOT NULL,
    occurred_at     DATETIME(3)     NULL,
    severity        ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
    score_contribution INT          NOT NULL DEFAULT 0,
    confidence      DECIMAL(4,3)    NOT NULL DEFAULT 0.500, -- 0.000–1.000
    metadata        JSON            NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_evidence_incident_id (incident_id),
    INDEX idx_evidence_evidence_type (evidence_type),
    INDEX idx_evidence_occurred_at (occurred_at),
    CONSTRAINT fk_evidence_incident FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE,
    CONSTRAINT fk_evidence_event    FOREIGN KEY (event_id)    REFERENCES events   (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- AI_PROVIDER_LOGS  (Groq / NVIDIA request/response audit)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_provider_logs (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    request_id      CHAR(36)        NOT NULL DEFAULT (UUID()),
    session_id      CHAR(36)        NULL,       -- optional context link
    provider        ENUM('groq','nvidia','none') NOT NULL,
    is_fallback     TINYINT(1)      NOT NULL DEFAULT 0,
    model           VARCHAR(128)    NULL,
    prompt_tokens   INT             NULL,
    completion_tokens INT           NULL,
    latency_ms      INT             NULL,
    http_status     SMALLINT        NULL,
    failure_reason  VARCHAR(255)    NULL,   -- timeout | rate_limit | quota | 5xx | empty | etc.
    success         TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    INDEX idx_ai_logs_provider (provider),
    INDEX idx_ai_logs_success (success),
    INDEX idx_ai_logs_created_at (created_at),
    INDEX idx_ai_logs_request_id (request_id),
    CONSTRAINT fk_ai_logs_session FOREIGN KEY (session_id) REFERENCES exam_sessions (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- RAG_DOCUMENTS  (policy/guideline source documents)
-- =============================================================================
CREATE TABLE IF NOT EXISTS rag_documents (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    exam_id         CHAR(36)        NULL,       -- NULL = institution-wide
    institution     VARCHAR(255)    NULL,
    doc_type        ENUM('exam_rules','institution_policy','ai_policy','allowed_resources',
                         'prohibited_resources','review_procedures','incident_guidance',
                         'detection_explanation','example_case','other')
                                    NOT NULL DEFAULT 'other',
    title           VARCHAR(255)    NOT NULL,
    content         LONGTEXT        NOT NULL,
    content_hash    CHAR(64)        NOT NULL,   -- SHA-256 for deduplication
    version         VARCHAR(32)     NOT NULL DEFAULT '1.0',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_rag_content_hash (content_hash),
    INDEX idx_rag_docs_exam_id (exam_id),
    INDEX idx_rag_docs_doc_type (doc_type),
    INDEX idx_rag_docs_institution (institution),
    INDEX idx_rag_docs_is_active (is_active),
    CONSTRAINT fk_rag_docs_exam FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- RAG_CHUNKS  (document chunks used for vector retrieval)
-- =============================================================================
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    document_id     CHAR(36)        NOT NULL,
    chunk_index     INT             NOT NULL,   -- position within document
    content         TEXT            NOT NULL,
    token_count     INT             NULL,
    vector_id       VARCHAR(255)    NULL,       -- ID in the vector store (ChromaDB/FAISS)
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_chunks_document_id (document_id),
    INDEX idx_chunks_vector_id (vector_id),
    UNIQUE KEY uq_chunks_doc_position (document_id, chunk_index),
    CONSTRAINT fk_chunks_document FOREIGN KEY (document_id) REFERENCES rag_documents (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================================
-- AUDIT_LOGS  (immutable record of all privileged actions)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    actor_id        CHAR(36)        NULL,       -- user_id (NULL = system)
    actor_role      VARCHAR(32)     NULL,
    action          VARCHAR(128)    NOT NULL,   -- e.g. CREATE_EXAM, FLAG_INCIDENT, RESOLVE_INCIDENT
    resource_type   VARCHAR(64)     NULL,       -- exam | session | incident | user
    resource_id     CHAR(36)        NULL,
    ip_address      VARCHAR(45)     NULL,
    user_agent      TEXT            NULL,
    old_value       JSON            NULL,
    new_value       JSON            NULL,
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    PRIMARY KEY (id),
    INDEX idx_audit_actor_id (actor_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_resource (resource_type, resource_id),
    INDEX idx_audit_created_at (created_at)
    -- No FK on actor_id intentionally: audit logs must survive user deletion
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- SEED: default admin user (password must be changed immediately)
-- password_hash is bcrypt of "ChangeMe123!" — CHANGE BEFORE USE
-- =============================================================================
INSERT IGNORE INTO users (id, email, password_hash, role) VALUES (
    'aaaaaaaa-0000-0000-0000-000000000001',
    'admin@exam-guardian.local',
    '$2b$12$placeholder_change_this_before_use_xxxxxxxxxxxxxxxxxxxxxxx',
    'admin'
);
