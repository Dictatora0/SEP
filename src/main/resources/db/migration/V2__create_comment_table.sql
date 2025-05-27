CREATE TABLE IF NOT EXISTS comment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL COMMENT '商品ID',
    content TEXT NOT NULL COMMENT '评论内容',
    nickname VARCHAR(100) COMMENT '用户昵称',
    score INT COMMENT '评分(1-5)',
    create_time DATETIME NOT NULL COMMENT '评论时间',
    sentiment_score DOUBLE DEFAULT NULL COMMENT '情感评分',
    sentiment_label VARCHAR(20) DEFAULT NULL COMMENT '情感标签',
    KEY idx_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品评论表'; 