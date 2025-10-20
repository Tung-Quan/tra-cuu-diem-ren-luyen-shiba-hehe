USE linksdb;

-- Bảng người
CREATE TABLE person (
  person_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
  full_name      VARCHAR(255) COLLATE utf8mb4_vi_0900_ai_ci,
  family_name    VARCHAR(128) COLLATE utf8mb4_vi_0900_ai_ci NULL,
  given_name     VARCHAR(128) COLLATE utf8mb4_vi_0900_ai_ci NULL,
  -- cột gộp để tìm kiếm: nếu có full_name thì dùng, nếu không thì ghép "family_name given_name"
  search_name    VARCHAR(255) AS (
                   COALESCE(full_name, CONCAT_WS(' ', family_name, given_name))
                 ) STORED
                 COLLATE utf8mb4_vi_0900_ai_ci,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_person_full (full_name)     -- nếu bạn muốn tránh trùng theo full_name
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_vi_0900_ai_ci;

-- Bảng link
CREATE TABLE link (
  link_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
  url         TEXT COLLATE utf8mb4_vi_0900_ai_ci NOT NULL,
  url_hash    BINARY(16) GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED,
  title       VARCHAR(255) COLLATE utf8mb4_vi_0900_ai_ci NULL,
  kind        VARCHAR(32)  COLLATE utf8mb4_vi_0900_ai_ci NULL, -- e.g. 'sheets','csv','html'
  gid         VARCHAR(32)  COLLATE utf8mb4_vi_0900_ai_ci NULL, -- gid của sheet nếu có
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_link_urlhash (url_hash),
  KEY idx_kind (kind),
  KEY idx_gid (gid)
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_vi_0900_ai_ci;

-- Bảng nối (nhiều–nhiều) + metadata dòng/sheet/snippet
CREATE TABLE person_link (
  person_id   BIGINT NOT NULL,
  link_id     BIGINT NOT NULL,
  sheet_name  VARCHAR(255) COLLATE utf8mb4_vi_0900_ai_ci NULL,
  row_number  INT NULL,
  address     VARCHAR(16) COLLATE utf8mb4_vi_0900_ai_ci NULL, -- A1, B9...
  snippet     VARCHAR(512) COLLATE utf8mb4_vi_0900_ai_ci NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (person_id, link_id, COALESCE(row_number,0)),
  CONSTRAINT fk_pl_person FOREIGN KEY (person_id) REFERENCES person(person_id) ON DELETE CASCADE,
  CONSTRAINT fk_pl_link   FOREIGN KEY (link_id)   REFERENCES link(link_id)   ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_vi_0900_ai_ci;

-- Chỉ mục tìm kiếm tên nhanh (accent-insensitive nhờ collation)
CREATE INDEX idx_person_search_name ON person (search_name);
