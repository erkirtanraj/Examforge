SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
CREATE TABLE IF NOT EXISTS ef_users (
 id VARCHAR(64) NOT NULL PRIMARY KEY, email VARCHAR(320) NULL, role VARCHAR(32) NULL,
 status VARCHAR(32) NULL, payload JSON NOT NULL, created_at DATETIME(6) NULL,
 updated_at DATETIME(6) NULL, UNIQUE KEY uq_ef_users_email (email),
 KEY ix_ef_users_role_status (role, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS ef_questions (
 id VARCHAR(64) NOT NULL PRIMARY KEY, category_id VARCHAR(64) NULL, subject_id VARCHAR(64) NULL,
 difficulty VARCHAR(16) NULL, question_type VARCHAR(32) NULL, payload JSON NOT NULL,
 created_at DATETIME(6) NULL, KEY ix_ef_questions_category_subject (category_id, subject_id),
 KEY ix_ef_questions_difficulty (difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS ef_tests (
 id VARCHAR(64) NOT NULL PRIMARY KEY, series_id VARCHAR(64) NULL, is_published BOOLEAN NULL,
 payload JSON NOT NULL, created_at DATETIME(6) NULL,
 KEY ix_ef_tests_series_published (series_id, is_published)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS ef_test_attempts (
 id VARCHAR(64) NOT NULL PRIMARY KEY, user_id VARCHAR(64) NULL, test_id VARCHAR(64) NULL,
 status VARCHAR(32) NULL, payload JSON NOT NULL, created_at DATETIME(6) NULL,
 updated_at DATETIME(6) NULL, KEY ix_ef_attempt_user_status (user_id, status),
 KEY ix_ef_attempt_test (test_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS ef_documents (
 collection_name VARCHAR(64) NOT NULL, id VARCHAR(128) NOT NULL, payload JSON NOT NULL,
 created_at DATETIME(6) NULL, updated_at DATETIME(6) NULL,
 PRIMARY KEY (collection_name, id), KEY ix_ef_documents_created (collection_name, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
SET FOREIGN_KEY_CHECKS = 1;
