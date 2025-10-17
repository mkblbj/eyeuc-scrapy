-- EyeUC 数据库表结构
-- 字符集：utf8mb4，支持 emoji 和特殊字符
-- 引擎：InnoDB，支持事务和外键

-- 1. 列表/游戏表
CREATE TABLE IF NOT EXISTS lists (
  list_id INT PRIMARY KEY COMMENT '列表 ID',
  game VARCHAR(128) NOT NULL COMMENT '游戏名称',
  slug VARCHAR(128) NULL COMMENT '游戏 slug（URL 友好）',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  UNIQUE KEY uk_game (game)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='游戏/列表集合';

-- 2. 资源主表
CREATE TABLE IF NOT EXISTS mods (
  mid INT PRIMARY KEY COMMENT '资源 ID（主键）',
  list_id INT NOT NULL COMMENT '所属列表 ID',
  category VARCHAR(64) NULL COMMENT '分类（工具/名单/照片/球衣等）',
  title VARCHAR(512) NOT NULL COMMENT '资源标题',
  intro_html MEDIUMTEXT NULL COMMENT '资源介绍（HTML）',
  cover_image TEXT NULL COMMENT '封面图 URL',
  
  -- 作者/发布者信息
  author VARCHAR(128) NULL COMMENT '作者名',
  author_url TEXT NULL COMMENT '作者主页',
  publisher VARCHAR(128) NULL COMMENT '发布者名',
  publisher_url TEXT NULL COMMENT '发布者主页',
  
  -- 统计信息
  views INT NULL COMMENT '浏览量',
  downloads INT NULL COMMENT '下载量',
  likes INT NULL COMMENT '点赞数',
  
  -- 时间信息
  created_at DATETIME NULL COMMENT '发布时间',
  last_updated DATETIME NULL COMMENT '最后更新时间',
  
  -- URL
  detail_url TEXT NOT NULL COMMENT '详情页 URL',
  list_url TEXT NOT NULL COMMENT '列表页 URL',
  
  -- 原始数据备份
  raw_json LONGBLOB NULL COMMENT '原始 JSON 数据',
  
  -- 系统字段
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  updated_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  -- 索引
  INDEX idx_list_id (list_id) COMMENT '列表 ID 索引',
  INDEX idx_category (category) COMMENT '分类索引',
  INDEX idx_author (author) COMMENT '作者索引',
  INDEX idx_created_at (created_at) COMMENT '发布时间索引',
  FULLTEXT INDEX fidx_title (title) WITH PARSER ngram COMMENT '标题全文索引',
  
  -- 外键
  CONSTRAINT fk_mods_lists FOREIGN KEY (list_id) REFERENCES lists(list_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源主表';

-- 3. 图片表
CREATE TABLE IF NOT EXISTS images (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
  mod_id INT NOT NULL COMMENT '资源 ID',
  url TEXT NOT NULL COMMENT '图片 URL',
  idx INT NULL COMMENT '图片顺序（0 开始）',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  -- 唯一约束（同一资源+同一 URL，截取前 191 字符避免索引过长）
  -- 注意：MySQL 5.7+ 需要先创建列再建索引
  UNIQUE KEY uk_mod_img (mod_id, url(191)) COMMENT '防重复',
  INDEX idx_mod (mod_id) COMMENT '资源索引',
  
  -- 外键
  CONSTRAINT fk_images_mods FOREIGN KEY (mod_id) REFERENCES mods(mid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源图片';

-- 4. 版本/分支表
CREATE TABLE IF NOT EXISTS versions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
  mod_id INT NOT NULL COMMENT '资源 ID',
  vid INT NULL COMMENT '版本 ID（网站原始 ID）',
  version_name VARCHAR(255) NULL COMMENT '版本名称',
  is_default TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否默认版本',
  intro TEXT NULL COMMENT '版本说明',
  
  -- 统计信息
  updated_at DATETIME NULL COMMENT '版本更新时间',
  views INT NULL COMMENT '浏览量',
  downloads INT NULL COMMENT '下载量',
  
  created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
  
  -- 唯一约束（同一资源+同一 vid）
  UNIQUE KEY uk_mod_vid (mod_id, vid) COMMENT '防重复',
  INDEX idx_mod (mod_id) COMMENT '资源索引',
  
  -- 外键
  CONSTRAINT fk_versions_mods FOREIGN KEY (mod_id) REFERENCES mods(mid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源版本/分支';

-- 5. 下载/附件表
CREATE TABLE IF NOT EXISTS downloads (
  id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
  mod_id INT NOT NULL COMMENT '资源 ID',
  version_id BIGINT NULL COMMENT '版本 ID（关联 versions.id）',
  
  -- 类型
  type ENUM('internal','external','forum_redirect','empty','unknown') NOT NULL COMMENT '类型：internal=站内附件, external=外部网盘, forum_redirect=论坛跳转, empty=无文件, unknown=未知',
  
  -- 站内附件字段（internal）
  fileid INT NULL COMMENT '文件 ID（站内）',
  filename VARCHAR(512) NULL COMMENT '文件名',
  size VARCHAR(64) NULL COMMENT '文件大小',
  
  -- 外链字段（external）
  url TEXT NULL COMMENT '下载 URL（外链直接用，站内为备用）',
  note VARCHAR(255) NULL COMMENT '备注（如：百度网盘、第一弹等）',
  
  -- 版本标签
  version_label VARCHAR(255) NULL COMMENT '版本标签',
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  -- 唯一约束（防止重复，URL 截取前 191 字符）
  UNIQUE KEY uk_dl (mod_id, version_id, fileid, url(191)) COMMENT '防重复',
  INDEX idx_mod_ver (mod_id, version_id) COMMENT '资源+版本索引',
  
  -- 外键
  CONSTRAINT fk_downloads_mods FOREIGN KEY (mod_id) REFERENCES mods(mid) ON DELETE CASCADE,
  CONSTRAINT fk_downloads_versions FOREIGN KEY (version_id) REFERENCES versions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='下载附件';

