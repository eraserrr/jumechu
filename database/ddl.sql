create table user (
    id int auto_increment primary key,
    user_name varchar(100)
);

create table ingredient (
    id int auto_increment primary key,
    user_id int,
    ingredient_name varchar(100)
);