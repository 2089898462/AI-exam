-- ============================================================
-- [已废弃 - DEPRECATED]
-- 本文件不再作为数据库初始化入口。
-- 数据库初始化与迁移请统一使用 Alembic：
--   cd backend && python -m alembic upgrade head
-- 本文件仅作为 DDL 参考文档保留。
-- ============================================================
-- 企业AI智能考试与能力评估系统 - 数据库初始化脚本
-- 数据库: MySQL 8.0
-- 生成方式: Alembic autogenerate
-- 警告: 此文件为手动参考，实际迁移请使用 Alembic
-- ============================================================

CREATE DATABASE IF NOT EXISTS exam_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE exam_system;

-- 用户表
CREATE TABLE `user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  `password_hash` VARCHAR(256) NOT NULL,
  `display_name` VARCHAR(64) NOT NULL,
  `email` VARCHAR(128) NULL,
  `phone` VARCHAR(20) NULL,
  `role` ENUM('admin', 'candidate') NOT NULL DEFAULT 'candidate',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_user_username` (`username`),
  UNIQUE INDEX `idx_user_email` (`email`),
  INDEX `idx_user_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 考试表
CREATE TABLE `exam` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(200) NOT NULL,
  `description` TEXT NULL,
  `duration_minutes` INT NOT NULL,
  `pass_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `status` ENUM('draft', 'published', 'closed') NOT NULL DEFAULT 'draft',
  `created_by` BIGINT NOT NULL,
  `published_at` DATETIME NULL,
  `closed_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_exam_created_by` (`created_by`),
  INDEX `idx_exam_status` (`status`),
  INDEX `idx_exam_created_at` (`created_at`),
  CONSTRAINT `fk_exam_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 题目表
CREATE TABLE `question` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `exam_id` BIGINT NOT NULL,
  `type` ENUM('single_choice', 'multiple_choice', 'true_false', 'short_answer') NOT NULL,
  `content` TEXT NOT NULL,
  `options` JSON NULL,
  `answer` TEXT NOT NULL,
  `score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `sort_order` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_question_exam_id` (`exam_id`),
  INDEX `idx_question_sort` (`exam_id`, `sort_order`),
  CONSTRAINT `fk_question_exam_id` FOREIGN KEY (`exam_id`) REFERENCES `exam` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 考试记录表
CREATE TABLE `exam_record` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `exam_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `status` ENUM('in_progress', 'submitted', 'graded') NOT NULL DEFAULT 'in_progress',
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `submitted_at` DATETIME NULL,
  `total_score` DECIMAL(8,2) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_record_exam_id` (`exam_id`),
  INDEX `idx_record_user_id` (`user_id`),
  INDEX `idx_record_status` (`status`),
  INDEX `idx_record_exam_user` (`exam_id`, `user_id`),
  CONSTRAINT `fk_record_exam_id` FOREIGN KEY (`exam_id`) REFERENCES `exam` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_record_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 答题记录表
CREATE TABLE `answer_record` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `exam_record_id` BIGINT NOT NULL,
  `question_id` BIGINT NOT NULL,
  `answer` TEXT NULL,
  `score` DECIMAL(5,2) NULL,
  `score_type` ENUM('auto', 'ai') NULL,
  `score_detail` JSON NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uq_answer_record_question` (`exam_record_id`, `question_id`),
  INDEX `idx_answer_record_id` (`exam_record_id`),
  INDEX `idx_answer_question_id` (`question_id`),
  CONSTRAINT `fk_answer_exam_record_id` FOREIGN KEY (`exam_record_id`) REFERENCES `exam_record` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_answer_question_id` FOREIGN KEY (`question_id`) REFERENCES `question` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- AI 报告表
CREATE TABLE `ai_report` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `exam_record_id` BIGINT NOT NULL,
  `strengths` JSON NOT NULL,
  `weaknesses` JSON NOT NULL,
  `learning_suggestions` JSON NOT NULL,
  `raw_report` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_report_exam_record_id` (`exam_record_id`),
  CONSTRAINT `fk_report_exam_record_id` FOREIGN KEY (`exam_record_id`) REFERENCES `exam_record` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;