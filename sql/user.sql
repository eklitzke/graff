CREATE TABLE user (
  id INTEGER NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(64) NOT NULL,
  pw_hash CHAR(56) NOT NULL,
  email VARCHAR(128),
  location VARCHAR(128),
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY (`name`),
  KEY (email)
) Engine=InnoDB;
