CREATE TABLE photo (
  id INTEGER NOT NULL AUTO_INCREMENT,
  body_hash CHAR(40) NOT NULL,
  content_type VARCHAR(64) NOT NULL,
  fsid CHAR(32) NOT NULL,
  latitude FLOAT,
  longitude FLOAT,
  make VARCHAR(128),
  model VARCHAR(128),
  photo_height INTEGER NOT NULL,
  photo_width INTEGER NOT NULL,
  photo_time DATETIME,
  remote_ip INTEGER UNSIGNED NOT NULL,
  sensor BOOLEAN,
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  user_id INTEGER,
  PRIMARY KEY (id)
) Engine=InnoDB;
