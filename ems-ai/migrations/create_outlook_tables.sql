-- ============================================================
-- EMS AI Enhancement – Outlook Duplicate Database Schema
-- Compatible with MySQL 8.x
-- Run AFTER the existing EMS schema (schema.sql) is applied.
-- These tables live in the same database: evaluator_mapping_db
-- ============================================================

-- Table 1: Outlook Emails (main email store)
CREATE TABLE IF NOT EXISTS outlook_emails (
    email_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id      VARCHAR(500) NOT NULL UNIQUE     COMMENT 'RFC 2822 Message-ID – prevents duplicate imports',
    sender_email    VARCHAR(255) NOT NULL,
    recipient_emails TEXT                             COMMENT 'JSON array of recipient addresses',
    cc_emails       TEXT,
    bcc_emails      TEXT,
    subject         VARCHAR(1000),
    body_text       LONGTEXT,
    body_html       LONGTEXT,
    received_date   DATETIME,
    sent_date       DATETIME,
    folder_name     VARCHAR(255) DEFAULT 'INBOX',
    is_read         TINYINT(1)  DEFAULT 0,
    has_attachments TINYINT(1)  DEFAULT 0,
    data_source     VARCHAR(50) DEFAULT 'MANUAL_IMPORT'  COMMENT 'MANUAL_IMPORT or GRAPH_SYNC',
    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sender   (sender_email),
    INDEX idx_received (received_date),
    INDEX idx_subject  (subject(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 2: Outlook Attachments
CREATE TABLE IF NOT EXISTS outlook_attachments (
    attachment_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    email_id        BIGINT NOT NULL,
    file_name       VARCHAR(500),
    file_type       VARCHAR(100)   COMMENT 'File extension: .pdf, .xlsx …',
    content_type    VARCHAR(255)   COMMENT 'MIME type',
    file_size_bytes BIGINT,
    file_path       VARCHAR(1000)  COMMENT 'Local storage path (nullable)',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES outlook_emails(email_id) ON DELETE CASCADE,
    INDEX idx_att_email (email_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 3: Outlook Folders
CREATE TABLE IF NOT EXISTS outlook_folders (
    folder_id        INT AUTO_INCREMENT PRIMARY KEY,
    folder_name      VARCHAR(255) NOT NULL,
    folder_type      VARCHAR(50)  DEFAULT 'CUSTOM'  COMMENT 'INBOX | SENT | DRAFTS | CUSTOM',
    parent_folder_id INT          COMMENT 'Self-referential for sub-folders',
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_folder_id) REFERENCES outlook_folders(folder_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 4: Synchronisation Log
CREATE TABLE IF NOT EXISTS outlook_sync_log (
    sync_id          INT AUTO_INCREMENT PRIMARY KEY,
    sync_type        VARCHAR(50) NOT NULL  COMMENT 'MANUAL_IMPORT | GRAPH_SYNC',
    started_at       DATETIME    NOT NULL,
    completed_at     DATETIME,
    status           VARCHAR(20) DEFAULT 'RUNNING'  COMMENT 'RUNNING | COMPLETED | FAILED',
    records_imported INT         DEFAULT 0,
    records_failed   INT         DEFAULT 0,
    error_details    TEXT,
    source_file      VARCHAR(500),
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 5: Agent Execution Log
CREATE TABLE IF NOT EXISTS agent_execution_log (
    execution_id INT AUTO_INCREMENT PRIMARY KEY,
    workflow_id  VARCHAR(100) NOT NULL           COMMENT 'UUID of the LangGraph workflow run',
    agent_name   VARCHAR(100) NOT NULL           COMMENT 'availability_agent | mapping_agent | validation_agent',
    cohort_id    INT,
    round_type   VARCHAR(20)                     COMMENT 'INTERIM | FINAL',
    status       VARCHAR(20)  DEFAULT 'PENDING'  COMMENT 'PENDING | RUNNING | COMPLETED | FAILED',
    started_at   DATETIME,
    completed_at DATETIME,
    input_data   LONGTEXT                        COMMENT 'JSON string of agent inputs',
    output_data  LONGTEXT                        COMMENT 'JSON string of agent outputs',
    error_details TEXT,
    tokens_used  INT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_exec_workflow (workflow_id),
    INDEX idx_exec_agent    (agent_name),
    INDEX idx_exec_status   (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
