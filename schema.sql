CREATE TABLE `users` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `username` text,
  `password` text
);
CREATE TABLE `settings` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `key` text,
  `value` text
);
CREATE TABLE `inbounds` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `user_id` integer,
  `up` integer,
  `down` integer,
  `total` integer,
  `all_time` integer DEFAULT 0,
  `remark` text,
  `enable` numeric,
  `expiry_time` integer,
  `traffic_reset` text DEFAULT "never",
  `last_traffic_reset_time` integer DEFAULT 0,
  `listen` text,
  `port` integer,
  `protocol` text,
  `settings` text,
  `stream_settings` text,
  `tag` text,
  `sniffing` text,
  CONSTRAINT `uni_inbounds_tag` UNIQUE (`tag`)
);
CREATE TABLE `client_traffics` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `inbound_id` integer,
  `enable` numeric,
  `email` text,
  `up` integer,
  `down` integer,
  `all_time` integer,
  `expiry_time` integer,
  `total` integer,
  `reset` integer DEFAULT 0,
  `last_online` integer DEFAULT 0,
  CONSTRAINT `fk_inbounds_client_stats` FOREIGN KEY (`inbound_id`) REFERENCES `inbounds`(`id`),
  CONSTRAINT `uni_client_traffics_email` UNIQUE (`email`)
);
CREATE TABLE `inbound_client_ips` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `client_email` text,
  `ips` text,
  CONSTRAINT `uni_inbound_client_ips_client_email` UNIQUE (`client_email`)
);
CREATE TABLE `outbound_traffics` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `tag` text,
  `up` integer DEFAULT 0,
  `down` integer DEFAULT 0,
  `total` integer DEFAULT 0,
  CONSTRAINT `uni_outbound_traffics_tag` UNIQUE (`tag`)
);
CREATE TABLE `history_of_seeders` (
  `id` integer PRIMARY KEY AUTOINCREMENT,
  `seeder_name` text
);
CREATE INDEX `idx_enable_traffic_reset` ON `inbounds`(`enable`, `traffic_reset`);