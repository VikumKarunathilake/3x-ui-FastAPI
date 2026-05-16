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
  CONSTRAINT `uni_client_traffics_email` UNIQUE (`email`)
);