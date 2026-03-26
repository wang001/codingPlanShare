-- ==============================================================================
-- init_mysql.sql — CodingPlanShare MySQL 建表脚本
-- ==============================================================================
-- 使用方式：
--   mysql -h <host> -u <user> -p coding_plan_share < init_mysql.sql
--
-- 注意：
--   1. 请提前手动创建数据库：CREATE DATABASE coding_plan_share CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
--   2. 本脚本使用 IF NOT EXISTS，可重复执行（幂等）
--   3. 字段定义与 SQLAlchemy Model 严格对应，修改 Model 后同步维护此文件
-- ==============================================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ------------------------------------------------------------------------------
-- 用户表 users
-- 对应 app/models/user.py :: User
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id`            INT          NOT NULL AUTO_INCREMENT COMMENT '用户 ID',
    `username`      VARCHAR(64)  NOT NULL                COMMENT '用户名，唯一',
    `email`         VARCHAR(128) NOT NULL                COMMENT '邮箱，唯一',
    `password_hash` VARCHAR(256) NOT NULL                COMMENT '密码哈希（bcrypt）',
    `balance`       INT          NOT NULL DEFAULT 0      COMMENT '积分余额',
    `status`        INT          NOT NULL DEFAULT 1      COMMENT '状态：1=正常 0=禁用',
    `created_at`    INT          NOT NULL                COMMENT '创建时间（Unix 时间戳）',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_users_username` (`username`),
    UNIQUE KEY `uq_users_email`    (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户表';

-- ------------------------------------------------------------------------------
-- API 密钥表 api_keys
-- 对应 app/models/api_key.py :: ApiKey
-- key_type: 1=平台调用密钥（用户自己的 key）  2=厂商密钥（托管给平台的 key）
-- status:   0=正常  1=已删除  2=禁用  3=超限冷却  4=无效
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `api_keys` (
    `id`            INT          NOT NULL AUTO_INCREMENT COMMENT '密钥 ID',
    `user_id`       INT          NOT NULL                COMMENT '所属用户 ID',
    `key_type`      INT          NOT NULL                COMMENT '密钥类型：1=平台调用密钥 2=厂商密钥',
    `provider`      VARCHAR(64)  NULL                   COMMENT '厂商标识（key_type=2 时填写，如 openai）',
    `encrypted_key` VARCHAR(512) NOT NULL                COMMENT '加密存储的密钥明文',
    `name`          VARCHAR(128) NOT NULL                COMMENT '密钥名称（用户自定义）',
    `status`        INT          NOT NULL DEFAULT 0      COMMENT '状态：0=正常 1=已删除 2=禁用 3=超限冷却 4=无效',
    `cooldown_until` DATETIME    NULL                   COMMENT '冷却截止时间（status=3 时有效）',
    `used_count`    INT          NOT NULL DEFAULT 0      COMMENT '累计使用次数',
    `last_used_at`  INT          NULL                   COMMENT '最后使用时间（Unix 时间戳）',
    `created_at`    INT          NOT NULL                COMMENT '创建时间（Unix 时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_api_keys_user_id` (`user_id`),
    CONSTRAINT `fk_api_keys_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='API 密钥表';

-- ------------------------------------------------------------------------------
-- 积分流水表 point_logs
-- 对应 app/models/point_log.py :: PointLog
-- amount: 负数=扣分  正数=增分
-- type:   1=调用消耗  2=托管收益  3=管理员调整
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `point_logs` (
    `id`             INT          NOT NULL AUTO_INCREMENT COMMENT '流水 ID',
    `user_id`        INT          NOT NULL                COMMENT '关联用户 ID',
    `amount`         INT          NOT NULL                COMMENT '积分变动量（负=扣 正=增）',
    `type`           INT          NOT NULL                COMMENT '类型：1=调用消耗 2=托管收益 3=管理员调整',
    `related_key_id` INT          NULL                   COMMENT '关联密钥 ID（可为空）',
    `model`          VARCHAR(128) NULL                   COMMENT '关联 AI 模型名称',
    `remark`         VARCHAR(256) NULL                   COMMENT '备注说明',
    `created_at`     INT          NOT NULL                COMMENT '创建时间（Unix 时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_point_logs_user_id`    (`user_id`),
    KEY `idx_point_logs_created_at` (`created_at`),
    CONSTRAINT `fk_point_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_point_logs_key_id` FOREIGN KEY (`related_key_id`) REFERENCES `api_keys` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='积分流水表';

-- ------------------------------------------------------------------------------
-- 调用日志表 call_logs
-- 对应 app/models/call_log.py :: CallLog
-- status: 0=失败  1=成功
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `call_logs` (
    `id`              INT           NOT NULL AUTO_INCREMENT COMMENT '日志 ID',
    `user_id`         INT           NOT NULL                COMMENT '关联用户 ID',
    `provider_key_id` INT           NULL                   COMMENT '使用的厂商密钥 ID（可为空）',
    `model`           VARCHAR(128)  NOT NULL                COMMENT '请求的 AI 模型名称',
    `status`          INT           NOT NULL                COMMENT '结果：0=失败 1=成功',
    `error_msg`       VARCHAR(1024) NULL                   COMMENT '失败时的错误信息',
    `ip`              VARCHAR(64)   NULL                   COMMENT '客户端 IP 地址',
    `created_at`      INT           NOT NULL                COMMENT '创建时间（Unix 时间戳）',
    PRIMARY KEY (`id`),
    KEY `idx_call_logs_user_id`    (`user_id`),
    KEY `idx_call_logs_created_at` (`created_at`),
    CONSTRAINT `fk_call_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_call_logs_key_id` FOREIGN KEY (`provider_key_id`) REFERENCES `api_keys` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='调用日志表';

-- ------------------------------------------------------------------------------
-- 系统配置表 system_config
-- 对应 app/models/system_config.py :: SystemConfig
-- KV 结构，key 为主键
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `system_config` (
    `key`   VARCHAR(128)  NOT NULL COMMENT '配置键',
    `value` VARCHAR(2048) NOT NULL COMMENT '配置值（JSON 字符串或普通字符串）',
    PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='系统配置表（KV）';

-- ------------------------------------------------------------------------------
-- 初始数据（管理员账号）
-- 密码 admin123 的 bcrypt hash（与 init_db.py 保持一致）
-- 生产环境部署后务必通过 API 修改密码！
-- ------------------------------------------------------------------------------
INSERT IGNORE INTO `users`
    (`username`, `email`, `password_hash`, `balance`, `status`, `created_at`)
VALUES (
    'admin',
    'admin@example.com',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',  -- admin123
    1000,
    1,
    UNIX_TIMESTAMP()
);

-- ==============================================================================
-- 完成提示
-- ==============================================================================
SELECT '✅ init_mysql.sql 执行完成，所有表已创建' AS message;
